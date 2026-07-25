import pytest

from forgetmegraph.domain.models import SubjectSelector
from forgetmegraph.privacy.selector import (
    SelectorProtectionError,
    SelectorProtector,
    assert_no_raw_value,
    safe_selector_summary,
)


def test_selector_is_tokenized_encrypted_and_recoverable() -> None:
    protector = SelectorProtector("a-test-secret-that-is-long-enough")
    selector = SubjectSelector(
        subject_type="customer",
        field="customer_id",
        value="42",
    )

    protected = protector.protect(selector)

    assert protected.token.startswith("subj_")
    assert protected.token != "42"
    assert "42" not in protected.ciphertext
    assert safe_selector_summary(protected)["token"] == protected.token
    assert protector.reveal(protected) == selector
    assert_no_raw_value(safe_selector_summary(protected), selector.value)


def test_privacy_assertion_rejects_raw_selector() -> None:
    with pytest.raises(SelectorProtectionError):
        assert_no_raw_value({"unsafe": "customer 42"}, "42")


def test_short_secret_is_rejected() -> None:
    with pytest.raises(SelectorProtectionError):
        SelectorProtector("too-short")
