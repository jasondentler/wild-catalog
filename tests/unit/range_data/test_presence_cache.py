from wild_catalog.core.types import GpsCoordinates
from wild_catalog.range_data.presence_cache import PresenceCache


def test_presence_cache_rejects_non_positive_max_entries() -> None:
    try:
        PresenceCache(max_entries=0)
    except ValueError as exc:
        assert str(exc) == "max_entries must be positive."
    else:
        raise AssertionError("Expected ValueError")


def test_presence_cache_key_uses_h3_resolution() -> None:
    gps_coordinates = GpsCoordinates(latitude=29.573361, longitude=-94.389507)

    assert (
        PresenceCache.presence_cache_key(gps_coordinates, h3_resolution=7)
        != PresenceCache.presence_cache_key(gps_coordinates, h3_resolution=8)
    )


def test_presence_cache_stores_copies_of_cached_sets() -> None:
    cache = PresenceCache(max_entries=2)

    cache.put("key", {1, 2})
    cached = cache.get("key")

    assert cached == {1, 2}
    assert cached is not None
    cached.add(3)

    assert cache.get("key") == {1, 2}


def test_presence_cache_returns_none_for_missing_key() -> None:
    cache = PresenceCache(max_entries=2)

    assert cache.get("missing") is None


def test_presence_cache_evicts_least_recently_used_entry() -> None:
    cache = PresenceCache(max_entries=2)
    cache.put("first", {1})
    cache.put("second", {2})

    assert cache.get("first") == {1}

    cache.put("third", {3})

    assert cache.get("first") == {1}
    assert cache.get("second") is None
    assert cache.get("third") == {3}
