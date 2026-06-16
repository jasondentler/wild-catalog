import logging
import signal
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("uvicorn.error")

Clock = Callable[[], float]
ProgressCallback = Callable[[int, int | None], None]
PYCURL_TIMEOUT_ERROR = 28
PYCURL_TIMEOUT_SECONDS = 240
_RETRYABLE_PYCURL_ERROR_DEFAULTS = frozenset(
    {
        5,  # Could not resolve proxy.
        6,  # Could not resolve host.
        7,  # Could not connect.
        18,  # Partial file.
        28,  # Operation timed out.
        35,  # SSL connect error.
        52,  # Got nothing from server.
        55,  # Send error.
        56,  # Receive error.
        92,  # HTTP/2 stream error.
    }
)
_PYTHON_EXIT_SIGNALS = (signal.SIGINT, signal.SIGTERM)
_download_shutdown_requested = False


class PycurlDownloadError(OSError):
    def __init__(self, error_code: int, error_message: str) -> None:
        self.error_code = error_code
        super().__init__(f"pycurl download failed: [{error_code}] {error_message}")


def download_file_with_progress(
    url: str,
    destination: str | Path,
    *,
    report_interval_seconds: float = 5.0,
    parallelism: int = 4,
    clock: Clock = time.monotonic,
) -> Path:
    destination_path = Path(destination)
    if destination_path.exists():
        return destination_path

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = destination_path.with_suffix(f"{destination_path.suffix}.part")
    partial_path.unlink(missing_ok=True)

    started_at = clock()
    last_reported_at = started_at
    bytes_downloaded = 0
    total_bytes: int | None = None

    def report_progress(downloaded: int, total: int | None) -> None:
        nonlocal bytes_downloaded, last_reported_at, total_bytes
        bytes_downloaded = downloaded
        total_bytes = total
        now = clock()
        if now - last_reported_at >= report_interval_seconds:
            _log_download_progress(
                destination_path.name,
                bytes_downloaded,
                total_bytes,
                started_at,
                now,
            )
            last_reported_at = now

    logger.info(f"Downloading {destination_path.name} from {url}")
    with _abort_download_on_shutdown_signal():
        try:
            _download_with_pycurl(
                url,
                partial_path,
                progress_callback=report_progress,
                parallelism=parallelism,
            )
            bytes_downloaded = partial_path.stat().st_size
            partial_path.replace(destination_path)
            _log_download_progress(
                destination_path.name,
                bytes_downloaded,
                total_bytes or bytes_downloaded,
                started_at,
                clock(),
            )
            logger.info(f"Finished downloading {destination_path.name}")
        except Exception:
            partial_path.unlink(missing_ok=True)
            raise

    return destination_path


def _download_with_pycurl(
    url: str,
    partial_path: Path,
    *,
    progress_callback: ProgressCallback,
    parallelism: int,
) -> None:
    pycurl = _load_pycurl()
    while True:
        try:
            total_bytes, accepts_ranges = _remote_file_metadata(url, pycurl)
            if (
                total_bytes is None
                or total_bytes <= 0
                or not accepts_ranges
                or parallelism <= 1
            ):
                _download_single_with_pycurl(
                    url,
                    partial_path,
                    pycurl=pycurl,
                    total_bytes=total_bytes,
                    progress_callback=progress_callback,
                    can_resume=accepts_ranges,
                )
                return

            _download_ranges_with_pycurl(
                url,
                partial_path,
                pycurl=pycurl,
                total_bytes=total_bytes,
                parallelism=parallelism,
                progress_callback=progress_callback,
            )
            return
        except PycurlDownloadError as exc:
            if _is_download_abort_error(exc, pycurl):
                raise KeyboardInterrupt from exc
            _retry_or_raise_pycurl_error(exc, pycurl, partial_path)
        except pycurl.error as exc:
            if _is_download_abort_error(exc, pycurl):
                raise KeyboardInterrupt from exc
            _retry_or_raise_pycurl_error(exc, pycurl, partial_path)


@contextmanager
def _abort_download_on_shutdown_signal():
    previous_handlers = {}
    _set_download_shutdown_requested(False)

    def request_shutdown(signal_number, frame) -> None:
        _ = frame
        _set_download_shutdown_requested(True)
        previous_handler = previous_handlers.get(signal_number)
        if callable(previous_handler):
            previous_handler(signal_number, frame)

    for signal_number in _PYTHON_EXIT_SIGNALS:
        previous_handlers[signal_number] = signal.getsignal(signal_number)
        signal.signal(signal_number, request_shutdown)

    try:
        yield
    finally:
        for signal_number, previous_handler in previous_handlers.items():
            signal.signal(signal_number, previous_handler)
        _set_download_shutdown_requested(False)


def _set_download_shutdown_requested(value: bool) -> None:
    global _download_shutdown_requested
    _download_shutdown_requested = value


def _is_download_abort_error(exc: Exception, pycurl) -> bool:
    if not _download_shutdown_requested:
        return False

    return _pycurl_error_code(exc) == int(getattr(pycurl, "E_ABORTED_BY_CALLBACK", 42))


def _retry_or_raise_pycurl_error(exc: Exception, pycurl, partial_path: Path) -> None:
    if not _is_retryable_pycurl_error(exc, pycurl):
        raise exc

    logger.warning(
        "Network error downloading %s; retrying and resuming from existing bytes: %s",
        partial_path.name,
        exc,
    )


def _is_retryable_pycurl_error(exc: Exception, pycurl) -> bool:
    error_code = _pycurl_error_code(exc)
    if error_code is None:
        return False

    return error_code in _retryable_pycurl_error_codes(pycurl)


def _pycurl_error_code(exc: Exception) -> int | None:
    if isinstance(exc, PycurlDownloadError):
        return exc.error_code

    if exc.args:
        return int(exc.args[0])

    return None


def _retryable_pycurl_error_codes(pycurl) -> frozenset[int]:
    return frozenset(
        {
            int(getattr(pycurl, "E_COULDNT_RESOLVE_PROXY", 5)),
            int(getattr(pycurl, "E_COULDNT_RESOLVE_HOST", 6)),
            int(getattr(pycurl, "E_COULDNT_CONNECT", 7)),
            int(getattr(pycurl, "E_PARTIAL_FILE", 18)),
            int(getattr(pycurl, "E_OPERATION_TIMEDOUT", PYCURL_TIMEOUT_ERROR)),
            int(getattr(pycurl, "E_SSL_CONNECT_ERROR", 35)),
            int(getattr(pycurl, "E_GOT_NOTHING", 52)),
            int(getattr(pycurl, "E_SEND_ERROR", 55)),
            int(getattr(pycurl, "E_RECV_ERROR", 56)),
            int(getattr(pycurl, "E_HTTP2_STREAM", 92)),
        }
    ) | _RETRYABLE_PYCURL_ERROR_DEFAULTS


def _load_pycurl():
    try:
        import pycurl
    except ImportError as exc:
        raise RuntimeError("pycurl is required for parallel model downloads.") from exc

    return pycurl


def _remote_file_metadata(url: str, pycurl) -> tuple[int | None, bool]:
    headers: dict[str, str] = {}

    def header_function(header_line: bytes) -> int:
        decoded = header_line.decode("iso-8859-1").strip()
        if ":" in decoded:
            key, value = decoded.split(":", 1)
            headers[key.lower()] = value.strip()
        return len(header_line)

    curl = pycurl.Curl()
    try:
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.NOBODY, True)
        curl.setopt(pycurl.FOLLOWLOCATION, True)
        curl.setopt(pycurl.TIMEOUT, PYCURL_TIMEOUT_SECONDS)
        curl.setopt(pycurl.HEADERFUNCTION, header_function)
        curl.perform()
        content_length = _get_content_length(curl, pycurl, headers)
    finally:
        curl.close()

    return content_length, headers.get("accept-ranges", "").lower() == "bytes"


def _download_single_with_pycurl(
    url: str,
    partial_path: Path,
    *,
    pycurl,
    total_bytes: int | None,
    progress_callback: ProgressCallback,
    can_resume: bool,
) -> None:
    existing_size = partial_path.stat().st_size if partial_path.exists() else 0
    if total_bytes is not None and existing_size >= total_bytes:
        progress_callback(total_bytes, total_bytes)
        return

    mode = "ab" if can_resume and existing_size else "wb"
    with partial_path.open(mode) as output_file:
        curl = pycurl.Curl()
        try:
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.FOLLOWLOCATION, True)
            curl.setopt(pycurl.TIMEOUT, PYCURL_TIMEOUT_SECONDS)
            if can_resume and existing_size:
                curl.setopt(pycurl.RANGE, f"{existing_size}-")
            curl.setopt(pycurl.WRITEDATA, output_file)
            _set_progress_callback(
                curl,
                pycurl,
                lambda downloaded: progress_callback(existing_size + downloaded, total_bytes),
            )
            curl.perform()
        finally:
            curl.close()


def _download_ranges_with_pycurl(
    url: str,
    partial_path: Path,
    *,
    pycurl,
    total_bytes: int,
    parallelism: int,
    progress_callback: ProgressCallback,
) -> None:
    ranges = _byte_ranges(total_bytes, parallelism)
    segment_paths = [_segment_path(partial_path, index) for index in range(len(ranges))]
    segment_progress = [
        min(_existing_segment_size(segment_paths[index]), end - start + 1)
        for index, (start, end) in enumerate(ranges)
    ]
    output_files = []
    handles = []
    multi = pycurl.CurlMulti()

    try:
        for index, (start, end) in enumerate(ranges):
            existing_size = segment_progress[index]
            if existing_size >= end - start + 1:
                continue

            output_file = segment_paths[index].open("ab" if existing_size else "wb")
            output_files.append(output_file)
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.FOLLOWLOCATION, True)
            curl.setopt(pycurl.TIMEOUT, PYCURL_TIMEOUT_SECONDS)
            curl.setopt(pycurl.RANGE, f"{start + existing_size}-{end}")
            curl.setopt(pycurl.WRITEDATA, output_file)
            _set_progress_callback(
                curl,
                pycurl,
                _segment_progress_callback(
                    index,
                    existing_size,
                    segment_progress,
                    total_bytes,
                    progress_callback,
                ),
            )
            handles.append(curl)
            multi.add_handle(curl)

        if handles:
            _perform_multi_download(multi, handles, pycurl)
    finally:
        for output_file in output_files:
            output_file.close()
        for curl in handles:
            multi.remove_handle(curl)
            curl.close()
        multi.close()

    progress_callback(total_bytes, total_bytes)
    _combine_segments(partial_path, segment_paths)


def _set_progress_callback(curl, pycurl, callback: Callable[[int], None]) -> None:
    def xfer_info(download_total, download_now, upload_total, upload_now) -> int:
        _ = download_total, upload_total, upload_now
        if _download_shutdown_requested:
            return 1

        callback(int(download_now))
        return 0

    curl.setopt(pycurl.NOPROGRESS, False)
    curl.setopt(pycurl.XFERINFOFUNCTION, xfer_info)


def _segment_progress_callback(
    index: int,
    existing_size: int,
    segment_progress: list[int],
    total_bytes: int,
    progress_callback: ProgressCallback,
) -> Callable[[int], None]:
    def update(downloaded: int) -> None:
        segment_progress[index] = existing_size + downloaded
        progress_callback(sum(segment_progress), total_bytes)

    return update


def _perform_multi_download(multi, handles: list, pycurl) -> None:
    while True:
        status, active_handles = multi.perform()
        if status != pycurl.E_CALL_MULTI_PERFORM and active_handles == 0:
            break
        multi.select(1.0)

    while True:
        queued_messages, successful_handles, failed_handles = multi.info_read()
        _ = queued_messages, successful_handles
        if not failed_handles:
            break

        failed_handle, error_code, error_message = failed_handles[0]
        _ = failed_handle
        raise PycurlDownloadError(int(error_code), str(error_message))

    if len(handles) != len(successful_handles):
        raise OSError("pycurl download failed before all range requests completed")


def _combine_segments(partial_path: Path, segment_paths: list[Path]) -> None:
    try:
        with partial_path.open("wb") as output_file:
            for segment_path in segment_paths:
                with segment_path.open("rb") as segment_file:
                    while chunk := segment_file.read(1024 * 1024):
                        output_file.write(chunk)
    finally:
        for segment_path in segment_paths:
            segment_path.unlink(missing_ok=True)


def _byte_ranges(total_bytes: int, parallelism: int) -> list[tuple[int, int]]:
    worker_count = min(max(parallelism, 1), total_bytes)
    base_size, extra_bytes = divmod(total_bytes, worker_count)
    ranges: list[tuple[int, int]] = []
    start = 0
    for index in range(worker_count):
        segment_size = base_size + (1 if index < extra_bytes else 0)
        end = start + segment_size - 1
        ranges.append((start, end))
        start = end + 1

    return ranges


def _segment_path(partial_path: Path, index: int) -> Path:
    return partial_path.with_name(f"{partial_path.name}.{index:04d}")


def _existing_segment_size(segment_path: Path) -> int:
    return segment_path.stat().st_size if segment_path.exists() else 0


def _get_content_length(curl, pycurl, headers: dict[str, str]) -> int | None:
    content_length = headers.get("content-length")
    if content_length is not None:
        return int(content_length)

    info_value = curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD_T)
    if info_value is None or info_value < 0:
        return None

    return int(info_value)


def _log_download_progress(
    filename: str,
    bytes_downloaded: int,
    total_bytes: int | None,
    started_at: float,
    now: float,
) -> None:
    elapsed_seconds = max(now - started_at, 0.001)
    bytes_per_second = bytes_downloaded / elapsed_seconds
    if total_bytes:
        percent = min(bytes_downloaded / total_bytes, 1.0)
        logger.info(
            "Downloading %s %s %5.1f%% %s/%s %s/s ETA %s",
            filename,
            _progress_bar(percent),
            percent * 100,
            _format_bytes(bytes_downloaded),
            _format_bytes(total_bytes),
            _format_bytes(bytes_per_second),
            _format_duration((total_bytes - bytes_downloaded) / bytes_per_second),
        )
        return

    logger.info(
        "Downloading %s %s downloaded %s %s/s elapsed %s",
        filename,
        _progress_bar(None),
        _format_bytes(bytes_downloaded),
        _format_bytes(bytes_per_second),
        _format_duration(elapsed_seconds),
    )


def _progress_bar(percent: float | None, width: int = 20) -> str:
    if percent is None:
        return "[" + "?" * width + "]"

    filled = min(round(percent * width), width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _format_bytes(size_bytes: float) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(size_bytes)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{size:.0f} {units[unit_index]}"

    return f"{size:.2f} {units[unit_index]}"


def _format_duration(seconds: float) -> str:
    total_seconds = max(round(seconds), 0)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"
