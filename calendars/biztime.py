from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

try:
    import holidays as pyholidays
    _HAS_HOLIDAYS = True
except Exception:
    _HAS_HOLIDAYS = False

@dataclass
class Cutoffs:
    tz: str
    cfg: Dict[str, Any]
    holiday_region: str = "US"

    @classmethod
    def from_yaml(cls, path: str):
        import yaml
        data = yaml.safe_load(open(path)) or {}
        return cls(
            tz=data.get("timezone", "America/New_York"),
            cfg=(data.get("rails") or {}),
            holiday_region=(data.get("holidays") or {}).get("region", "US"),
        )

    def tzinfo(self): return ZoneInfo(self.tz)

    def _holidays(self, year: int):
        if _HAS_HOLIDAYS:
            try: return pyholidays.country_holidays(self.holiday_region, years=[year])
            except Exception: return set()
        return set()

    def is_business_day(self, d: dt.date) -> bool:
        if d.weekday() >= 5:  # Sat/Sun
            return False
        if _HAS_HOLIDAYS:
            return d not in self._holidays(d.year)
        return True

    def minutes_to_cutoff(self, now: Optional[dt.datetime], rail: str) -> Optional[int]:
        rail_cfg = self.cfg.get(rail, {}); cutoff = rail_cfg.get("cutoff_local")
        if not cutoff: return None
        if now is None:
            now = dt.datetime.now(self.tzinfo())
        elif now.tzinfo is None:
            now = now.replace(tzinfo=self.tzinfo())
        h, m = map(int, cutoff.split(":"))
        co = now.replace(hour=h, minute=m, second=0, microsecond=0)
        return int((co - now).total_seconds() // 60)

    def can_same_day(self, now: Optional[dt.datetime], rail: str) -> bool:
        if not self.is_business_day((now or dt.datetime.now(self.tzinfo())).date()):
            return False
        mins = self.minutes_to_cutoff(now, rail)
        return mins is None or mins >= 0

    def eta_label(self, now: Optional[dt.datetime], rail: str) -> str:
        tz = self.tzinfo()
        if now is None: now = dt.datetime.now(tz)
        elif now.tzinfo is None: now = now.replace(tzinfo=tz)
        is_bday = self.is_business_day(now.date())
        mins = self.minutes_to_cutoff(now, rail)
        rcfg = self.cfg.get(rail, {})
        if rail == "rtp": return "Instant (24/7)"
        if rail == "ach_same_day":
            return "Same day (ACH)" if is_bday and (mins is None or mins >= 0) else "T+1 (business)"
        if rail == "wire":
            return "Same day (wire)" if is_bday and (mins is None or mins >= 0) else "T+1 (business)"
        if rail == "ach": return "T+1–T+2 (business)"
        if rail == "card": return "T+1–T+2"
        if rail == "check": return f"T+{rcfg.get('mail_days_business','3-7')} (mail)"
        return "Unknown"
