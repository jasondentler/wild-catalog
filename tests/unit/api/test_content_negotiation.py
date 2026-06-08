import pytest

from wild_catalog.api.content_negotiation import (
    NotAcceptableResponseError,
    ResponseFormat,
    select_identify_response_format,
)


def test_select_returns_multipart_when_images_requested_and_multipart_accepted() -> None:
    selection = select_identify_response_format(
        accept_header="multipart/mixed",
        return_detected_images=True,
    )

    assert selection.response_format is ResponseFormat.MULTIPART
    assert selection.include_images is True


def test_select_returns_multipart_when_images_requested_and_accept_missing() -> None:
    selection = select_identify_response_format(
        accept_header=None,
        return_detected_images=True,
    )

    assert selection.response_format is ResponseFormat.MULTIPART
    assert selection.include_images is True


def test_select_returns_multipart_when_images_requested_and_accept_wildcard() -> None:
    selection = select_identify_response_format(
        accept_header="*/*",
        return_detected_images=True,
    )

    assert selection.response_format is ResponseFormat.MULTIPART
    assert selection.include_images is True


def test_select_returns_multipart_when_images_requested_and_multipart_wildcard() -> None:
    selection = select_identify_response_format(
        accept_header="multipart/*",
        return_detected_images=True,
    )

    assert selection.response_format is ResponseFormat.MULTIPART
    assert selection.include_images is True


def test_select_rejects_images_when_multipart_not_accepted() -> None:
    with pytest.raises(NotAcceptableResponseError, match="multipart/mixed"):
        select_identify_response_format(
            accept_header="application/json",
            return_detected_images=True,
        )


def test_select_returns_multipart_when_images_requested_and_json_plus_multipart() -> None:
    selection = select_identify_response_format(
        accept_header="application/json, multipart/mixed",
        return_detected_images=True,
    )

    assert selection.response_format is ResponseFormat.MULTIPART
    assert selection.include_images is True


def test_select_returns_json_by_default_when_images_not_requested() -> None:
    selection = select_identify_response_format(
        accept_header=None,
        return_detected_images=False,
    )

    assert selection.response_format is ResponseFormat.JSON
    assert selection.include_images is False


def test_select_returns_json_for_application_json_when_images_not_requested() -> None:
    selection = select_identify_response_format(
        accept_header="application/json",
        return_detected_images=False,
    )

    assert selection.response_format is ResponseFormat.JSON
    assert selection.include_images is False


def test_select_returns_multipart_without_images_when_only_multipart_accepted() -> None:
    selection = select_identify_response_format(
        accept_header="multipart/mixed",
        return_detected_images=False,
    )

    assert selection.response_format is ResponseFormat.MULTIPART
    assert selection.include_images is False


def test_select_returns_json_when_json_and_multipart_are_accepted() -> None:
    selection = select_identify_response_format(
        accept_header="application/json, multipart/mixed",
        return_detected_images=False,
    )

    assert selection.response_format is ResponseFormat.JSON
    assert selection.include_images is False


def test_select_returns_json_when_multipart_and_json_are_accepted() -> None:
    selection = select_identify_response_format(
        accept_header="multipart/mixed, application/json",
        return_detected_images=False,
    )

    assert selection.response_format is ResponseFormat.JSON
    assert selection.include_images is False


def test_select_accepts_multipart_with_parameters() -> None:
    selection = select_identify_response_format(
        accept_header="multipart/mixed; boundary=example",
        return_detected_images=False,
    )

    assert selection.response_format is ResponseFormat.MULTIPART
    assert selection.include_images is False


def test_select_returns_json_for_wildcard_when_images_not_requested() -> None:
    selection = select_identify_response_format(
        accept_header="*/*",
        return_detected_images=False,
    )

    assert selection.response_format is ResponseFormat.JSON
    assert selection.include_images is False
