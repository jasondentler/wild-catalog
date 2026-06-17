from wild_catalog.core.settings import Settings
from wild_catalog.taxonomy.taxonomy_importer import import_taxonomy_archive_if_missing


def main() -> None:
    settings = Settings.from_env()
    import_taxonomy_archive_if_missing(
        settings.taxonomy_store_database_path,
        settings.taxonomy_archive_download_dir,
        languages=settings.taxonomy_languages,
    )


if __name__ == "__main__":
    main()
