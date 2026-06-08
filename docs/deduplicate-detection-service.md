[Architecture](./architecture.md)

# Duplicate Detection Service

## Responsibility

The duplicate detection service filters redundant or nearly identical detections before cropping and classification. This reduces memory use, avoids duplicate API response entries, and prevents the classifier from doing repeated work on the same organism.

## Technical Stack

* Python spatial logic
* Optional NumPy acceleration if it improves clarity or performance

## Operation: `filter_overlapping_detections`

### Description

The service receives normalized `Detection` objects from the active detector plugin. It calculates Intersection over Union (IoU) between neighboring detections. When overlapping detections represent the same broad subject and exceed the configured IoU threshold, the service keeps one detection and discards the duplicate.

With open-vocabulary detectors, a single organism may be detected under multiple labels. For example:

* `bird` and `animal`
* `flower` and `plant`
* `mushroom` and `fungus`

For this reason, deduplication should group by normalized detection category rather than exact raw label.

### Inputs

* `raw_detections`: List of `Detection` objects from the active detector plugin.

### Outputs

* `filtered_detections`: List of deduplicated `Detection` objects.

## Default policy

1. Group detections by `Detection.category`.
2. Sort each group by confidence descending.
3. Compare candidates using IoU.
4. If IoU is greater than the configured threshold, keep one detection.
5. Prefer higher confidence.
6. When confidence is close, prefer the more specific label.

Default IoU threshold:

```text
0.45
```

## Specificity tie-breaker

A model may return both broad and specific labels for the same organism. When two detections overlap strongly and confidence scores are close, prefer the more specific label.

Example ranking:

```python
SPECIFICITY_RANK = {
    "butterfly": 3,
    "moth": 3,
    "beetle": 3,
    "dragonfly": 3,
    "spider": 3,
    "snail": 3,
    "bird": 3,
    "mammal": 3,
    "reptile": 3,
    "amphibian": 3,
    "fish": 3,
    "flower": 3,
    "tree": 3,
    "leaf": 3,
    "grass": 3,
    "moss": 3,
    "lichen": 3,
    "mushroom": 3,

    "insect": 2,
    "plant": 2,
    "fungus": 2,

    "animal": 1,
}
```

The exact ranking should remain configuration-friendly because detector behavior may change as models improve.

## Performance notes

The input list should already be capped by `WILD_CATALOG_MAX_DETECTIONS`, so a simple readable implementation is preferred over complex spatial indexing. Optimize only if benchmarks show the deduplication stage matters.

## Integration with real detector output

Once Grounding DINO is implemented, deduplication tests should include realistic overlapping open-vocabulary labels such as `bird` + `animal`, `flower` + `plant`, and `mushroom` + `fungus`.

Deduplication remains detector-agnostic. It should never import Grounding DINO classes directly. It should operate only on stable `Detection` objects.
