[Architecture](./architecture.md)

# Logit Conditioning Layer

## Responsibility

The logit conditioning layer adjusts raw classifier outputs using geographic context without changing the classifier model itself. It is intentionally separated from the classifier so classifier plugins can remain model-specific while geographic priors remain pipeline-level behavior.

## Technical Stack

* PyTorch
* CUDA, Apple Silicon MPS, or CPU through the shared device helper

## Operation: `apply_geographic_prior`

### Description

The layer takes unconditioned raw logits from the active classifier plugin and applies an additive log-space shift using a spatial prior mask.

```text
z_conditioned = z_raw + gamma * log(G + epsilon)
```

Then it applies Softmax to produce final probabilities.

This can push geographically unlikely species downward while allowing visually plausible, location-compatible alternatives to move upward.

### Inputs

* `raw_logits`: Tensor of shape `[M, N]`, where `M` is the number of detected crops and `N` is the active classifier class count.
* `spatial_prior_mask`: Tensor of shape `[N]`, aligned to the active classifier class index.
* `gamma`: Tunable scalar controlling prior strength.
* `epsilon`: Underflow floor.
* `top_k`: Number of candidates retained per crop.

### Outputs

* `conditioned_predictions`: Top-k class indices and probabilities per crop.

## Compatibility requirements

The conditioning layer assumes:

1. The classifier output is raw logits.
2. The prior mask length matches the classifier score width.
3. Prior-mask indices match classifier class indices exactly.

If a future classifier plugin can only return probabilities, the adapter should either expose logits if possible or opt out of geographic logit conditioning.

## Testing

Unit tests should cover:

* Shape validation.
* Missing-GPS all-ones prior behavior.
* Epsilon clamping.
* Gamma effects.
* Top-k ordering.
* Device and dtype consistency.

## Relationship to confidence filtering

The conditioning layer should remain focused on transforming raw logits into conditioned probabilities and top-k class predictions.

Final result-quality policy belongs after conditioning. That later policy may decide:

```text
minimum final confidence
minimum number of returned predictions
maximum number of returned predictions
whether to suppress low-confidence alternatives
whether to return an uncertain result when all predictions are weak
```

Do not put API response filtering, taxonomy lookup, or confidence-threshold policy inside the classifier plugin or inside the logit conditioner.
