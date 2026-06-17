import sqlite3
import zipfile
from contextlib import closing

from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.taxonomy import (
    SQLiteTaxonomyStore,
    TaxonomyService,
    import_taxonomy_archive,
    vernacular_csv_files_for_languages,
)


def test_vernacular_csv_files_for_languages_falls_back_to_base_language() -> None:
    files = vernacular_csv_files_for_languages(("en-US", "es-MX"))

    assert ("en", "VernacularNames-english.csv") in files
    assert ("es", "VernacularNames-spanish.csv") in files


def test_import_taxonomy_archive_loads_taxa_and_requested_vernacular_names(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)

    result = import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US", "es-MX"),
    )

    assert result.taxa_imported == 8
    assert result.vernacular_names_imported == 16

    with closing(sqlite3.connect(database_path)) as connection:
        taxa = connection.execute(
            """
            SELECT taxon_id, parent_taxon_id, rank, display_name
            FROM taxonomy_taxa
            WHERE taxon_id IN (43335, 418151)
            ORDER BY taxon_id
            """
        ).fetchall()
        common_names = connection.execute(
            """
            SELECT taxon_id, language_code, vernacular_name
            FROM taxonomy_vernacular_names
            WHERE taxon_id = 418151
            ORDER BY language_code
            """
        ).fetchall()

    assert taxa == [
        (43335, 43329, "species", "quagga"),
        (418151, 43335, "subspecies", "chapmani"),
    ]
    assert common_names == [
        (418151, "en", "Chapman's Zebra"),
        (418151, "es", "Cebra de Chapman"),
    ]


def test_taxonomy_service_enriches_prediction_lineage_and_common_names(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US", "es-MX"),
    )
    service = TaxonomyService(SQLiteTaxonomyStore(database_path))

    enriched = service.enrich_prediction(
        Prediction(
            confidence=0.91,
            is_present=True,
            taxon_id=418151,
            class_id=12,
        ),
        common_name_language="es-MX",
    )

    assert enriched.accepted_taxon_id == 418151
    assert enriched.taxonomy == (
        "Animalia",
        "Chordata",
        "Mammalia",
        "Perissodactyla",
        "Equidae",
        "Equus",
        "quagga",
        "chapmani",
    )
    assert enriched.taxonomy_common_names == (
        "Animales",
        "Cordados",
        "Mamiferos",
        "Caballos, tapires y rinocerontes",
        "Caballos, asnos y cebras",
        "Caballos, asnos y cebras",
        "Cebra de Sabana",
        "Cebra de Chapman",
    )
    assert enriched.taxonomy_rank_names == (
        "kingdom",
        "phylum",
        "class",
        "order",
        "family",
        "genus",
        "species",
        "subspecies",
    )


def test_taxonomy_service_falls_back_to_english_then_scientific_name(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path, include_species_english=False)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US",),
    )
    service = TaxonomyService(SQLiteTaxonomyStore(database_path))

    enriched = service.enrich_prediction(
        Prediction(taxon_id=418151),
        common_name_language="fr-FR",
    )

    assert enriched.taxonomy_common_names[-2:] == ("quagga", "Chapman's Zebra")


def test_taxonomy_service_defaults_missing_language_to_english(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US",),
    )
    service = TaxonomyService(SQLiteTaxonomyStore(database_path))

    enriched = service.enrich_prediction(
        Prediction(taxon_id=418151),
        common_name_language=None,
    )

    assert enriched.taxonomy_common_names[-1] == "Chapman's Zebra"


def test_taxonomy_service_orders_lineage_by_parent_chain_and_omits_life_root(
    tmp_path,
) -> None:
    archive_path = tmp_path / "bird-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_bird_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US",),
    )
    service = TaxonomyService(SQLiteTaxonomyStore(database_path))

    enriched = service.enrich_prediction(
        Prediction(taxon_id=9744),
        common_name_language="en-US",
    )

    assert enriched.taxonomy == (
        "Animalia",
        "Chordata",
        "Vertebrata",
        "Aves",
        "Passeriformes",
        "Icteridae",
        "Agelaius",
        "phoeniceus",
    )
    assert enriched.taxonomy_common_names == (
        "Animals",
        "Chordates",
        "Vertebrates",
        "Birds",
        "Perching Birds",
        "New World Blackbirds and Orioles",
        "Agelaius Blackbirds",
        "Red-winged Blackbird",
    )
    assert enriched.taxonomy_rank_names == (
        "kingdom",
        "phylum",
        "subphylum",
        "class",
        "order",
        "family",
        "genus",
        "species",
    )


def _create_taxonomy_archive(
    archive_path,
    *,
    include_species_english: bool = True,
) -> None:
    taxa_rows = [
        "taxonID,parentNameUsageID,acceptedNameUsageID,scientificName,taxonRank",
        "1,,,Animalia,kingdom",
        "2,1,,Chordata,phylum",
        "40151,2,,Mammalia,class",
        "43327,40151,,Perissodactyla,order",
        "43328,43327,,Equidae,family",
        "43329,43328,,Equus,genus",
        "43335,43329,,Equus quagga,species",
        "418151,43335,,Equus quagga ssp. chapmani,subspecies",
    ]
    english_names = [
        "taxonID,vernacularName,language",
        "1,Animals,en",
        "2,Chordates,en",
        "40151,Mammals,en",
        "43327,Odd-toed Ungulates,en",
        "43328,Equids,en",
        "43329,\"Horses, Asses, and Zebras\",en",
        "418151,Chapman's Zebra,en",
    ]
    if include_species_english:
        english_names.insert(-1, "43335,Plains Zebra,en")
    spanish_names = [
        "taxonID,vernacularName,language",
        "1,Animales,es",
        "2,Cordados,es",
        "40151,Mamiferos,es",
        "43327,\"Caballos, tapires y rinocerontes\",es",
        "43328,\"Caballos, asnos y cebras\",es",
        "43329,\"Caballos, asnos y cebras\",es",
        "43335,Cebra de Sabana,es",
        "418151,Cebra de Chapman,es",
    ]

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("taxa.csv", "\n".join(taxa_rows) + "\n")
        archive.writestr("VernacularNames-english.csv", "\n".join(english_names) + "\n")
        archive.writestr("VernacularNames-spanish.csv", "\n".join(spanish_names) + "\n")


def _create_bird_taxonomy_archive(archive_path) -> None:
    taxa_rows = [
        "taxonID,parentNameUsageID,acceptedNameUsageID,scientificName,taxonRank",
        "48460,,,Life,stateofmatter",
        "1,48460,,Animalia,kingdom",
        "2,1,,Chordata,phylum",
        "355675,2,,Vertebrata,subphylum",
        "3,355675,,Aves,class",
        "7251,3,,Passeriformes,order",
        "11989,7251,,Icteridae,family",
        "9740,11989,,Agelaius,genus",
        "9744,9740,,Agelaius phoeniceus,species",
    ]
    english_names = [
        "taxonID,vernacularName,language",
        "48460,biota,en",
        "1,Animals,en",
        "2,Chordates,en",
        "355675,Vertebrates,en",
        "3,Birds,en",
        "7251,Perching Birds,en",
        "11989,New World Blackbirds and Orioles,en",
        "9740,Agelaius Blackbirds,en",
        "9744,Red-winged Blackbird,en",
    ]

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("taxa.csv", "\n".join(taxa_rows) + "\n")
        archive.writestr("VernacularNames-english.csv", "\n".join(english_names) + "\n")
