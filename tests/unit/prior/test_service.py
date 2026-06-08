import pytest
import torch
from shapely import to_wkb
from shapely.geometry import Polygon

from wild_catalog.classifier.types import ClassIndex
from wild_catalog.core.config import Settings
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.service import SpeciesRangePriorService
from wild_catalog.prior.stub import StubSpeciesRangeStore


def test_generate_prior_mask_returns_all_ones_when_gps_missing() -> None:
    service = SpeciesRangePriorService(
        Settings(prior_epsilon=0.01),
        store=StubSpeciesRangeStore(),
    )
    class_index = ClassIndex(
        id="stub",
        taxon_id_by_class_id={
            0: 101,
            1: 202,
            2: 303,
        },
    )

    prior_mask = service.generate_prior_mask(
        gps_coordinates=None,
        class_index=class_index,
    )

    assert prior_mask.class_index_id == "stub"
    assert torch.equal(prior_mask.values, torch.ones(3))


def test_get_presence_for_taxa_returns_true_when_gps_missing() -> None:
    service = SpeciesRangePriorService(
        Settings(),
        store=StubSpeciesRangeStore(),
    )

    presence = service.get_presence_for_taxa(
        gps_coordinates=None,
        taxon_ids={101, 202},
    )

    assert presence.is_present_by_taxon_id == {
        101: True,
        202: True,
    }


def test_generate_prior_mask_uses_present_taxa_when_gps_exists() -> None:
    gps_coordinates = GpsCoordinates(latitude=29.7604, longitude=-95.3698)

    service = SpeciesRangePriorService(
        Settings(prior_epsilon=0.01, range_prior_cache_enabled=False),
        store=StubSpeciesRangeStore(
            candidate_geometries=[
                (101, to_wkb(_box(-96.0, 29.0, -95.0, 30.0))),
                (202, to_wkb(_box(-80.0, 20.0, -79.0, 21.0))),
                (303, to_wkb(_box(-96.0, 29.0, -95.0, 30.0))),
            ],
        ),
    )
    class_index = ClassIndex(
        id="stub",
        taxon_id_by_class_id={
            0: 101,
            1: 202,
            2: 303,
        },
    )

    prior_mask = service.generate_prior_mask(
        gps_coordinates=gps_coordinates,
        class_index=class_index,
    )

    assert prior_mask.class_index_id == "stub"
    assert torch.equal(
        prior_mask.values,
        torch.tensor([1.0, 0.01, 1.0], dtype=torch.float32),
    )


def test_get_presence_for_taxa_uses_range_store_when_gps_exists() -> None:
    gps_coordinates = GpsCoordinates(latitude=29.7604, longitude=-95.3698)

    service = SpeciesRangePriorService(
        Settings(range_prior_cache_enabled=False),
        store=StubSpeciesRangeStore(
            candidate_geometries=[
                (101, to_wkb(_box(-96.0, 29.0, -95.0, 30.0))),
                (202, to_wkb(_box(-80.0, 20.0, -79.0, 21.0))),
            ],
        ),
    )

    presence = service.get_presence_for_taxa(
        gps_coordinates=gps_coordinates,
        taxon_ids={101, 202},
    )

    assert presence.is_present_by_taxon_id == {
        101: True,
        202: False,
    }


def test_generate_prior_mask_rejects_non_contiguous_class_index() -> None:
    service = SpeciesRangePriorService(
        Settings(),
        store=StubSpeciesRangeStore(),
    )
    class_index = ClassIndex(
        id="bad",
        taxon_id_by_class_id={
            0: 101,
            2: 202,
        },
    )

    with pytest.raises(ValueError, match="contiguous class IDs"):
        service.generate_prior_mask(
            gps_coordinates=None,
            class_index=class_index,
        )


def _box(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Polygon:
    return Polygon(
        [
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat),
        ]
    )
