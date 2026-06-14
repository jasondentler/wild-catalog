# Detection Deduplication

Filters redundant or nearly identical detection boxes for the same broad organism candidate.

The service accepts an iterable of project `Detection` objects and returns a list with lower-confidence duplicates removed.

## Matching Rule

Two detections are considered duplicate candidates when they have compatible broad classes and their bounding boxes overlap above the configured IoU threshold.

Class compatibility is true when:

* the detector class ids match, or
* both detections have non-empty labels that normalize to the same case-insensitive value

## IoU Threshold

The default threshold is:

```text
0.45
```

The service calculates intersection over union for each candidate box against boxes already selected in confidence order. If IoU is greater than the threshold, the lower-confidence candidate is discarded.

The returned list is sorted back into the original input order for the retained detections.
