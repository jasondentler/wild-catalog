from wild_catalog.core.settings import Settings
from wild_catalog.species_classifier.classifier import SpeciesClassifier


def main() -> None:
    SpeciesClassifier(Settings.from_env())


if __name__ == "__main__":
    main()
