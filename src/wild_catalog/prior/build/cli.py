import logging

from wild_catalog.core.config import Settings
from wild_catalog.prior.build.builder import build_inat21_range_map_store


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    database_path = build_inat21_range_map_store(settings)
    print(f"Built iNat21 range-map SQLite store: {database_path}")


if __name__ == "__main__":
    main()
