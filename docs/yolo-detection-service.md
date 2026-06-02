[Architecture](./architecture.md)

# YOLO Detection Service
* **Responsibility**: Locates broad, target ecological subjects (fauna, flora, fungi) inside the frame, defining spatial boundaries so the system ignores non-relevant backgrounds.
* **Technical Stack**: `ultralytics` framework, PyTorch, Nvidia CUDA / Apple Silicon MPS hardware acceleration.

## Operation: `locate_objects`
* **Description**: Instantiates the lightweight `yolo11n.pt` (YOLO11 nano) model footprint lazily on first use and loads it onto the preferred local device: Apple Silicon MPS first, CUDA GPU second, and CPU last. The normalized Pillow image is fed into the tensor runtime to execute fast spatial regression.
* **Inputs**:
  * `normalized_image` (PIL.Image Object): The standardized 3-channel source bitmap.
* **Outputs**:
  * `raw_bounding_boxes` (List of Arrays / Tensor): A collection of structural predictions, where each detected target outputs an array containing `[xmin, ymin, xmax, ymax, confidence_score, class_id]`.

## COCO Class Filtering

YOLO11 nano is COCO-pretrained, so detection is limited to the COCO object
classes. The service keeps every COCO class that can represent a candidate
living organism for this application, excluding `person`: `bird`, `cat`, `dog`,
`horse`, `sheep`, `cow`, `elephant`, `bear`, `zebra`, `giraffe`, and the coarse
`potted plant` class. Other COCO objects, including people and non-living
objects, are filtered out before downstream cropping.

Fungi, many wild plants, amphibians, reptiles, fish, and invertebrates are not
reliably represented by COCO detection classes. Those biological distinctions
are refined later by classification rather than exposed as detection-time API
filters.
