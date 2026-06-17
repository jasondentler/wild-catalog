from wild_catalog.range_data.preop import main as import_range_maps
from wild_catalog.species_classifier.preop import main as prepare_classifier_model
from wild_catalog.taxonomy.preop import main as import_taxonomy_dwca
from wild_catalog.wildlife_detection.preop import main as prepare_detector_model


def main() -> None:
    import_taxonomy_dwca()
    import_range_maps()
    prepare_classifier_model()
    prepare_detector_model()


if __name__ == "__main__":
    main()
