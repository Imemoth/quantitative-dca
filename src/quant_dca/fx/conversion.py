"""Fail-closed point-in-time FX quote selection and HUF conversion."""
from collections.abc import Iterable
from datetime import datetime, timedelta
import math

from quant_dca.point_in_time.asof import latest_known
from quant_dca.types import FXQuote, QualityTier


class FXQuoteUnavailable(LookupError):
    """No evidenced quote was usable at the requested instant."""


class StaleFXQuote(LookupError):
    """The selected quote violates the caller's maximum-age policy."""


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"INVALID_TIMESTAMP:{field}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"INVALID_TIMESTAMP:{field}")
    return value


def _currency(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 3
        or not value.isascii()
        or not value.isalpha()
        or value != value.upper()
    ):
        raise ValueError(f"INVALID_FX_CURRENCY:{field}")
    return value


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _validate_quote(row: FXQuote) -> None:
    if not isinstance(row, FXQuote):
        raise TypeError("INVALID_FX_QUOTE:canonical FXQuote required")
    base = _currency(row.base_currency, "base_currency")
    counter = _currency(row.quote_currency, "quote_currency")
    if base == counter:
        raise ValueError("INVALID_FX_CURRENCY:identical legs")
    if not _finite(row.rate) or row.rate <= 0:
        raise ValueError("INVALID_FX_RATE")
    fixing = _aware(row.fixing_at, "fixing_at")
    available = _aware(row.available_at, "available_at")
    if available < fixing:
        raise ValueError("INVALID_FX_CHRONOLOGY:availability_before_fixing")

    published = (
        None if row.published_at is None else _aware(row.published_at, "published_at")
    )
    revised = None if row.revised_at is None else _aware(row.revised_at, "revised_at")
    if published is not None and available < published:
        raise ValueError("PIT_INVALID_CHRONOLOGY:availability_before_publication")
    if revised is not None and available < revised:
        raise ValueError("PIT_INVALID_CHRONOLOGY:availability_before_revision")
    if published is not None and revised is not None and revised < published:
        raise ValueError("PIT_INVALID_CHRONOLOGY:revision_before_publication")
    if not isinstance(row.quality, QualityTier):
        raise ValueError("INVALID_FX_PROVENANCE:quality")
    if not isinstance(row.source, str) or not row.source.strip():
        raise ValueError("INVALID_FX_PROVENANCE:source")
    if not isinstance(row.revision_id, str) or not row.revision_id.strip():
        raise ValueError("INVALID_FX_PROVENANCE:revision_id")
    if not isinstance(row.quote_type, str) or row.quote_type not in {
        "spot",
        "daily_open",
    }:
        if row.quote_type == "daily_close":
            raise ValueError("UNSUPPORTED_DAILY_FX_QUOTE_TYPE")
        raise ValueError("INVALID_FX_QUOTE_TYPE")


def _latest_fixing_revision(rows: list[FXQuote], cutoff: datetime) -> FXQuote:
    """Order evidenced revisions explicitly without changing shared PIT rules."""
    revisions = [row for row in rows if row.revised_at is not None]
    if not revisions:
        return latest_known(rows, cutoff)

    latest_revision_at = max(row.revised_at for row in revisions)
    tied = [row for row in revisions if row.revised_at == latest_revision_at]
    selected = tied[0]
    if any(row != selected for row in tied[1:]):
        raise ValueError("PIT_AMBIGUOUS_VINTAGE:indistinguishable revision order")
    return selected


class FXService:
    """Resolve direct canonical FX pairs without look-ahead.

    ``max_age=None`` is an explicit caller policy allowing any age. A finite
    duration rejects older selected fixings; this layer supplies no tuned
    default. Daily-only rows must be marked ``daily_open`` and are usable only
    on their evidenced opening calendar day.
    """

    def __init__(self, rows: Iterable[FXQuote], *, max_age: timedelta | None):
        if max_age is not None:
            if not isinstance(max_age, timedelta) or max_age < timedelta(0):
                raise ValueError("INVALID_MAX_FX_AGE")
        self._rows = tuple(rows)
        if any(not isinstance(row, FXQuote) for row in self._rows):
            raise TypeError("INVALID_FX_QUOTE:canonical FXQuote required")
        self._max_age = max_age

    @classmethod
    def from_rows(
        cls, rows: Iterable[FXQuote], *, max_age: timedelta | None
    ) -> "FXService":
        """Snapshot fully evidenced canonical rows; tuple shorthands are rejected."""
        return cls(rows, max_age=max_age)

    def resolve(self, base: str, quote: str, at_or_before: datetime) -> FXQuote:
        """Return the latest fixing and its latest revision known by the cutoff."""
        base_currency = _currency(base, "base")
        quote_currency = _currency(quote, "quote")
        if base_currency == quote_currency:
            raise ValueError("INVALID_FX_CURRENCY:identical requested legs")
        cutoff = _aware(at_or_before, "at_or_before")

        # Reject malformed collection members before pair filtering so a bad
        # row cannot hide behind a later request for a differently-cased pair.
        for row in self._rows:
            _validate_quote(row)
        matching = [
            row
            for row in self._rows
            if row.base_currency == base_currency
            and row.quote_currency == quote_currency
        ]
        if not matching:
            raise FXQuoteUnavailable(
                f"FX_QUOTE_UNAVAILABLE:{base_currency}/{quote_currency}"
            )
        known = [
            row
            for row in matching
            if row.fixing_at <= cutoff and row.available_at <= cutoff
        ]
        same_day_known = [
            row
            for row in known
            if row.quote_type != "daily_open"
            or row.fixing_at.date() == cutoff.astimezone(row.fixing_at.tzinfo).date()
        ]
        if not same_day_known:
            detail = (
                "FX_DAILY_OPEN_UNAVAILABLE"
                if any(row.quote_type == "daily_open" for row in known)
                else "FX_QUOTE_UNAVAILABLE"
            )
            raise FXQuoteUnavailable(f"{detail}:{base_currency}/{quote_currency}")

        fixing_at = max(row.fixing_at for row in same_day_known)
        fixing_rows = [row for row in same_day_known if row.fixing_at == fixing_at]
        selected = _latest_fixing_revision(fixing_rows, cutoff)
        if self._max_age is not None and cutoff - selected.fixing_at > self._max_age:
            raise StaleFXQuote(
                f"STALE_FX_QUOTE:{base_currency}/{quote_currency}:"
                f"fixing={selected.fixing_at.isoformat()}"
            )
        return selected

    def rate(self, base: str, quote: str, at_or_before: datetime) -> float:
        """Return the scalar rate from the selected evidenced quote."""
        return self.resolve(base, quote, at_or_before).rate

    def to_huf(self, amount: float, currency: str, execution_ts: datetime) -> float:
        """Convert a finite native amount to HUF at its execution instant."""
        if not _finite(amount):
            raise ValueError("INVALID_FX_AMOUNT")
        native_currency = _currency(currency, "currency")
        cutoff = _aware(execution_ts, "execution_ts")
        if native_currency == "HUF":
            return float(amount)
        return float(amount) * self.rate(native_currency, "HUF", cutoff)
