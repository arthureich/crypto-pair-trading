"""Deterministic client order id generation for exchange-facing orders."""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass

CLIENT_ORDER_ID_VERSION = "coid.v1"
SHORT_CLIENT_ORDER_ID_VERSION = "coid.v1h"
DEFAULT_HASH_CHARS = 32
MIN_HASH_CHARS = 16

_COMPONENT_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True, slots=True)
class ClientOrderIdInputs:
    """Immutable fields required to reconstruct a client order id."""

    venue: str
    account_id: str
    strategy_id: str
    trade_id: str
    leg: str
    phase: str
    symbol: str
    attempt: int | str | None = None
    slice_id: str | None = None
    id_version: str = CLIENT_ORDER_ID_VERSION


@dataclass(frozen=True, slots=True)
class ClientOrderId:
    """Generated venue id plus the canonical value that must be persisted."""

    client_order_id: str
    canonical_id: str
    version: str
    is_shortened: bool


def build_client_order_id(
    inputs: ClientOrderIdInputs,
    *,
    max_length: int | None = None,
    hash_chars: int = DEFAULT_HASH_CHARS,
) -> ClientOrderId:
    """Build a deterministic, restart-stable client order id.

    If ``max_length`` is provided and the canonical id exceeds it, the returned
    exchange-facing id is a deterministic hash of the full canonical id. The
    caller must persist ``canonical_id`` alongside the returned id.
    """

    canonical_id = canonical_client_order_id(inputs)

    if max_length is None or len(canonical_id) <= max_length:
        return ClientOrderId(
            client_order_id=canonical_id,
            canonical_id=canonical_id,
            version=inputs.id_version,
            is_shortened=False,
        )

    shortened_id = _shorten_canonical_id(
        canonical_id,
        max_length=max_length,
        hash_chars=hash_chars,
    )
    return ClientOrderId(
        client_order_id=shortened_id,
        canonical_id=canonical_id,
        version=inputs.id_version,
        is_shortened=True,
    )


def generate_client_order_id(
    *,
    venue: str,
    account_id: str,
    strategy_id: str,
    trade_id: str,
    leg: str,
    phase: str,
    symbol: str,
    attempt: int | str | None = None,
    slice_id: str | None = None,
    max_length: int | None = None,
) -> str:
    """Convenience wrapper returning only the exchange-facing id."""

    inputs = ClientOrderIdInputs(
        venue=venue,
        account_id=account_id,
        strategy_id=strategy_id,
        trade_id=trade_id,
        leg=leg,
        phase=phase,
        symbol=symbol,
        attempt=attempt,
        slice_id=slice_id,
    )
    return build_client_order_id(inputs, max_length=max_length).client_order_id


def canonical_client_order_id(inputs: ClientOrderIdInputs) -> str:
    """Return the full documented canonical id for durable Ledger storage."""

    _validate_inputs(inputs)
    return ":".join(
        (
            inputs.id_version,
            inputs.venue,
            inputs.account_id,
            inputs.strategy_id,
            inputs.trade_id,
            inputs.leg,
            inputs.phase,
            inputs.symbol,
            _attempt_or_slice(inputs),
        )
    )


def _attempt_or_slice(inputs: ClientOrderIdInputs) -> str:
    if inputs.attempt is not None and inputs.slice_id is None:
        return f"attempt-{inputs.attempt}"
    if inputs.slice_id is not None and inputs.attempt is None:
        return f"slice-{inputs.slice_id}"
    raise ValueError("exactly one of attempt or slice_id is required")


def _shorten_canonical_id(
    canonical_id: str,
    *,
    max_length: int,
    hash_chars: int,
) -> str:
    if hash_chars < MIN_HASH_CHARS:
        raise ValueError(f"hash_chars must be at least {MIN_HASH_CHARS}")

    prefix = f"{SHORT_CLIENT_ORDER_ID_VERSION}:"
    digest_chars = min(hash_chars, max_length - len(prefix))
    if digest_chars < MIN_HASH_CHARS:
        raise ValueError(f"max_length must allow {len(prefix) + MIN_HASH_CHARS} characters")

    digest = hashlib.sha256(canonical_id.encode("utf-8")).digest()
    encoded_digest = base64.b32encode(digest).decode("ascii").lower().rstrip("=")
    return f"{prefix}{encoded_digest[:digest_chars]}"


def _validate_inputs(inputs: ClientOrderIdInputs) -> None:
    _validate_component("id_version", inputs.id_version)
    if inputs.id_version != CLIENT_ORDER_ID_VERSION:
        raise ValueError(f"unsupported client order id version: {inputs.id_version}")

    required_components = {
        "venue": inputs.venue,
        "account_id": inputs.account_id,
        "strategy_id": inputs.strategy_id,
        "trade_id": inputs.trade_id,
        "leg": inputs.leg,
        "phase": inputs.phase,
        "symbol": inputs.symbol,
    }
    for field_name, value in required_components.items():
        _validate_component(field_name, value)

    if inputs.attempt is not None:
        _validate_component("attempt", str(inputs.attempt))
    if inputs.slice_id is not None:
        _validate_component("slice_id", inputs.slice_id)


def _validate_component(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")

    if not value.isascii():
        raise ValueError(f"{field_name} must be ASCII")

    if not _COMPONENT_PATTERN.fullmatch(value):
        allowed = "A-Z, a-z, 0-9, dot, underscore, and hyphen"
        raise ValueError(f"{field_name} contains unsupported characters; allowed: {allowed}")


__all__ = [
    "CLIENT_ORDER_ID_VERSION",
    "SHORT_CLIENT_ORDER_ID_VERSION",
    "ClientOrderId",
    "ClientOrderIdInputs",
    "build_client_order_id",
    "canonical_client_order_id",
    "generate_client_order_id",
]
