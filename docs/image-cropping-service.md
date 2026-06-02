[Architecture](./architecture.md)

# Image Cropping Service
* **Responsibility**: Isolates individual targets into specialized sub-images, providing a canvas context focused entirely on the subject to optimize classifier accuracy.
* **Technical Stack**: `Pillow` (Coordinate slicing primitives).

## Operation: `extract_target_regions`
* **Description**: Loops through the deduplicated coordinates list. It reads the source `normalized_image` matrix and cuts out isolated target snapshots. The algorithm dynamically calculates an explicit pixel padding margin around the bounding borders (clamping to `0` and maximum width/height constraints) to prevent cutting off critical diagnostic features of plants, wings, or fungal caps.
* **Inputs**:
  * `normalized_image` (PIL.Image Object): The complete source bitmap.
  * `filtered_bounding_boxes` (List of Arrays): Coordinates of chosen targets.
* **Outputs**:
  * `cropped_images` (List of PIL.Image Objects): An ordered collection of independent, isolated target image objects. Crucially, because the source was converted upfront, these crops natively retain pure **RGB format**.
