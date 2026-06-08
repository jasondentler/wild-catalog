import sqlite3
from pathlib import Path


def create_range_store_fixture(
    database_path: Path,
    *,
    h3_resolution: int,
    rows: list[tuple[str, int]],
) -> None:
    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            """
            CREATE TABLE range_cells (
                h3_cell TEXT NOT NULL,
                taxon_id INTEGER NOT NULL,
                PRIMARY KEY (h3_cell, taxon_id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX idx_range_cells_taxon_id
            ON range_cells (taxon_id)
            """
        )
        connection.execute(
            """
            CREATE TABLE range_store_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO range_store_metadata (key, value)
            VALUES ('h3_resolution', ?)
            """,
            (str(h3_resolution),),
        )
        connection.executemany(
            """
            INSERT INTO range_cells (h3_cell, taxon_id)
            VALUES (?, ?)
            """,
            rows,
        )
        connection.commit()
    finally:
        connection.close()
