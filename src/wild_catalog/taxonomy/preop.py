from wild_catalog.core.config import Settings
from wild_catalog.taxonomy.dwca import download_taxonomy_dwca


def preop_taxonomy_dwca(settings: Settings | None = None) -> None:
    settings = settings or Settings.from_env()
    download_taxonomy_dwca(settings)


def main() -> None:
    preop_taxonomy_dwca()


if __name__ == "__main__":
    main()
