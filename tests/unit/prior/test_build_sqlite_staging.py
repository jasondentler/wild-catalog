import sqlite3

from wild_catalog.prior.build.sqlite_staging import (
    copy_gpkg_layer_to_temp_table,
    list_geopackage_feature_layers,
    quote_identifier,
)


def test_list_geopackage_feature_layers(tmp_path) -> None:
    gpkg_path = tmp_path / "ranges.gpkg"
    connection = sqlite3.connect(gpkg_path)

    try:
        connection.execute(
            """
            CREATE TABLE gpkg_contents (
                table_name TEXT NOT NULL,
                data_type TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO gpkg_contents (table_name, data_type)
            VALUES (?, ?)
            """,
            [
                ("z_layer", "features"),
                ("a_layer", "features"),
                ("tiles", "tiles"),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    assert list_geopackage_feature_layers(gpkg_path) == ["a_layer", "z_layer"]


def test_quote_identifier_escapes_double_quotes() -> None:
    assert quote_identifier('range"layer') == '"range""layer"'


def test_copy_gpkg_layer_to_temp_table(tmp_path) -> None:
    gpkg_path = tmp_path / "ranges.gpkg"
    gpkg_connection = sqlite3.connect(gpkg_path)

    try:
        gpkg_connection.execute('CREATE TABLE "range layer" (taxon_id INTEGER)')
        gpkg_connection.execute('INSERT INTO "range layer" (taxon_id) VALUES (101)')
        gpkg_connection.commit()
    finally:
        gpkg_connection.close()

    connection = sqlite3.connect(":memory:")

    try:
        copy_gpkg_layer_to_temp_table(
            connection,
            gpkg_path=gpkg_path,
            layer_name="range layer",
            temp_table_name="staged_ranges",
        )
        rows = connection.execute("SELECT taxon_id FROM staged_ranges").fetchall()
    finally:
        connection.close()

    assert rows == [(101,)]
