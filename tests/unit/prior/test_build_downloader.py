from io import BytesIO

from wild_catalog.prior.build import downloader
from wild_catalog.prior.build.metadata import RangeMapArchive


def test_download_range_map_archive_reuses_existing_non_empty_file(monkeypatch, tmp_path) -> None:
    archive = RangeMapArchive(
        collection_key="birds",
        archive_index=None,
        url="https://example.test/birds.gpkg",
        filename="birds.gpkg",
    )
    destination = tmp_path / "birds.gpkg"
    destination.write_bytes(b"existing")

    def fail_download(url: str, *, timeout_seconds: int) -> bytes:
        raise AssertionError("download should not run")

    monkeypatch.setattr(downloader, "download_bytes", fail_download)

    result = downloader.download_range_map_archive(archive, download_dir=tmp_path)

    assert result == destination
    assert destination.read_bytes() == b"existing"


def test_download_range_map_archive_writes_temp_file_then_replaces(monkeypatch, tmp_path) -> None:
    archive = RangeMapArchive(
        collection_key="birds",
        archive_index=None,
        url="https://example.test/birds.gpkg",
        filename="birds.gpkg",
    )

    monkeypatch.setattr(downloader, "urlopen", _fake_urlopen(b"downloaded"))

    result = downloader.download_range_map_archive(archive, download_dir=tmp_path)

    assert result == tmp_path / "birds.gpkg"
    assert result.read_bytes() == b"downloaded"
    assert not (tmp_path / "birds.gpkg.tmp").exists()


def _fake_urlopen(payload: bytes):
    def open_url(url: str, *, timeout: int) -> BytesIO:
        return BytesIO(payload)

    return open_url
