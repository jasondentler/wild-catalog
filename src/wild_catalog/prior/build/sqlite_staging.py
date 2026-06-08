import sqlite3
from pathlib import Path


def list_geopackage_feature_layers(gpkg_path: Path) -> list[str]:
    connection = sqlite3.connect(gpkg_path)

    try:
        rows = connection.execute(
            """
            SELECT table_name
            FROM gpkg_contents
            WHERE data_type = 'features'
            ORDER BY table_name
            """
        ).fetchall()
    finally:
        connection.close()

    return [str(row[0]) for row in rows]


def quote_identifier(identifier: str) -> str:
    if "\x00" in identifier:
        raise ValueError("SQLite identifiers cannot contain NUL bytes.")

    return '"' + identifier.replace('"', '""') + '"'


def copy_gpkg_layer_to_temp_table(
    connection: sqlite3.Connection,
    *,
    gpkg_path: Path,
    layer_name: str,
    temp_table_name: str,
) -> None:
    source_layer = f"gpkg_source.{quote_identifier(layer_name)}"
    target_table = quote_identifier(temp_table_name)

    connection.execute("ATTACH DATABASE ? AS gpkg_source", (str(gpkg_path),))

    try:
        connection.execute(
            f"""
            CREATE TEMP TABLE {target_table}
            AS SELECT *
            FROM {source_layer}
            """
        )
    finally:
        connection.execute("DETACH DATABASE gpkg_source")
