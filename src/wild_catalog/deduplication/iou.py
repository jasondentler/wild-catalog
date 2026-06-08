from wild_catalog.core.types import BoundingBox


def calculate_iou(a: BoundingBox, b: BoundingBox) -> float:
    x_left = max(a.xmin, b.xmin)
    y_top = max(a.ymin, b.ymin)
    x_right = min(a.xmax, b.xmax)
    y_bottom = min(a.ymax, b.ymax)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    a_area = a.width * a.height
    b_area = b.width * b.height
    union_area = a_area + b_area - intersection_area

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area
