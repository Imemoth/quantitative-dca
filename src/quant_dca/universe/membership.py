"""Fail-closed reconstruction of a historically knowable equity universe."""
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timezone
import math

from quant_dca.calendars.service import eligible_session_close
from quant_dca.types import Region, Security, UniverseMembership


def _require_aware(value: object, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a timezone-aware datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _date(value: str, name: str) -> date:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO date string") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} must be an ISO date string")
    return parsed


@dataclass(frozen=True, slots=True)
class EligibilityThresholds:
    """Caller-owned eligibility policy; this module supplies no research defaults."""

    min_trading_sessions: int
    min_liquidity: float
    require_fundamental_report: bool

    def __post_init__(self) -> None:
        if not isinstance(self.min_trading_sessions, int) or isinstance(
            self.min_trading_sessions, bool
        ):
            raise TypeError("min_trading_sessions must be a positive integer")
        if self.min_trading_sessions < 120:
            raise ValueError("min_trading_sessions must be at least 120")
        if (
            isinstance(self.min_liquidity, bool)
            or not isinstance(self.min_liquidity, (int, float))
        ):
            raise TypeError("min_liquidity must be a finite non-negative number")
        if not math.isfinite(self.min_liquidity) or self.min_liquidity < 0:
            raise ValueError("min_liquidity must be a finite non-negative number")
        if not isinstance(self.require_fundamental_report, bool):
            raise TypeError("require_fundamental_report must be boolean")


@dataclass(frozen=True, slots=True, kw_only=True)
class TradingSession:
    """Evidence that a security has history for one exchange session."""

    security_id: str
    exchange: str
    session_date: str
    available_at: datetime

    def __post_init__(self) -> None:
        _date(self.session_date, "session_date")
        _require_aware(self.available_at, "available_at")


@dataclass(frozen=True, slots=True, kw_only=True)
class LiquidityMetric:
    """A caller-computed liquidity value with measurement and knowledge times."""

    security_id: str
    measured_at: datetime
    available_at: datetime
    value: float

    def __post_init__(self) -> None:
        measured = _require_aware(self.measured_at, "measured_at")
        available = _require_aware(self.available_at, "available_at")
        if measured > available:
            raise ValueError("measured_at cannot be after available_at")
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise TypeError("value must be a finite non-negative number")
        if not math.isfinite(self.value) or self.value < 0:
            raise ValueError("value must be a finite non-negative number")


@dataclass(frozen=True, slots=True, kw_only=True)
class FundamentalReport:
    """Evidence of one published fundamental report known to the researcher."""

    security_id: str
    published_at: datetime
    available_at: datetime

    def __post_init__(self) -> None:
        published = _require_aware(self.published_at, "published_at")
        available = _require_aware(self.available_at, "available_at")
        if published > available:
            raise ValueError("published_at cannot be after available_at")


class UniverseIndex:
    """Select primary common equities from explicit point-in-time evidence."""

    def __init__(
        self,
        *,
        securities: Iterable[Security],
        memberships: Iterable[UniverseMembership],
        trading_sessions: Iterable[TradingSession],
        liquidity_metrics: Iterable[LiquidityMetric],
        fundamental_reports: Iterable[FundamentalReport],
        thresholds: EligibilityThresholds,
    ) -> None:
        if not isinstance(thresholds, EligibilityThresholds):
            raise TypeError("thresholds must be an EligibilityThresholds instance")
        self._securities = tuple(securities)
        self._memberships = tuple(memberships)
        self._sessions = tuple(trading_sessions)
        self._liquidity = tuple(liquidity_metrics)
        self._reports = tuple(fundamental_reports)
        self._thresholds = thresholds

    @classmethod
    def from_rows(
        cls,
        memberships: Iterable[UniverseMembership],
        *,
        securities: Iterable[Security],
        trading_sessions: Iterable[TradingSession],
        liquidity_metrics: Iterable[LiquidityMetric],
        fundamental_reports: Iterable[FundamentalReport],
        thresholds: EligibilityThresholds,
    ) -> "UniverseIndex":
        """Build from complete typed rows; omitted evidence cannot confer eligibility."""
        return cls(
            securities=securities,
            memberships=memberships,
            trading_sessions=trading_sessions,
            liquidity_metrics=liquidity_metrics,
            fundamental_reports=fundamental_reports,
            thresholds=thresholds,
        )

    @staticmethod
    def _latest_known(rows: list[object], cutoff: datetime) -> object | None:
        from quant_dca.point_in_time.asof import latest_known
        try:
            return latest_known(rows, cutoff)
        except (LookupError, ValueError, TypeError):
            return None

    @staticmethod
    def _active(row: Security | UniverseMembership, day: date) -> bool:
        start = _date(row.active_from, "active_from")
        end = _date(row.active_to, "active_to") if row.active_to is not None else None
        return start <= day and (end is None or day < end)

    def _security(self, security_id: str, cutoff: datetime) -> Security | None:
        row = self._latest_known(
            [item for item in self._securities if item.security_id == security_id], cutoff
        )
        return row if isinstance(row, Security) else None

    def _membership(
        self, security: Security, cutoff: datetime, day: date
    ) -> UniverseMembership | None:
        groups: dict[str, list[UniverseMembership]] = defaultdict(list)
        for row in self._memberships:
            if row.security_id == security.security_id:
                groups[row.universe_id].append(row)
        for universe_id in sorted(groups):
            row = self._latest_known(groups[universe_id], cutoff)
            if (
                isinstance(row, UniverseMembership)
                and self._active(row, day)
                and row.region is security.region
                and row.exchange == security.exchange
                and row.currency == security.currency
            ):
                return row
        return None

    def _has_history(self, security: Security, cutoff: datetime, day: date) -> bool:
        start = _date(security.active_from, "active_from")
        dates: set[date] = set()
        for row in self._sessions:
            if (
                row.security_id != security.security_id
                or row.exchange != security.exchange
                or row.available_at > cutoff
            ):
                continue
            session_day = _date(row.session_date, "session_date")
            if not start <= session_day <= day:
                continue
            try:
                close = eligible_session_close(security.exchange, session_day)
            except ValueError:
                return False
            if close is not None and close <= cutoff:
                dates.add(session_day)
        return len(dates) >= self._thresholds.min_trading_sessions

    def _has_liquidity(self, security_id: str, cutoff: datetime) -> bool:
        known = [
            row for row in self._liquidity
            if row.security_id == security_id
            and row.measured_at <= cutoff
            and row.available_at <= cutoff
        ]
        if not known:
            return False
        latest_measurement = max(row.measured_at for row in known)
        latest_rows = [row for row in known if row.measured_at == latest_measurement]
        latest_availability = max(row.available_at for row in latest_rows)
        tied = [row for row in latest_rows if row.available_at == latest_availability]
        if any(row.value != tied[0].value for row in tied[1:]):
            return False
        return tied[0].value >= self._thresholds.min_liquidity

    def _has_fundamental(self, security_id: str, cutoff: datetime) -> bool:
        if not self._thresholds.require_fundamental_report:
            return True
        return any(
            row.security_id == security_id
            and row.published_at <= cutoff
            and row.available_at <= cutoff
            for row in self._reports
        )

    def is_eligible(self, security_id: str, as_of: datetime) -> bool:
        """Return eligibility at an aware point in time, failing closed on gaps."""
        cutoff = _require_aware(as_of, "as_of")
        day = cutoff.astimezone(timezone.utc).date()
        security = self._security(security_id, cutoff)
        if (
            security is None
            or security.region not in (Region.US, Region.EU)
            or security.security_type != "common_equity"
            or not security.primary_listing
            or not self._active(security, day)
        ):
            return False
        membership = self._membership(security, cutoff, day)
        return bool(
            membership is not None
            and self._has_history(security, cutoff, day)
            and self._has_liquidity(security.security_id, cutoff)
            and self._has_fundamental(security.security_id, cutoff)
        )

    def eligible_universe(self, as_of: datetime, region: Region) -> list[Security]:
        """Return eligible known security versions for US or EU, sorted by ID."""
        cutoff = _require_aware(as_of, "as_of")
        if region not in (Region.US, Region.EU):
            raise ValueError("region must be US or EU")
        security_ids = sorted({row.security_id for row in self._securities})
        result = []
        for security_id in security_ids:
            security = self._security(security_id, cutoff)
            if (
                security is not None
                and security.region is region
                and self.is_eligible(security_id, cutoff)
            ):
                result.append(security)
        return result
