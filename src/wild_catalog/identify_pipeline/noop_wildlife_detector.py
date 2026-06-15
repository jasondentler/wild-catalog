class NoopWildlifeDetector:
    def detect(self, normalized_image: object) -> list[object]:
        _ = normalized_image
        return []
