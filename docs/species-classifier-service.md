[Architecture](./architecture.md)

# Species Classifier Service
* **Responsibility**: Computes highly detailed fine-grained taxonomic predictions for the targeted visual crops.
* **Technical Stack**: `birder`, PyTorch, Nvidia CUDA / Apple Silicon MPS hardware acceleration.

## Operation: `predict_species`
* **Description**: Loads the specialized `hieradet_d_small_dino-v2-inat21` vision transformer architecture lazily on the first real-model request. The model is moved to the shared PyTorch device helper result, put in evaluation mode (`.eval()`), and evaluated under `torch.no_grad()`. Device selection follows the shared helper: native macOS MPS first, CUDA second, and CPU last; MPS is disabled when running inside Docker because standard Docker containers do not expose Apple Metal Performance Shaders to PyTorch. Each cropped RGB image is transformed with Birder's model signature size and RGB normalization statistics, then crops are batched for inference.
* **Inputs**:
  * `cropped_images` (List of PIL.Image Objects): Individual isolated RGB organism snapshots.
* **Outputs**:
  * `RawClassifierOutput`: Raw, unconditioned logits for each crop. These are not softmax probabilities; geographic conditioning can modify the logits before final probabilities are computed.

## Implementations
* `SpeciesClassifier`: Protocol exposing `predict_species(cropped_images) -> RawClassifierOutput`.
* `StubSpeciesClassifier`: Deterministic fixture classifier used by API contract and default integration tests. It emits logits for the fixture class indices in `data/class_index.py`, allowing the pipeline to exercise taxonomy enrichment without model downloads.
* `BirderSpeciesClassifier`: Production adapter for `birder.load_pretrained_model("hieradet_d_small_dino-v2-inat21", inference=True)`. Wild Catalog depends on this model's logits and iNaturalist 2021 class-index ordering; other Birder models are not supported by this service contract.

## Configuration
Environment variables:

* `WILD_CATALOG_SPECIES_CLASSIFIER_MODEL_CACHE_PATH`: Optional local model cache path. The Birder adapter applies this as Birder's `DATA_DIR` while loading the model.
* `WILD_CATALOG_SPECIES_CLASSIFIER_BATCH_SIZE`: Real-model crop batch size. Defaults to `8`.
* `WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K`: Number of classifier candidates returned per detection before taxonomy enrichment. Defaults to `12`.

## Testing
Default unit tests use `StubSpeciesClassifier` and do not require Birder, PyTorch, or model weights. Real-model integration tests are skipped unless `WILD_CATALOG_RUN_REAL_MODEL_TESTS=1` is set. When that flag is set, missing model dependencies or unavailable weights fail the suite with setup/cache guidance.
