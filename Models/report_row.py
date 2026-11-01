from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from enum import Enum


class Day(Enum):
    SUNDAY = "ראשון"
    MONDAY = "שני"
    TUESDAY = "שלישי"
    WEDNESDAY = "רביעי"
    THURSDAY = "חמישי"
    FRIDAY = "שישי"
    SATURDAY = "שבת"


@dataclass
class ReportRow:
    date: date | None
    day: Day | None
    # None means a row without work (Saturday, holiday): only date and day are filled
    entry_time: time | None
    exit_time: time | None
    total: Decimal | None

    @property
    def has_hours(self) -> bool:
        return self.entry_time is not None and self.exit_time is not None


@dataclass
class RowA(ReportRow):
    workplace: str | None
    break_time: time
    percent_100: Decimal
    percent_125: Decimal
    percent_150: Decimal
    shabbat_150: Decimal


@dataclass
class RowB(ReportRow):
    notes: str | None