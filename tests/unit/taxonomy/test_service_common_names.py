from wild_catalog.taxonomy.service import _select_common_name
from wild_catalog.taxonomy.types import CommonNameRecord


def test_select_common_name_uses_requested_locale_exact_match() -> None:
    result = _select_common_name(
        common_names=(
            CommonNameRecord(taxon_id=1, locale="en-US", name="American Bird"),
            CommonNameRecord(taxon_id=1, locale="en", name="English Bird"),
        ),
        scientific_name="Aves",
        requested_locale="en-US",
        default_locale="en",
    )

    assert result == "American Bird"


def test_select_common_name_uses_requested_language_without_region() -> None:
    result = _select_common_name(
        common_names=(
            CommonNameRecord(taxon_id=1, locale="es", name="Ave"),
            CommonNameRecord(taxon_id=1, locale="en", name="Bird"),
        ),
        scientific_name="Aves",
        requested_locale="es-MX",
        default_locale="en-US",
    )

    assert result == "Ave"


def test_select_common_name_uses_default_locale() -> None:
    result = _select_common_name(
        common_names=(
            CommonNameRecord(taxon_id=1, locale="fr", name="Oiseau"),
            CommonNameRecord(taxon_id=1, locale="en-US", name="Bird"),
        ),
        scientific_name="Aves",
        requested_locale="de-DE",
        default_locale="en-US",
    )

    assert result == "Bird"


def test_select_common_name_uses_any_english_name() -> None:
    result = _select_common_name(
        common_names=(CommonNameRecord(taxon_id=1, locale="en-GB", name="Bird"),),
        scientific_name="Aves",
        requested_locale="de-DE",
        default_locale="es-MX",
    )

    assert result == "Bird"


def test_select_common_name_prefers_newer_dwca_common_name_within_fallback_tier() -> None:
    result = _select_common_name(
        common_names=(
            CommonNameRecord(
                taxon_id=1,
                locale="en",
                name="Olivaceous Cormorant",
                created="2022-05-16T13:14:56Z",
            ),
            CommonNameRecord(
                taxon_id=1,
                locale="en",
                name="Neotropic Cormorant",
                created="2022-05-16T13:14:57Z",
            ),
        ),
        scientific_name="Nannopterum brasilianum",
        requested_locale="en-US",
        default_locale="en",
    )

    assert result == "Neotropic Cormorant"


def test_select_common_name_falls_back_to_scientific_name() -> None:
    result = _select_common_name(
        common_names=(),
        scientific_name="Aves",
        requested_locale="de-DE",
        default_locale="en-US",
    )

    assert result == "Aves"
