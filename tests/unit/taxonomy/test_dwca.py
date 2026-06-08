from io import BytesIO
from zipfile import ZipFile

from wild_catalog.core.config import Settings
from wild_catalog.taxonomy import dwca
from wild_catalog.taxonomy.dwca import (
    download_taxonomy_dwca,
    load_taxonomy_store_from_dwca,
    taxonomy_dwca_path_for_settings,
)


def test_taxonomy_dwca_path_for_settings_uses_explicit_path(tmp_path) -> None:
    settings = Settings(
        taxonomy_dwca_path=tmp_path / "explicit.dwca.zip",
        taxonomy_store_path=tmp_path / "taxonomy",
    )

    assert taxonomy_dwca_path_for_settings(settings) == tmp_path / "explicit.dwca.zip"


def test_taxonomy_dwca_path_for_settings_uses_store_default_path(tmp_path) -> None:
    settings = Settings(taxonomy_store_path=tmp_path / "taxonomy")

    assert taxonomy_dwca_path_for_settings(settings) == (
        tmp_path / "taxonomy" / "taxonomy.dwca.zip"
    )


def test_download_taxonomy_dwca_reuses_existing_non_empty_file(monkeypatch, tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    archive_path.write_bytes(b"existing")
    settings = Settings(taxonomy_dwca_path=archive_path)

    def fail_download(url: str, *, timeout: int) -> BytesIO:
        raise AssertionError("download should not run")

    monkeypatch.setattr(dwca, "urlopen", fail_download)

    result = download_taxonomy_dwca(settings)

    assert result == archive_path
    assert archive_path.read_bytes() == b"existing"


def test_download_taxonomy_dwca_writes_temp_file_then_replaces(monkeypatch, tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    settings = Settings(
        taxonomy_dwca_url="https://example.test/taxonomy.dwca.zip",
        taxonomy_dwca_path=archive_path,
    )

    monkeypatch.setattr(dwca, "urlopen", _fake_urlopen(b"downloaded"))

    result = download_taxonomy_dwca(settings)

    assert result == archive_path
    assert archive_path.read_bytes() == b"downloaded"
    assert not (tmp_path / "taxonomy.dwca.zip.tmp").exists()


def test_load_taxonomy_store_from_dwca_reads_taxa_and_common_names(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "taxa.csv",
            "\n".join(
                [
                    (
                        "taxonID,parentNameUsageID,acceptedNameUsageID,"
                        "scientificName,taxonRank,taxonomicStatus"
                    ),
                    "1,,,Animalia,kingdom,accepted",
                    "2,1,,Chordata,phylum,accepted",
                    "3,2,,Aves,class,accepted",
                ]
            ),
        )
        archive.writestr(
            "VernacularName.csv",
            "\n".join(
                [
                    "taxonID,language,vernacularName",
                    "1,en-US,Animals",
                    "2,en-US,Chordates",
                    "3,en-US,Birds",
                ]
            ),
        )

    store = load_taxonomy_store_from_dwca(archive_path)

    taxon = store.get_taxon(3)

    assert taxon is not None
    assert taxon.scientific_name == "Aves"
    assert store.get_common_names(3)[0].name == "Birds"


def test_load_taxonomy_store_from_dwca_reads_inaturalist_member_shapes(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "nested/taxa.csv",
            "\n".join(
                [
                    "id,taxonID,parentNameUsageID,scientificName,taxonRank,references",
                    "1,https://www.inaturalist.org/taxa/1,,Animalia,kingdom,",
                    (
                        "3,https://www.inaturalist.org/taxa/3,"
                        "https://www.inaturalist.org/taxa/1,Aves,class,"
                    ),
                ]
            ),
        )
        archive.writestr(
            "nested/VernacularNames-english.csv",
            "\n".join(
                [
                    "id,vernacularName,language,locality,countryCode",
                    "1,Animals,en,,",
                    "3,Birds,en,,",
                ]
            ),
        )
        archive.writestr(
            "nested/VernacularNames-spanish.csv",
            "\n".join(
                [
                    "taxon_id,vernacularName,language,locality,countryCode",
                    "3,Aves,es,,",
                ]
            ),
        )

    store = load_taxonomy_store_from_dwca(archive_path)

    taxon = store.get_taxon(3)

    assert taxon is not None
    assert taxon.parent_taxon_id == 1
    assert tuple(record.name for record in store.get_common_names(3)) == ("Birds", "Aves")


def _fake_urlopen(payload: bytes):
    def open_url(url: str, *, timeout: int) -> BytesIO:
        return BytesIO(payload)

    return open_url
