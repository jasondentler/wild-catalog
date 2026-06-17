from wild_catalog.core.settings import Settings
from wild_catalog.range_data.inaturalist_open_range_importer import (
    import_inaturalist_open_range_data_if_missing,
)


def main() -> None:
    settings = Settings.from_env()
    import_inaturalist_open_range_data_if_missing(
        settings.range_store_database_path,
        settings.range_geopackage_download_dir,
    )


if __name__ == "__main__":
    main()
