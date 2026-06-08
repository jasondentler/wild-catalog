import sqlite3

import pytest

from tests.unit.prior.helpers import create_range_store_fixture
from wild_catalog.prior.store import SQLiteSpeciesRangeStore


def test_sqlite_store_returns_present_taxon_ids_for_cell(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store_fixture(
        database_path,
        h3_resolution=5,
        rows=[
            ("cell-a", 101),
            ("cell-a", 202),
            ("cell-b", 303),
        ],
    )

    store = SQLiteSpeciesRangeStore(database_path)

    try:
        assert store.get_present_taxon_ids_for_cell("cell-a") == {101, 202}
        assert store.get_present_taxon_ids_for_cell("cell-b") == {303}
        assert store.get_present_taxon_ids_for_cell("missing") == set()
    finally:
        store.close()


def test_sqlite_store_contains_taxon_in_cell(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store_fixture(
        database_path,
        h3_resolution=5,
        rows=[
            ("cell-a", 101),
        ],
    )

    store = SQLiteSpeciesRangeStore(database_path)

    try:
        assert store.contains_taxon_in_cell(h3_cell="cell-a", taxon_id=101) is True
        assert store.contains_taxon_in_cell(h3_cell="cell-a", taxon_id=202) is False
        assert store.contains_taxon_in_cell(h3_cell="cell-b", taxon_id=101) is False
    finally:
        store.close()


def test_sqlite_store_reads_h3_resolution(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store_fixture(
        database_path,
        h3_resolution=7,
        rows=[],
    )

    store = SQLiteSpeciesRangeStore(database_path)

    try:
        assert store.get_h3_resolution() == 7
    finally:
        store.close()


def test_sqlite_store_requires_h3_resolution_metadata(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE range_store_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    store = SQLiteSpeciesRangeStore(database_path)

    try:
        with pytest.raises(ValueError, match="h3_resolution"):
            store.get_h3_resolution()
    finally:
        store.close()
