import csv
import logging
import sqlite3
import zipfile
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path

from wild_catalog.taxonomy.vernacular_language_code_to_csv import (
    VERNACULAR_LANGUAGE_CODE_TO_CSV_FILES,
)
from wild_catalog.wildlife_detection.model_download import download_file_with_progress

logger = logging.getLogger("uvicorn.error")

DEFAULT_TAXONOMY_DWCA_URL = "https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip"
DEFAULT_TAXONOMY_LANGUAGES = ("en-US",)


def _normalize_language_code(language: str) -> str:
    return language.strip().replace("_", "-").lower()


_LANGUAGE_TO_CSV_FILES = {
    _normalize_language_code(language): filenames
    for language, filenames in VERNACULAR_LANGUAGE_CODE_TO_CSV_FILES.items()
}


@dataclass(frozen=True, slots=True)
class TaxonomyImportResult:
    taxa_imported: int
    vernacular_names_imported: int


def import_taxonomy_archive_if_missing(
    target_database_path: str | Path,
    download_dir: str | Path,
    *,
    archive_url: str = DEFAULT_TAXONOMY_DWCA_URL,
    languages: Iterable[str] = DEFAULT_TAXONOMY_LANGUAGES,
) -> TaxonomyImportResult:
    target_path = Path(target_database_path)
    if target_path.exists():
        logger.info("iNaturalist taxonomy store already exists at %s", target_path)
        return TaxonomyImportResult(taxa_imported=0, vernacular_names_imported=0)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    archive_path = download_file_with_progress(
        archive_url,
        download_path / _filename_from_url(archive_url),
    )

    temporary_target_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
    _unlink_sqlite_database_files(temporary_target_path)
    try:
        result = import_taxonomy_archive(
            temporary_target_path,
            archive_path,
            languages=languages,
        )
        temporary_target_path.replace(target_path)
        return result
    finally:
        _unlink_sqlite_database_files(temporary_target_path)


def create_taxonomy_store_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS taxonomy_taxa (
            taxon_id INTEGER PRIMARY KEY,
            parent_taxon_id INTEGER,
            accepted_taxon_id INTEGER,
            rank TEXT NOT NULL,
            scientific_name TEXT NOT NULL,
            display_name TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_taxonomy_taxa_scientific_name
        ON taxonomy_taxa (scientific_name);

        CREATE INDEX IF NOT EXISTS idx_taxonomy_taxa_parent_taxon_id
        ON taxonomy_taxa (parent_taxon_id);

        CREATE TABLE IF NOT EXISTS taxonomy_vernacular_names (
            taxon_id INTEGER NOT NULL,
            language_code TEXT NOT NULL,
            vernacular_name TEXT NOT NULL,
            position INTEGER NOT NULL,
            PRIMARY KEY (taxon_id, language_code, vernacular_name)
        );

        CREATE INDEX IF NOT EXISTS idx_taxonomy_vernacular_names_lookup
        ON taxonomy_vernacular_names (taxon_id, language_code, position);

        CREATE TABLE IF NOT EXISTS taxonomy_store_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def _drop_taxonomy_store_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS taxonomy_vernacular_names;
        DROP TABLE IF EXISTS taxonomy_taxa;
        DROP TABLE IF EXISTS taxonomy_store_metadata;
        """
    )


def import_taxonomy_archive(
    target_database_path: str | Path,
    archive_path: str | Path,
    *,
    languages: Iterable[str] = DEFAULT_TAXONOMY_LANGUAGES,
) -> TaxonomyImportResult:
    with closing(sqlite3.connect(target_database_path)) as connection:
        _configure_connection(connection)
        with connection:
            _drop_taxonomy_store_schema(connection)
            create_taxonomy_store_schema(connection)
            taxa_imported = _import_taxa(connection, archive_path)
            vernacular_names_imported = _import_vernacular_names(
                connection,
                archive_path,
                languages,
            )
            connection.executemany(
                """
                INSERT INTO taxonomy_store_metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                [
                    ("source", str(archive_path)),
                    (
                        "languages",
                        ",".join(_normalized_language_preferences(languages)),
                    ),
                ],
            )
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    return TaxonomyImportResult(
        taxa_imported=taxa_imported,
        vernacular_names_imported=vernacular_names_imported,
    )


def vernacular_csv_files_for_languages(languages: Iterable[str]) -> tuple[tuple[str, str], ...]:
    files: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for language in _normalized_language_preferences(languages):
        resolved_language = language
        filenames = _LANGUAGE_TO_CSV_FILES.get(language)
        if filenames is None and "-" in language:
            resolved_language = language.split("-", maxsplit=1)[0]
            filenames = _LANGUAGE_TO_CSV_FILES.get(resolved_language)

        for filename in filenames or ():
            item = (resolved_language, filename)
            if item not in seen:
                seen.add(item)
                files.append(item)

    return tuple(files)


def _import_taxa(connection: sqlite3.Connection, archive_path: str | Path) -> int:
    rows = []
    with _open_archive_member(archive_path, "taxa.csv") as taxa_file:
        reader = csv.DictReader(taxa_file)
        for row in reader:
            taxon_id = _optional_taxon_id(_field(row, "taxonID", "id"))
            scientific_name = _field(row, "scientificName", "name")
            if taxon_id is None or not scientific_name:
                continue

            rank = (_field(row, "taxonRank", "rank") or "unknown").lower()
            rows.append(
                (
                    taxon_id,
                    _optional_taxon_id(_field(row, "parentNameUsageID", "parentID")),
                    _optional_taxon_id(_field(row, "acceptedNameUsageID", "acceptedID")),
                    rank,
                    scientific_name,
                    _display_name_for_rank(scientific_name, rank),
                )
            )

    connection.executemany(
        """
        INSERT INTO taxonomy_taxa (
            taxon_id,
            parent_taxon_id,
            accepted_taxon_id,
            rank,
            scientific_name,
            display_name
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def _import_vernacular_names(
    connection: sqlite3.Connection,
    archive_path: str | Path,
    languages: Iterable[str],
) -> int:
    imported = 0

    for language_code, filename in vernacular_csv_files_for_languages(languages):
        try:
            with _open_archive_member(archive_path, filename) as vernacular_file:
                rows = _vernacular_rows(vernacular_file, language_code)
        except FileNotFoundError:
            logger.warning("Vernacular names file %s not found in %s", filename, archive_path)
            continue

        connection.executemany(
            """
            INSERT OR IGNORE INTO taxonomy_vernacular_names (
                taxon_id,
                language_code,
                vernacular_name,
                position
            )
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        imported += len(rows)

    return imported


def _vernacular_rows(
    vernacular_file: TextIOWrapper,
    language_code: str,
) -> list[tuple[int, str, str, int]]:
    rows = []
    reader = csv.DictReader(vernacular_file)
    for position, row in enumerate(reader):
        taxon_id = _optional_taxon_id(_field(row, "taxonID", "id"))
        vernacular_name = _field(row, "vernacularName", "name")
        if taxon_id is None or not vernacular_name:
            continue
        rows.append((taxon_id, language_code, vernacular_name, position))

    return rows


@contextmanager
def _open_archive_member(
    archive_path: str | Path,
    member_name: str,
) -> Iterator[TextIOWrapper]:
    path = Path(archive_path)
    if path.is_dir():
        member_path = path / member_name
        if not member_path.exists():
            raise FileNotFoundError(member_name)
        with member_path.open("r", encoding="utf-8-sig", newline="") as file:
            yield file
        return

    with zipfile.ZipFile(path) as archive:
        try:
            member = archive.open(member_name)
        except KeyError as exc:
            raise FileNotFoundError(member_name) from exc
        with member, TextIOWrapper(member, encoding="utf-8-sig", newline="") as file:
            yield file


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA cache_size = -100000")


def _field(row: dict[str, str | None], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None and value.strip():
            return value.strip()
    return ""


def _optional_int(value: str) -> int | None:
    if not value:
        return None
    return int(value)


def _optional_taxon_id(value: str) -> int | None:
    if not value:
        return None

    token = value.rstrip("/").rsplit("/", maxsplit=1)[-1]
    return int(token)


def _display_name_for_rank(scientific_name: str, rank: str) -> str:
    if rank in {"species", "subspecies"}:
        return scientific_name.replace(" ssp. ", " ").split()[-1]
    return scientific_name


def _normalized_language_preferences(languages: Iterable[str]) -> tuple[str, ...]:
    normalized = []
    seen = set()
    for language in languages:
        code = _normalize_language_code(language)
        if code and code not in seen:
            seen.add(code)
            normalized.append(code)
    return tuple(normalized)


def _filename_from_url(url: str) -> str:
    filename = url.rsplit("/", maxsplit=1)[-1].split("?", maxsplit=1)[0]
    return filename or "taxonomy.dwca.zip"


def _unlink_sqlite_database_files(database_path: Path) -> None:
    for path in (
        database_path,
        database_path.with_name(f"{database_path.name}-wal"),
        database_path.with_name(f"{database_path.name}-shm"),
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
