[Architecture](./architecture.md)

# Image Conversion Service
* **Responsibility**: Ingests completely blind binary data streams without needing file extensions. It extracts embedded EXIF metadata (specifically looking for GPS telemetry and original timestamp) to feed downstream logic, and normalizes multi-format image structures into a standard RGB pixel layout.
* **Technical Stack**: `Pillow`, `rawpy`, `pillow-heif`, `exifread`.

## Operation: `process_and_extract_metadata`
* **Description**: Lazily scans the first few bytes of the incoming binary stream to infer the image type by analyzing format-specific headers. Standard web photos (JPEG, PNG, WebP) are processed using Pillow, while professional RAW files (such as Canon CR3, CR2, NEF, ARW, DNG) are decoded through `rawpy` using automatic white balance variables. 

During ingestion, the service extracts structural EXIF blocks to retrieve the original capture device file name and spatial telemetry coordinates (converting latitude/longitude degrees, minutes, and seconds into floating-point decimals). Finally, it executes an explicit `.convert("RGB")` transform to ensure an uncompromised 3-channel layout is passed to the downstream model layers.
* **Inputs**:
  * `file_bytes` (Binary Stream): A raw, unparsed array of the uploaded photograph.
* **Outputs**:
  * `normalized_image` (PIL.Image Object): A unified 3-channel (RGB) in-memory pixel matrix compatible with Pillow and downstream models.
  * `original_filename` (String / None): The source file name assigned by the camera hardware at the moment of capture, extracted from the EXIF dictionary.
  * `gps_coordinates` (Tuple of Floats / None): A decimal pair structure `(latitude, longitude)` representing the physical telemetry location, ready for the GPS Location Booster.
