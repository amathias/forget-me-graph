from __future__ import annotations

import base64
import hmac
import json
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken

from forgetmegraph.domain.models import ProtectedSelector, SubjectSelector


class SelectorProtectionError(ValueError):
    pass


class SelectorProtector:
    """Pseudonymizes selectors for display and encrypts values for resumable execution."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 16:
            raise SelectorProtectionError("selector secret must contain at least 16 characters")
        self._secret = secret.encode("utf-8")
        fernet_key = base64.urlsafe_b64encode(sha256(self._secret + b":encryption").digest())
        self._fernet = Fernet(fernet_key)

    def protect(self, selector: SubjectSelector) -> ProtectedSelector:
        payload = selector.model_dump_json().encode("utf-8")
        digest = hmac.new(self._secret, payload, sha256).hexdigest()
        return ProtectedSelector(
            subject_type=selector.subject_type,
            field=selector.field,
            operator=selector.operator,
            token=f"subj_{digest[:16]}",
            ciphertext=self._fernet.encrypt(payload).decode("ascii"),
        )

    def reveal(self, protected: ProtectedSelector) -> SubjectSelector:
        try:
            payload = self._fernet.decrypt(protected.ciphertext.encode("ascii"))
        except InvalidToken as exc:
            raise SelectorProtectionError("selector ciphertext is invalid") from exc
        selector = SubjectSelector.model_validate_json(payload)
        expected = self.protect(selector).token
        if not hmac.compare_digest(expected, protected.token):
            raise SelectorProtectionError("selector token does not match ciphertext")
        return selector


def safe_selector_summary(protected: ProtectedSelector) -> dict[str, str]:
    return {
        "subject_type": protected.subject_type,
        "field": protected.field,
        "operator": protected.operator.value,
        "token": protected.token,
    }


def assert_no_raw_value(payload: object, raw_value: str) -> None:
    serialized = json.dumps(payload, default=str, sort_keys=True)
    if raw_value in serialized:
        raise SelectorProtectionError("privacy boundary violation: raw selector value detected")
