import string
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from wild_catalog.core.types import BoundingBox
from wild_catalog.detection.types import Detection, DetectionCategory

ANIMAL_LABELS = frozenset(
    {
        "animal",
        "amphibian",
        "beetle",
        "bird",
        "butterfly",
        "dragonfly",
        "fish",
        "insect",
        "mammal",
        "moth",
        "reptile",
        "snail",
        "spider",
    }
)
PLANT_LABELS = frozenset({"flower", "grass", "leaf", "moss", "plant", "tree"})
FUNGUS_LABELS = frozenset({"fungus", "mushroom"})
LICHEN_LABELS = frozenset({"lichen"})


@dataclass(frozen=True, slots=True)
class GroundingDinoPrediction:
    box: tuple[float, float, float, float]
    score: float
    label: str


def postprocess_grounding_dino_predictions(
    predictions: Iterable[GroundingDinoPrediction],
    *,
    image_width: int,
    image_height: int,
    confidence_threshold: float,
    boxes_are_normalized_cxcywh: bool,
    source: str = "grounding-dino",
) -> list[Detection]:
    detections: list[Detection] = []

    for prediction in predictions:
        if prediction.score < confidence_threshold:
            continue

        label = normalize_detection_label(prediction.label)
        category = detection_category_for_label(label)

        if category is None:
            continue

        bounding_box = (
            normalized_cxcywh_to_bounding_box(
                prediction.box,
                image_width=image_width,
                image_height=image_height,
            )
            if boxes_are_normalized_cxcywh
            else xyxy_to_bounding_box(
                prediction.box,
                image_width=image_width,
                image_height=image_height,
            )
        )

        if bounding_box is None:
            continue

        detections.append(
            Detection(
                bounding_box=bounding_box,
                confidence=float(prediction.score),
                label=label,
                category=category,
                source=source,
            )
        )

    return sorted(detections, key=lambda detection: detection.confidence, reverse=True)


def normalize_detection_label(label: str) -> str:
    normalized = label.casefold().strip()
    normalized = normalized.translate(str.maketrans("", "", string.punctuation))
    return " ".join(normalized.split())


def detection_category_for_label(label: str) -> DetectionCategory | None:
    words = set(label.split())

    if words & ANIMAL_LABELS:
        return DetectionCategory.ANIMAL

    if words & PLANT_LABELS:
        return DetectionCategory.PLANT

    if words & FUNGUS_LABELS:
        return DetectionCategory.FUNGUS

    if words & LICHEN_LABELS:
        return DetectionCategory.LICHEN

    return None


def normalized_cxcywh_to_bounding_box(
    box: Sequence[float],
    *,
    image_width: int,
    image_height: int,
) -> BoundingBox | None:
    center_x, center_y, width, height = box
    xmin = (center_x - width / 2) * image_width
    ymin = (center_y - height / 2) * image_height
    xmax = (center_x + width / 2) * image_width
    ymax = (center_y + height / 2) * image_height

    return xyxy_to_bounding_box(
        (xmin, ymin, xmax, ymax),
        image_width=image_width,
        image_height=image_height,
    )


def xyxy_to_bounding_box(
    box: Sequence[float],
    *,
    image_width: int,
    image_height: int,
) -> BoundingBox | None:
    xmin, ymin, xmax, ymax = box

    bounding_box = BoundingBox(
        xmin=_clamp(round(xmin), minimum=0, maximum=image_width),
        ymin=_clamp(round(ymin), minimum=0, maximum=image_height),
        xmax=_clamp(round(xmax), minimum=0, maximum=image_width),
        ymax=_clamp(round(ymax), minimum=0, maximum=image_height),
    )

    if bounding_box.width <= 0 or bounding_box.height <= 0:
        return None

    return bounding_box


def _clamp(value: int, *, minimum: int, maximum: int) -> int:
    return min(max(value, minimum), maximum)
