from types import SimpleNamespace

import pytest

from wild_catalog.wildlife_detection import model_download


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.warnings: list[str] = []

    def info(self, message, *args) -> None:
        if args:
            message = message % args
        self.messages.append(message)

    def warning(self, message, *args) -> None:
        if args:
            message = message % args
        self.warnings.append(message)


def test_download_file_with_progress_logs_percent_speed_and_eta(monkeypatch, tmp_path) -> None:
    logger = _Logger()
    clock_values = iter([0.0, 1.0, 2.0, 3.0])
    destination = tmp_path / "MDV6-apa-rtdetr-e.pth"

    def fake_download(url, partial_path, *, progress_callback, parallelism):
        assert url == "https://example.test/model.pth"
        assert parallelism == 4
        partial_path.write_bytes(b"abcdef")
        progress_callback(3, 6)
        progress_callback(6, 6)

    monkeypatch.setattr(model_download, "logger", logger)
    monkeypatch.setattr(model_download, "_download_with_pycurl", fake_download)

    result = model_download.download_file_with_progress(
        "https://example.test/model.pth",
        destination,
        report_interval_seconds=1,
        clock=lambda: next(clock_values),
    )

    assert result == destination
    assert destination.read_bytes() == b"abcdef"
    assert not destination.with_suffix(".pth.part").exists()
    assert logger.messages[0] == (
        "Downloading MDV6-apa-rtdetr-e.pth from https://example.test/model.pth"
    )
    assert any("[##########----------]  50.0%" in message for message in logger.messages)
    assert any("ETA" in message for message in logger.messages)
    assert logger.messages[-1] == "Finished downloading MDV6-apa-rtdetr-e.pth"


def test_download_file_with_progress_logs_unknown_total(monkeypatch, tmp_path) -> None:
    logger = _Logger()
    clock_values = iter([0.0, 1.0, 2.0])

    def fake_download(url, partial_path, *, progress_callback, parallelism):
        _ = url, parallelism
        partial_path.write_bytes(b"abc")
        progress_callback(3, None)

    monkeypatch.setattr(model_download, "logger", logger)
    monkeypatch.setattr(model_download, "_download_with_pycurl", fake_download)

    model_download.download_file_with_progress(
        "https://example.test/model.pth",
        tmp_path / "model.pth",
        report_interval_seconds=1,
        clock=lambda: next(clock_values),
    )

    assert any("[????????????????????]" in message for message in logger.messages)
    assert any("elapsed" in message for message in logger.messages)


def test_download_file_with_progress_skips_existing_destination(monkeypatch, tmp_path) -> None:
    destination = tmp_path / "model.pth"
    destination.write_bytes(b"already-here")

    def fail_download(*args, **kwargs):
        raise AssertionError("download should not be attempted")

    monkeypatch.setattr(model_download, "_download_with_pycurl", fail_download)

    assert model_download.download_file_with_progress("https://example.test/model.pth", destination)
    assert destination.read_bytes() == b"already-here"


def test_download_file_with_progress_removes_partial_file_on_failure(monkeypatch, tmp_path) -> None:
    def fake_download(url, partial_path, *, progress_callback, parallelism):
        _ = url, progress_callback, parallelism
        partial_path.write_bytes(b"partial")
        raise OSError("network failed")

    monkeypatch.setattr(model_download, "_download_with_pycurl", fake_download)
    destination = tmp_path / "model.pth"

    with pytest.raises(OSError, match="network failed"):
        model_download.download_file_with_progress("https://example.test/model.pth", destination)

    assert not destination.exists()
    assert not destination.with_suffix(".pth.part").exists()


def test_byte_ranges_split_file_across_parallel_workers() -> None:
    assert model_download._byte_ranges(total_bytes=10, parallelism=4) == [
        (0, 2),
        (3, 5),
        (6, 7),
        (8, 9),
    ]


def test_byte_ranges_never_create_empty_segments() -> None:
    assert model_download._byte_ranges(total_bytes=2, parallelism=8) == [(0, 0), (1, 1)]


def test_segment_progress_callback_reports_aggregate_progress() -> None:
    reported = []
    callback = model_download._segment_progress_callback(
        1,
        1,
        [2, 0],
        10,
        lambda downloaded, total: reported.append((downloaded, total)),
    )

    callback(3)

    assert reported == [(6, 10)]


def test_download_with_pycurl_retries_timeout_and_preserves_partial_file(
    monkeypatch,
    tmp_path,
) -> None:
    logger = _Logger()
    attempts = {"count": 0}
    pycurl, _ = _fake_pycurl()
    partial_path = tmp_path / "model.pth.part"

    def fake_download_ranges(*args, **kwargs):
        attempts["count"] += 1
        partial_path.write_bytes(b"partial")
        if attempts["count"] == 1:
            raise model_download.PycurlDownloadError(pycurl.E_OPERATION_TIMEDOUT, "timeout")

    monkeypatch.setattr(model_download, "logger", logger)
    monkeypatch.setattr(model_download, "_load_pycurl", lambda: pycurl)
    monkeypatch.setattr(
        model_download,
        "_remote_file_metadata",
        lambda url, pycurl: (100, True),
    )
    monkeypatch.setattr(model_download, "_download_ranges_with_pycurl", fake_download_ranges)

    model_download._download_with_pycurl(
        "https://example.test/model.pth",
        partial_path,
        progress_callback=lambda downloaded, total: None,
        parallelism=4,
    )

    assert attempts["count"] == 2
    assert partial_path.read_bytes() == b"partial"
    assert logger.warnings == [
        (
            "Network error downloading model.pth.part; retrying and resuming from "
            "existing bytes: pycurl download failed: [28] timeout"
        )
    ]


def test_download_with_pycurl_retries_network_failure(monkeypatch, tmp_path) -> None:
    attempts = {"count": 0}
    pycurl, _ = _fake_pycurl()

    def fake_remote_metadata(url, pycurl):
        _ = url, pycurl
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise pycurl.error(pycurl.E_COULDNT_CONNECT, "could not connect")
        return 100, True

    monkeypatch.setattr(model_download, "_load_pycurl", lambda: pycurl)
    monkeypatch.setattr(model_download, "_remote_file_metadata", fake_remote_metadata)
    monkeypatch.setattr(
        model_download,
        "_download_ranges_with_pycurl",
        lambda *args, **kwargs: None,
    )

    model_download._download_with_pycurl(
        "https://example.test/model.pth",
        tmp_path / "model.pth.part",
        progress_callback=lambda downloaded, total: None,
        parallelism=4,
    )

    assert attempts["count"] == 2


def test_download_with_pycurl_raises_non_retryable_pycurl_error(monkeypatch, tmp_path) -> None:
    pycurl, _ = _fake_pycurl()

    monkeypatch.setattr(model_download, "_load_pycurl", lambda: pycurl)
    monkeypatch.setattr(
        model_download,
        "_remote_file_metadata",
        lambda url, pycurl: (_ for _ in ()).throw(pycurl.error(3, "bad url")),
    )

    with pytest.raises(pycurl.error, match="bad url"):
        model_download._download_with_pycurl(
            "https://example.test/model.pth",
            tmp_path / "model.pth.part",
            progress_callback=lambda downloaded, total: None,
            parallelism=4,
        )


def test_download_with_pycurl_raises_non_pycurl_error(monkeypatch, tmp_path) -> None:
    pycurl, _ = _fake_pycurl()

    monkeypatch.setattr(model_download, "_load_pycurl", lambda: pycurl)
    monkeypatch.setattr(
        model_download,
        "_remote_file_metadata",
        lambda url, pycurl: (_ for _ in ()).throw(ValueError("not pycurl")),
    )

    with pytest.raises(ValueError, match="not pycurl"):
        model_download._download_with_pycurl(
            "https://example.test/model.pth",
            tmp_path / "model.pth.part",
            progress_callback=lambda downloaded, total: None,
            parallelism=4,
        )


def test_download_with_pycurl_uses_single_transfer_when_ranges_are_unavailable(
    monkeypatch,
    tmp_path,
) -> None:
    calls = {}
    pycurl = object()

    monkeypatch.setattr(model_download, "_load_pycurl", lambda: pycurl)
    monkeypatch.setattr(
        model_download,
        "_remote_file_metadata",
        lambda url, pycurl: (100, False),
    )
    monkeypatch.setattr(
        model_download,
        "_download_single_with_pycurl",
        lambda *args, **kwargs: calls.setdefault("single", (args, kwargs)),
    )
    monkeypatch.setattr(
        model_download,
        "_download_ranges_with_pycurl",
        lambda *args, **kwargs: calls.setdefault("ranges", (args, kwargs)),
    )

    model_download._download_with_pycurl(
        "https://example.test/model.pth",
        tmp_path / "model.pth.part",
        progress_callback=lambda downloaded, total: None,
        parallelism=4,
    )

    assert "single" in calls
    assert "ranges" not in calls


def test_download_with_pycurl_uses_parallel_ranges_when_supported(monkeypatch, tmp_path) -> None:
    calls = {}
    pycurl = object()

    monkeypatch.setattr(model_download, "_load_pycurl", lambda: pycurl)
    monkeypatch.setattr(
        model_download,
        "_remote_file_metadata",
        lambda url, pycurl: (100, True),
    )
    monkeypatch.setattr(
        model_download,
        "_download_single_with_pycurl",
        lambda *args, **kwargs: calls.setdefault("single", (args, kwargs)),
    )
    monkeypatch.setattr(
        model_download,
        "_download_ranges_with_pycurl",
        lambda *args, **kwargs: calls.setdefault("ranges", (args, kwargs)),
    )

    model_download._download_with_pycurl(
        "https://example.test/model.pth",
        tmp_path / "model.pth.part",
        progress_callback=lambda downloaded, total: None,
        parallelism=4,
    )

    assert "ranges" in calls
    assert "single" not in calls


def test_remote_file_metadata_reads_content_length_and_accept_ranges() -> None:
    pycurl, curl_calls = _fake_pycurl()

    content_length, accepts_ranges = model_download._remote_file_metadata(
        "https://example.test/model.pth",
        pycurl,
    )

    assert content_length == 123
    assert accepts_ranges is True
    assert curl_calls[0].options[pycurl.URL] == "https://example.test/model.pth"
    assert curl_calls[0].options[pycurl.NOBODY] is True
    assert curl_calls[0].options[pycurl.TIMEOUT] == 240
    assert curl_calls[0].closed is True


def test_download_single_with_pycurl_writes_file_and_reports_progress(tmp_path) -> None:
    pycurl, curl_calls = _fake_pycurl()
    reported = []
    partial_path = tmp_path / "model.pth.part"

    model_download._download_single_with_pycurl(
        "https://example.test/model.pth",
        partial_path,
        pycurl=pycurl,
        total_bytes=6,
        progress_callback=lambda downloaded, total: reported.append((downloaded, total)),
        can_resume=False,
    )

    assert partial_path.read_bytes() == b"single"
    assert reported == [(6, 6)]
    assert curl_calls[0].options[pycurl.URL] == "https://example.test/model.pth"
    assert curl_calls[0].options[pycurl.TIMEOUT] == 240
    assert curl_calls[0].closed is True


def test_download_single_with_pycurl_resumes_from_existing_partial_file(tmp_path) -> None:
    pycurl, curl_calls = _fake_pycurl()
    reported = []
    partial_path = tmp_path / "model.pth.part"
    partial_path.write_bytes(b"abc")

    model_download._download_single_with_pycurl(
        "https://example.test/model.pth",
        partial_path,
        pycurl=pycurl,
        total_bytes=9,
        progress_callback=lambda downloaded, total: reported.append((downloaded, total)),
        can_resume=True,
    )

    assert partial_path.read_bytes() == b"abcsingle"
    assert reported == [(9, 9)]
    assert curl_calls[0].options[pycurl.RANGE] == "3-"


def test_download_single_with_pycurl_skips_completed_partial_file(tmp_path) -> None:
    pycurl, curl_calls = _fake_pycurl()
    reported = []
    partial_path = tmp_path / "model.pth.part"
    partial_path.write_bytes(b"complete")

    model_download._download_single_with_pycurl(
        "https://example.test/model.pth",
        partial_path,
        pycurl=pycurl,
        total_bytes=8,
        progress_callback=lambda downloaded, total: reported.append((downloaded, total)),
        can_resume=True,
    )

    assert reported == [(8, 8)]
    assert curl_calls == []


def test_download_ranges_with_pycurl_writes_segments_in_order(monkeypatch, tmp_path) -> None:
    pycurl, curl_calls = _fake_pycurl()
    reported = []
    partial_path = tmp_path / "model.pth.part"

    def fake_perform_multi_download(multi, handles, pycurl):
        _ = multi, pycurl
        for handle in handles:
            output_file = handle.options[pycurl.WRITEDATA]
            output_file.write(handle.options[pycurl.RANGE].encode("ascii"))

    monkeypatch.setattr(model_download, "_perform_multi_download", fake_perform_multi_download)

    model_download._download_ranges_with_pycurl(
        "https://example.test/model.pth",
        partial_path,
        pycurl=pycurl,
        total_bytes=6,
        parallelism=2,
        progress_callback=lambda downloaded, total: reported.append((downloaded, total)),
    )

    assert partial_path.read_bytes() == b"0-23-5"
    assert reported[-1] == (6, 6)
    assert [curl.options[pycurl.RANGE] for curl in curl_calls] == ["0-2", "3-5"]
    assert all(curl.closed for curl in curl_calls)


def test_download_ranges_with_pycurl_resumes_incomplete_segments(monkeypatch, tmp_path) -> None:
    pycurl, curl_calls = _fake_pycurl()
    partial_path = tmp_path / "model.pth.part"
    model_download._segment_path(partial_path, 0).write_bytes(b"abc")
    model_download._segment_path(partial_path, 1).write_bytes(b"d")

    def fake_perform_multi_download(multi, handles, pycurl):
        _ = multi
        for handle in handles:
            handle.options[pycurl.WRITEDATA].write(handle.options[pycurl.RANGE].encode("ascii"))

    monkeypatch.setattr(model_download, "_perform_multi_download", fake_perform_multi_download)

    model_download._download_ranges_with_pycurl(
        "https://example.test/model.pth",
        partial_path,
        pycurl=pycurl,
        total_bytes=6,
        parallelism=2,
        progress_callback=lambda downloaded, total: None,
    )

    assert partial_path.read_bytes() == b"abcd4-5"
    assert [curl.options[pycurl.RANGE] for curl in curl_calls] == ["4-5"]


def test_perform_multi_download_raises_failed_handle_error() -> None:
    pycurl, _ = _fake_pycurl()
    failed_handle = object()
    multi = SimpleNamespace(
        perform=lambda: (0, 0),
        select=lambda timeout: None,
        info_read=lambda: (0, [], [(failed_handle, 7, "failed")]),
    )

    with pytest.raises(OSError, match=r"\[7\] failed"):
        model_download._perform_multi_download(multi, [failed_handle], pycurl)


def test_perform_multi_download_raises_when_handles_do_not_complete() -> None:
    pycurl, _ = _fake_pycurl()
    multi = SimpleNamespace(
        perform=lambda: (0, 0),
        select=lambda timeout: None,
        info_read=lambda: (0, [], []),
    )

    with pytest.raises(OSError, match="before all range requests completed"):
        model_download._perform_multi_download(multi, [object()], pycurl)


def test_combine_segments_writes_complete_file_and_removes_segments(tmp_path) -> None:
    partial_path = tmp_path / "model.pth.part"
    first_segment = tmp_path / "model.pth.part.0000"
    second_segment = tmp_path / "model.pth.part.0001"
    first_segment.write_bytes(b"abc")
    second_segment.write_bytes(b"def")

    model_download._combine_segments(partial_path, [first_segment, second_segment])

    assert partial_path.read_bytes() == b"abcdef"
    assert not first_segment.exists()
    assert not second_segment.exists()


def test_load_pycurl_explains_missing_dependency(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pycurl":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="pycurl is required"):
        model_download._load_pycurl()


def test_get_content_length_prefers_header_value() -> None:
    curl = object()
    pycurl = object()

    assert model_download._get_content_length(curl, pycurl, {"content-length": "123"}) == 123


def test_get_content_length_handles_missing_pycurl_info() -> None:
    class _Curl:
        def getinfo(self, option):
            return -1

    class _Pycurl:
        CONTENT_LENGTH_DOWNLOAD_T = object()

    assert model_download._get_content_length(_Curl(), _Pycurl(), {}) is None


def test_get_content_length_uses_pycurl_info() -> None:
    class _Curl:
        def getinfo(self, option):
            return 123

    class _Pycurl:
        CONTENT_LENGTH_DOWNLOAD_T = object()

    assert model_download._get_content_length(_Curl(), _Pycurl(), {}) == 123


def test_retryable_error_detection_accepts_pycurl_timeout_and_network_errors() -> None:
    pycurl, _ = _fake_pycurl()

    assert model_download._is_retryable_pycurl_error(
        pycurl.error(pycurl.E_OPERATION_TIMEDOUT, "x"), pycurl
    )
    assert model_download._is_retryable_pycurl_error(
        pycurl.error(pycurl.E_COULDNT_CONNECT, "x"), pycurl
    )
    assert model_download._is_retryable_pycurl_error(
        model_download.PycurlDownloadError(pycurl.E_RECV_ERROR, "x"), pycurl
    )
    assert not model_download._is_retryable_pycurl_error(pycurl.error(3, "x"), pycurl)


def test_download_abort_error_detection_requires_shutdown_request() -> None:
    pycurl, _ = _fake_pycurl()
    abort_error = pycurl.error(pycurl.E_ABORTED_BY_CALLBACK, "aborted")

    model_download._set_download_shutdown_requested(False)
    assert not model_download._is_download_abort_error(abort_error, pycurl)

    model_download._set_download_shutdown_requested(True)
    try:
        assert model_download._is_download_abort_error(abort_error, pycurl)
    finally:
        model_download._set_download_shutdown_requested(False)


def test_progress_callback_aborts_when_shutdown_requested() -> None:
    pycurl, curl_calls = _fake_pycurl()
    curl = pycurl.Curl()
    seen = []
    model_download._set_progress_callback(curl, pycurl, lambda downloaded: seen.append(downloaded))

    model_download._set_download_shutdown_requested(True)
    try:
        result = curl.options[pycurl.XFERINFOFUNCTION](10, 5, 0, 0)
    finally:
        model_download._set_download_shutdown_requested(False)

    assert result == 1
    assert seen == []
    assert curl_calls == [curl]


def test_abort_download_on_shutdown_signal_sets_flag_and_restores_handlers(
    monkeypatch,
) -> None:
    registered_handlers = {}
    previous_handlers = {
        model_download.signal.SIGINT: lambda signal_number, frame: None,
        model_download.signal.SIGTERM: lambda signal_number, frame: None,
    }
    previous_calls = []

    def fake_getsignal(signal_number):
        return previous_handlers[signal_number]

    def fake_signal(signal_number, handler):
        registered_handlers[signal_number] = handler
        return previous_handlers[signal_number]

    def previous_handler(signal_number, frame):
        previous_calls.append((signal_number, frame))

    previous_handlers[model_download.signal.SIGINT] = previous_handler
    monkeypatch.setattr(model_download.signal, "getsignal", fake_getsignal)
    monkeypatch.setattr(model_download.signal, "signal", fake_signal)

    with model_download._abort_download_on_shutdown_signal():
        registered_handlers[model_download.signal.SIGINT](model_download.signal.SIGINT, "frame")
        assert model_download._download_shutdown_requested is True

    assert previous_calls == [(model_download.signal.SIGINT, "frame")]
    assert registered_handlers == previous_handlers
    assert model_download._download_shutdown_requested is False


def test_format_helpers_cover_large_values_and_hours() -> None:
    assert model_download._segment_path(model_download.Path("model.pth.part"), 3).name == (
        "model.pth.part.0003"
    )
    assert model_download._format_bytes(1024 * 1024 * 1024) == "1.00 GB"
    assert model_download._format_duration(3661) == "1:01:01"


def _fake_pycurl():
    curls = []

    def make_curl():
        curl = SimpleNamespace(options={}, closed=False)

        def setopt(option, value):
            curl.options[option] = value

        def perform():
            if "HEADERFUNCTION" in curl.options:
                curl.options["HEADERFUNCTION"](b"Content-Length: 123\r\n")
                curl.options["HEADERFUNCTION"](b"Accept-Ranges: bytes\r\n")
            if "WRITEDATA" in curl.options:
                curl.options["WRITEDATA"].write(b"single")
            if "XFERINFOFUNCTION" in curl.options:
                curl.options["XFERINFOFUNCTION"](6, 6, 0, 0)

        def getinfo(option):
            return 123

        def close():
            curl.closed = True

        curl.setopt = setopt
        curl.perform = perform
        curl.getinfo = getinfo
        curl.close = close
        curls.append(curl)
        return curl

    def make_multi():
        multi = SimpleNamespace(handles=[], closed=False)

        def add_handle(curl):
            multi.handles.append(curl)

        def remove_handle(curl):
            multi.handles.remove(curl)

        def close():
            multi.closed = True

        multi.add_handle = add_handle
        multi.remove_handle = remove_handle
        multi.close = close
        return multi

    pycurl = SimpleNamespace(
        CONTENT_LENGTH_DOWNLOAD_T="CONTENT_LENGTH_DOWNLOAD_T",
        E_COULDNT_CONNECT=7,
        E_ABORTED_BY_CALLBACK=42,
        E_CALL_MULTI_PERFORM=1,
        E_OPERATION_TIMEDOUT=28,
        E_RECV_ERROR=56,
        FOLLOWLOCATION="FOLLOWLOCATION",
        HEADERFUNCTION="HEADERFUNCTION",
        NOBODY="NOBODY",
        NOPROGRESS="NOPROGRESS",
        RANGE="RANGE",
        TIMEOUT="TIMEOUT",
        URL="URL",
        WRITEDATA="WRITEDATA",
        XFERINFOFUNCTION="XFERINFOFUNCTION",
        Curl=make_curl,
        CurlMulti=make_multi,
        error=type("PycurlError", (Exception,), {}),
    )
    return pycurl, curls
