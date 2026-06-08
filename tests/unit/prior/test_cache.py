import pytest

from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.cache import PresenceCache, presence_cache_key


def test_presence_cache_returns_copies_and_tracks_recent_use() -> None:
    cache = PresenceCache(max_entries=2)

    cache.put("a", {101})
    cache.put("b", {202})

    cached = cache.get("a")
    assert cached == {101}

    assert cached is not None
    cached.add(303)

    cache.put("c", {303})

    assert cache.get("a") == {101}
    assert cache.get("b") is None
    assert cache.get("c") == {303}


def test_presence_cache_rejects_non_positive_max_entries() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        PresenceCache(max_entries=0)


def test_presence_cache_key_uses_h3_resolution() -> None:
    gps_coordinates = GpsCoordinates(latitude=29.7604, longitude=-95.3698)

    assert presence_cache_key(gps_coordinates, h3_resolution=4) != presence_cache_key(
        gps_coordinates,
        h3_resolution=5,
    )
