from pathlib import Path

from wild_catalog.core.config import Settings
from wild_catalog.taxonomy import preop


def test_preop_taxonomy_dwca_downloads_configured_archive(monkeypatch, tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    observed_settings: list[Settings] = []

    def fake_download(settings: Settings) -> Path:
        observed_settings.append(settings)
        return archive_path

    settings = Settings(taxonomy_dwca_path=archive_path)
    monkeypatch.setattr(preop, "download_taxonomy_dwca", fake_download)

    preop.preop_taxonomy_dwca(settings)

    assert observed_settings == [settings]
