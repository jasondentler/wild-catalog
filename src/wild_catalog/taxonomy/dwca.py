import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from wild_catalog.core.config import Settings
from wild_catalog.taxonomy.store import InMemoryTaxonomyStore
from wild_catalog.taxonomy.types import CommonNameRecord, TaxonRecord

logger = logging.getLogger(__name__)

DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
DEFAULT_TAXONOMY_DWCA_FILENAME = "taxonomy.dwca.zip"


@dataclass(frozen=True, slots=True)
class DarwinCoreArchivePaths:
    archive_path: Path


def taxonomy_dwca_path_for_settings(settings: Settings) -> Path:
    return settings.taxonomy_dwca_path or (
        settings.taxonomy_store_path / DEFAULT_TAXONOMY_DWCA_FILENAME
    )


def download_taxonomy_dwca(
    settings: Settings,
    *,
    timeout_seconds: int = 600,
) -> Path:
    destination = taxonomy_dwca_path_for_settings(settings)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and destination.stat().st_size > 0:
        logger.info("Reusing downloaded taxonomy DarwinCore Archive %s", destination)
        return destination

    temporary_destination = destination.with_suffix(destination.suffix + ".tmp")

    logger.info(
        "Downloading taxonomy DarwinCore Archive %s to %s",
        settings.taxonomy_dwca_url,
        destination,
    )

    with urlopen(settings.taxonomy_dwca_url, timeout=timeout_seconds) as response:
        with temporary_destination.open("wb") as temporary_file:
            while chunk := response.read(DOWNLOAD_CHUNK_SIZE_BYTES):
                temporary_file.write(chunk)

    temporary_destination.replace(destination)
    logger.info("Downloaded taxonomy DarwinCore Archive %s", destination)

    return destination


def load_taxonomy_store_from_dwca(
    archive_path: Path,
) -> InMemoryTaxonomyStore:
    taxa_by_id: dict[int, TaxonRecord] = {}
    common_names_by_taxon_id: dict[int, list[CommonNameRecord]] = {}

    with ZipFile(archive_path) as archive:
        taxon_member_name = _find_member_name(
            archive,
            candidates=("taxa.csv", "taxon.csv", "Taxon.csv"),
        )
        vernacular_member_names = _find_vernacular_member_names(archive)
        legacy_vernacular_member_name = _find_member_name(
            archive,
            candidates=(
                "VernacularName.csv",
                "vernacular_names.csv",
                "vernacularNames.csv",
            ),
            required=False,
        )

        if legacy_vernacular_member_name is not None:
            vernacular_member_names = (
                legacy_vernacular_member_name,
                *vernacular_member_names,
            )

        with archive.open(taxon_member_name) as taxon_file:
            reader = csv.DictReader(line.decode("utf-8") for line in taxon_file)

            for row in reader:
                taxon_id = _required_taxon_id(row)
                parent_taxon_id = _optional_taxon_id(row.get("parentNameUsageID"))
                accepted_taxon_id = _optional_taxon_id(row.get("acceptedNameUsageID"))

                taxa_by_id[taxon_id] = TaxonRecord(
                    taxon_id=taxon_id,
                    scientific_name=row["scientificName"],
                    rank=row.get("taxonRank", ""),
                    parent_taxon_id=parent_taxon_id,
                    accepted_taxon_id=accepted_taxon_id,
                    is_active=row.get("taxonomicStatus", "accepted") == "accepted",
                )

        for vernacular_member_name in vernacular_member_names:
            with archive.open(vernacular_member_name) as vernacular_file:
                reader = csv.DictReader(line.decode("utf-8") for line in vernacular_file)

                for row in reader:
                    taxon_id = _required_common_name_taxon_id(row)
                    locale = row.get("language") or row.get("locale") or ""
                    name = row.get("vernacularName") or row.get("name") or ""

                    if not locale or not name:
                        continue

                    common_names_by_taxon_id.setdefault(taxon_id, []).append(
                        CommonNameRecord(
                            taxon_id=taxon_id,
                            locale=locale,
                            name=name,
                            source=row.get("source", ""),
                            lexicon=row.get("lexicon", ""),
                            created=row.get("created", ""),
                        )
                    )

    return InMemoryTaxonomyStore(
        taxa_by_id=taxa_by_id,
        common_names_by_taxon_id={
            taxon_id: tuple(records) for taxon_id, records in common_names_by_taxon_id.items()
        },
    )


def _find_member_name(
    archive: ZipFile,
    *,
    candidates: tuple[str, ...],
    required: bool = True,
) -> str | None:
    names_by_basename = {Path(name).name: name for name in archive.namelist()}

    for candidate in candidates:
        if candidate in names_by_basename:
            return names_by_basename[candidate]

    if required:
        raise ValueError(
            f"DarwinCore Archive is missing required member. Tried: {', '.join(candidates)}"
        )

    return None


def _find_vernacular_member_names(archive: ZipFile) -> tuple[str, ...]:
    return tuple(
        name
        for name in archive.namelist()
        if Path(name).name.startswith("VernacularNames-") and Path(name).suffix.lower() == ".csv"
    )


def _required_taxon_id(row: dict[str, str]) -> int:
    return _required_int(row.get("id") or row.get("taxonID"), field_name="id")


def _required_common_name_taxon_id(row: dict[str, str]) -> int:
    return _required_int(
        row.get("id") or row.get("taxon_id") or row.get("taxonID"),
        field_name="taxon_id",
    )


def _optional_taxon_id(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None

    return _required_int(value, field_name="taxon_id")


def _required_int(value: str | None, *, field_name: str) -> int:
    if value is None or value.strip() == "":
        raise ValueError(f"DarwinCore Archive row is missing required {field_name}.")

    normalized_value = value.strip().rstrip("/").rsplit("/", maxsplit=1)[-1]

    return int(normalized_value)
