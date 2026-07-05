import sqlite3
import zipfile
from contextlib import closing

from wild_catalog.core.types import GpsCoordinates
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.taxonomy import (
    SEARCH_RESULT_LIMIT,
    SQLiteTaxonomyStore,
    TaxonomyService,
    import_taxonomy_archive,
    import_taxonomy_archive_if_missing,
    vernacular_csv_files_for_languages,
)


def test_vernacular_csv_files_for_languages_falls_back_to_base_language() -> None:
    files = vernacular_csv_files_for_languages(("en-US", "es-MX"))

    assert ("en", "VernacularNames-english.csv") in files
    assert ("es", "VernacularNames-spanish.csv") in files


def test_vernacular_csv_files_for_languages_defaults_to_all_supported_languages() -> None:
    files = vernacular_csv_files_for_languages(())

    assert ("en", "VernacularNames-english.csv") in files
    assert ("es", "VernacularNames-spanish.csv") in files
    assert ("zh-cn", "VernacularNames-chinese-simplified.csv") in files


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

    with closing(sqlite3.connect(database_path)) as connection:
        fts_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name IN (
                    'taxonomy_taxa_fts',
                    'taxonomy_vernacular_names_fts'
                  )
                """
            ).fetchall()
        }
        taxa_indexed = connection.execute(
            "SELECT COUNT(*) FROM taxonomy_taxa_fts"
        ).fetchone()[0]
        vernacular_names_indexed = connection.execute(
            "SELECT COUNT(*) FROM taxonomy_vernacular_names_fts"
        ).fetchone()[0]

    assert fts_tables == {"taxonomy_taxa_fts", "taxonomy_vernacular_names_fts"}
    assert taxa_indexed == result.taxa_imported
    assert vernacular_names_indexed == result.vernacular_names_imported


def test_import_taxonomy_archive_defaults_to_all_supported_languages(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)

    result = import_taxonomy_archive(database_path, archive_path)

    with closing(sqlite3.connect(database_path)) as connection:
        languages = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT language_code FROM taxonomy_vernacular_names"
            ).fetchall()
        }
        chinese_name = connection.execute(
            """
            SELECT vernacular_name
            FROM taxonomy_vernacular_names
            WHERE taxon_id = 43335
              AND language_code = 'zh-cn'
            """
        ).fetchone()[0]

    assert result.taxa_imported == 8
    assert result.vernacular_names_imported == 24
    assert {"en", "es", "zh-cn"}.issubset(languages)
    assert chinese_name == "平原斑马"


def test_import_taxonomy_archive_if_missing_repairs_missing_search_indexes(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute("DROP TABLE taxonomy_taxa_fts")
            connection.execute("DROP TABLE taxonomy_vernacular_names_fts")

    result = import_taxonomy_archive_if_missing(database_path, tmp_path / "downloads")

    with closing(sqlite3.connect(database_path)) as connection:
        taxa_indexed = connection.execute(
            "SELECT COUNT(*) FROM taxonomy_taxa_fts"
        ).fetchone()[0]
        vernacular_names_indexed = connection.execute(
            "SELECT COUNT(*) FROM taxonomy_vernacular_names_fts"
        ).fetchone()[0]

    assert result.taxa_imported == 0
    assert result.vernacular_names_imported == 0
    assert taxa_indexed == 8
    assert vernacular_names_indexed == 8


def test_import_taxonomy_archive_if_missing_does_not_rebuild_existing_store_for_languages(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    result = import_taxonomy_archive_if_missing(
        database_path,
        tmp_path / "downloads",
        archive_url="https://example.test/taxonomy.dwca.zip",
        languages=("en-US", "zh-CN"),
    )

    with closing(sqlite3.connect(database_path)) as connection:
        metadata_languages = connection.execute(
            "SELECT value FROM taxonomy_store_metadata WHERE key = 'languages'"
        ).fetchone()[0]
        chinese_name = connection.execute(
            """
            SELECT vernacular_name
            FROM taxonomy_vernacular_names
            WHERE taxon_id = 43335
              AND language_code = 'zh-cn'
            """
        ).fetchone()

    assert result.taxa_imported == 0
    assert result.vernacular_names_imported == 0
    assert metadata_languages == "en-us"
    assert chinese_name is None


def test_taxonomy_service_enriches_prediction_lineage_and_common_names(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US", "es-MX"),
    )
    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
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
    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
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
    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
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
    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
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


def test_taxonomy_service_pads_unknown_taxon_prediction_fields(tmp_path) -> None:
    enriched = TaxonomyService(
        SQLiteTaxonomyStore(tmp_path / "unused.sqlite")
    ).enrich_prediction(
        Prediction(
            taxon_id=-1,
            taxonomy=("Animalia", "Agelaius", "phoeniceus"),
            taxonomy_rank_names=("kingdom",),
            taxonomy_common_names=("Animals", "Blackbirds"),
        )
    )

    assert enriched.taxonomy == ("Animalia", "Agelaius", "phoeniceus")
    assert enriched.taxonomy_rank_names == ("kingdom", "", "")
    assert enriched.taxonomy_common_names == ("Animals", "Blackbirds", "")


def test_taxonomy_service_pads_prediction_fields_when_lineage_is_missing(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path)

    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
        enriched = service.enrich_prediction(
            Prediction(
                taxon_id=999999,
                taxonomy=("Animalia", "Agelaius", "phoeniceus"),
                taxonomy_rank_names=("kingdom",),
                taxonomy_common_names=("Animals", "Blackbirds"),
            )
        )

    assert enriched.taxonomy == ("Animalia", "Agelaius", "phoeniceus")
    assert enriched.taxonomy_rank_names == ("kingdom", "", "")
    assert enriched.taxonomy_common_names == ("Animals", "Blackbirds", "")


def test_taxonomy_store_searches_scientific_names_with_fts_prefix_matching(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path)

    with SQLiteTaxonomyStore(database_path) as store:
        matches = store.search_scientific_names("Equus", limit=10)

    assert [match.taxon_id for match in matches[:3]] == [43329, 43335, 418151]


def test_taxonomy_store_searches_common_names_by_language(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US", "es-MX"),
    )

    with SQLiteTaxonomyStore(database_path) as store:
        spanish_matches = store.search_common_names(
            "Cebra de",
            language_preferences=("es", "en"),
            limit=10,
        )
        english_matches = store.search_common_names(
            "Cebra de",
            language_preferences=("en",),
            limit=10,
        )

    assert [match.taxon_id for match in spanish_matches] == [418151, 43335]
    assert english_matches == ()


def test_taxonomy_service_searches_chinese_common_names(tmp_path) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US", "zh-CN"),
    )

    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
        results = service.search(
            "平原斑马",
            language_preferences=("zh-CN",),
        )

    assert len(results) == 1
    assert results[0].taxonomy[-1] == "quagga"
    assert results[0].taxonomy_common_names[-1] == "平原斑马"


def test_taxonomy_service_does_not_search_english_common_names_for_spanish_request(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US", "es-MX"),
    )

    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
        results = service.search(
            "Plains",
            field="common",
            language_preferences=("es-MX",),
        )

    assert results == ()


def test_taxonomy_service_search_normalizes_names_like_identify(tmp_path) -> None:
    archive_path = tmp_path / "mixed-case-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_mixed_case_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
        results = service.search(
            "PHOENICEUS",
            field="scientific",
            language_preferences=("en-US",),
        )

    assert len(results) == 1
    assert results[0].taxonomy == ("Animalia", "Agelaius", "phoeniceus")
    assert results[0].taxonomy_common_names == (
        "Animals",
        "Blackbirds And Orioles",
        "Black-Bellied Bewick's Wren",
    )


def test_taxonomy_service_search_resolves_accepted_taxa_and_localized_names(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path, include_accepted_synonym=True)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US", "es-MX"),
    )

    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
        results = service.search(
            "Quagga antigua",
            field="scientific",
            language_preferences=("es-MX",),
        )

    assert len(results) == 1
    assert results[0].taxonomy[-1] == "quagga"
    assert results[0].taxonomy_rank_names[-1] == "species"
    assert results[0].taxonomy_common_names[-1] == "Cebra De Sabana"


def test_taxonomy_service_search_combines_common_and_scientific_results(
    tmp_path,
) -> None:
    archive_path = tmp_path / "taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_taxonomy_archive(archive_path)
    import_taxonomy_archive(
        database_path,
        archive_path,
        languages=("en-US",),
    )

    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
        common_results = service.search(
            "Plains",
            field="common",
            language_preferences=("en-US",),
        )
        scientific_results = service.search(
            "Equus",
            field="scientific",
            language_preferences=("es-MX",),
        )
        english_scientific_results = service.search(
            "Equus",
            field="scientific",
            language_preferences=("en-US",),
        )
        combined_results = service.search(
            "Equus",
            language_preferences=("en-US",),
        )

    assert [result.taxonomy[-1] for result in common_results] == ["quagga"]
    assert scientific_results[0].taxonomy[-1] == "Equus"
    assert scientific_results == english_scientific_results
    assert combined_results[0].taxonomy[-1] == "Equus"


def test_taxonomy_service_search_limits_results_to_top_twenty(tmp_path) -> None:
    archive_path = tmp_path / "many-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_many_search_result_archive(archive_path, count=25)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    with TaxonomyService(SQLiteTaxonomyStore(database_path)) as service:
        results = service.search(
            "Searchbird",
            field="common",
            language_preferences=("en-US",),
        )

    assert len(results) == SEARCH_RESULT_LIMIT


def test_taxonomy_service_search_gps_filter_keeps_present_species(tmp_path) -> None:
    archive_path = tmp_path / "bird-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_bird_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))
    range_prior_service = _FakeRangePriorService({9744})
    gps_coordinates = GpsCoordinates(latitude=29.5, longitude=-94.5)

    with TaxonomyService(
        SQLiteTaxonomyStore(database_path),
        range_prior_service=range_prior_service,
    ) as service:
        results = service.search(
            "Red-winged",
            field="common",
            language_preferences=("en-US",),
            gps_coordinates=gps_coordinates,
        )

    assert len(results) == 1
    assert results[0].taxonomy[-1] == "phoeniceus"
    assert range_prior_service.calls == [gps_coordinates]


def test_taxonomy_service_search_gps_filter_omits_absent_species(tmp_path) -> None:
    archive_path = tmp_path / "bird-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_bird_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    with TaxonomyService(
        SQLiteTaxonomyStore(database_path),
        range_prior_service=_FakeRangePriorService(set()),
    ) as service:
        results = service.search(
            "Red-winged",
            field="common",
            language_preferences=("en-US",),
            gps_coordinates=GpsCoordinates(latitude=29.5, longitude=-94.5),
        )

    assert results == ()


def test_taxonomy_service_search_gps_filter_keeps_present_ancestor(tmp_path) -> None:
    archive_path = tmp_path / "bird-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_bird_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    with TaxonomyService(
        SQLiteTaxonomyStore(database_path),
        range_prior_service=_FakeRangePriorService({9744}),
    ) as service:
        results = service.search(
            "Agelaius",
            field="scientific",
            language_preferences=("en-US",),
            gps_coordinates=GpsCoordinates(latitude=29.5, longitude=-94.5),
        )

    assert [result.taxonomy[-1] for result in results] == [
        "Agelaius",
        "phoeniceus",
    ]


def test_taxonomy_service_search_gps_filter_omits_absent_ancestor(tmp_path) -> None:
    archive_path = tmp_path / "bird-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_bird_taxonomy_archive(archive_path)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    with TaxonomyService(
        SQLiteTaxonomyStore(database_path),
        range_prior_service=_FakeRangePriorService({999999}),
    ) as service:
        results = service.search(
            "Agelaius",
            field="scientific",
            language_preferences=("en-US",),
            gps_coordinates=GpsCoordinates(latitude=29.5, longitude=-94.5),
        )

    assert results == ()


def test_taxonomy_service_search_applies_result_limit_after_gps_filtering(
    tmp_path,
) -> None:
    archive_path = tmp_path / "many-taxonomy.dwca.zip"
    database_path = tmp_path / "taxonomy.sqlite"
    _create_many_search_result_archive(archive_path, count=25)
    import_taxonomy_archive(database_path, archive_path, languages=("en-US",))

    with TaxonomyService(
        SQLiteTaxonomyStore(database_path),
        range_prior_service=_FakeRangePriorService(set(range(1005, 1025))),
    ) as service:
        results = service.search(
            "Searchbird",
            field="common",
            language_preferences=("en-US",),
            gps_coordinates=GpsCoordinates(latitude=29.5, longitude=-94.5),
        )

    assert len(results) == SEARCH_RESULT_LIMIT
    assert all(result.taxonomy[-1] not in {"searchbird0", "searchbird1"} for result in results)


class _FakeRangePriorService:
    def __init__(self, present_taxon_ids: set[int]) -> None:
        self._present_taxon_ids = set(present_taxon_ids)
        self.calls: list[GpsCoordinates] = []

    def get_present_taxon_ids(self, gps_coordinates: GpsCoordinates) -> set[int]:
        self.calls.append(gps_coordinates)
        return set(self._present_taxon_ids)


def _create_taxonomy_archive(
    archive_path,
    *,
    include_species_english: bool = True,
    include_accepted_synonym: bool = False,
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
    if include_accepted_synonym:
        taxa_rows.append("900001,43329,43335,Equus quagga antigua,species")
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
    chinese_names = [
        "taxonID,vernacularName,language",
        "1,动物,zh-CN",
        "2,脊索动物,zh-CN",
        "40151,哺乳动物,zh-CN",
        "43327,奇蹄目,zh-CN",
        "43328,马科,zh-CN",
        "43329,马属,zh-CN",
        "43335,平原斑马,zh-CN",
        "418151,查普曼斑马,zh-CN",
    ]

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("taxa.csv", "\n".join(taxa_rows) + "\n")
        archive.writestr("VernacularNames-english.csv", "\n".join(english_names) + "\n")
        archive.writestr("VernacularNames-spanish.csv", "\n".join(spanish_names) + "\n")
        archive.writestr(
            "VernacularNames-chinese-simplified.csv",
            "\n".join(chinese_names) + "\n",
        )


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


def _create_mixed_case_taxonomy_archive(archive_path) -> None:
    taxa_rows = [
        "taxonID,parentNameUsageID,acceptedNameUsageID,scientificName,taxonRank",
        "1,,,animalia,kingdom",
        "2,1,,AGELAIUS,genus",
        "3,2,,AGELAIUS PHOENICEUS,species",
    ]
    english_names = [
        "taxonID,vernacularName,language",
        "1,animals,en",
        "2,blackbirds and orioles,en",
        "3,black-bellied bewick's wren,en",
    ]

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("taxa.csv", "\n".join(taxa_rows) + "\n")
        archive.writestr("VernacularNames-english.csv", "\n".join(english_names) + "\n")


def _create_many_search_result_archive(archive_path, *, count: int) -> None:
    taxa_rows = [
        "taxonID,parentNameUsageID,acceptedNameUsageID,scientificName,taxonRank",
        "1,,,Animalia,kingdom",
        "2,1,,Chordata,phylum",
        "3,2,,Aves,class",
        "4,3,,Passeriformes,order",
        "5,4,,Icteridae,family",
        "6,5,,Agelaius,genus",
    ]
    english_names = [
        "taxonID,vernacularName,language",
        "1,Animals,en",
        "2,Chordates,en",
        "3,Birds,en",
        "4,Perching Birds,en",
        "5,New World Blackbirds and Orioles,en",
        "6,Agelaius Blackbirds,en",
    ]

    for index in range(count):
        taxon_id = 1000 + index
        taxa_rows.append(f"{taxon_id},6,,Agelaius searchbird{index},species")
        english_names.append(f"{taxon_id},Searchbird {index},en")

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("taxa.csv", "\n".join(taxa_rows) + "\n")
        archive.writestr("VernacularNames-english.csv", "\n".join(english_names) + "\n")
