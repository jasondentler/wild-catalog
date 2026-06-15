# Detection Processing Pipeline

The detection processing pipeline accepts one deduplicated wildlife detection and the normalized image, crops the image around the detection, and returns one identified object structure for the identify response.

The current implementation wires image cropping into this pipeline and maps the retained detection into the response object. Future detection processing stages remain out of scope.
