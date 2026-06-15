# Detection Processing Pipeline

The detection processing pipeline accepts one deduplicated wildlife detection and the normalized image, crops the image around the detection, classifies the crop, and returns one identified object structure for the identify response.

The current implementation wires image cropping and Birder-backed species classification into this pipeline. The API dependency layer passes the same device selected for wildlife detection into the species classifier.
