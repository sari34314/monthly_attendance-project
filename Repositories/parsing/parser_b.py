import calendar
import re
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from Models.report import Report
from Models.report_row import RowB
from Repositories.common.constants import HOLIDAY_NOTES, WEEKDAY_TO_DAY
from Repositories.common.time_utils import minutes
from Repositories.parsing.base_parser import BaseParser

DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2})\b")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")

SATURDAY = 5


class ParserB(BaseParser):
    """Reads type B text. The result is always every day of the month, in order."""

    def _find_company(self, lines: list[str]) -> str | None:
        # Type B has no company line
        return None

    def _parse_row(self, line: str) -> RowB | None:
        # A raw row: whatever the OCR found. It is cleaned up in _finish.
        when = self._find_date(line)
        times = self._find_times(line)

        if when is None and not times:
            return None

        return RowB(
            date=when,
            day=None,
            entry_time=times[0] if times else None,
            exit_time=times[1] if len(times) > 1 else None,
            total=None,
            notes=self._find_note(line),
        )

    def _finish(self, report: Report, lines: list[str]) -> Report:
        raw_rows = report.rows

        month = self._find_month(raw_rows)
        if month is None:
            report.rows = []
            return report
        year, mon = month

        # Rows with a readable date, keyed by date (the row with more times wins)
        by_date = {}
        for row in raw_rows:
            if row.date is not None and (row.date.year, row.date.month) == month:
                old = by_date.get(row.date)
                if old is None or self._count(row) > self._count(old):
                    by_date[row.date] = row

        self._place_undated(raw_rows, by_date, month)
        default = self._default_hours(by_date)

        last_day = calendar.monthrange(year, mon)[1]
        report.rows = [
            self._build_row(
                date(year, mon, n), by_date.get(date(year, mon, n)), default
            )
            for n in range(1, last_day + 1)
        ]
        return report

    # ------------------------------------------------------------------
    # Month reconstruction
    # ------------------------------------------------------------------
    @staticmethod
    def _find_month(rows: list[RowB]) -> tuple[int, int] | None:
        # The most common (year, month) among the dates the OCR read
        months = Counter((r.date.year, r.date.month) for r in rows if r.date)
        return months.most_common(1)[0][0] if months else None

    def _place_undated(self, raw_rows, by_date, month) -> None:
        # A line with hours but a lost date goes to the next free weekday after
        # the previous line, because the lines are in date order.
        year, mon = month
        previous = date(year, mon, 1) - timedelta(days=1)

        for row in raw_rows:
            if row.date is not None:
                if (row.date.year, row.date.month) == month:
                    previous = row.date
                continue
            if row.entry_time is None:
                continue

            free = self._next_free(previous + timedelta(days=1), by_date, month)
            if free is not None:
                by_date[free] = row
                previous = free

    @staticmethod
    def _next_free(start: date, by_date: dict, month: tuple[int, int]) -> date | None:
        current = start
        while (current.year, current.month) == month:
            if current.weekday() != SATURDAY and current not in by_date:
                return current
            current += timedelta(days=1)
        return None

    @staticmethod
    def _default_hours(by_date: dict) -> tuple[time, time] | None:
        # The most common (entry, exit) pair, used when the OCR lost the hours of a workday
        pairs = Counter(
            (r.entry_time, r.exit_time)
            for r in by_date.values()
            if r.entry_time is not None and r.exit_time is not None
        )
        return pairs.most_common(1)[0][0] if pairs else None

    def _build_row(self, d: date, raw: RowB | None, default) -> RowB:
        # Saturday is always empty
        if d.weekday() == SATURDAY:
            return self._make(d, None, None, None)

        note = raw.notes if raw else None
        entry = raw.entry_time if raw else None
        exit_ = raw.exit_time if raw else None

        # A known note without hours is a holiday: an empty row that keeps its note
        if entry is None and note:
            return self._make(d, None, None, note)

        # Any other workday must have hours; fill what the OCR lost
        if default is not None:
            if entry is None:
                entry = default[0]
            if exit_ is None or minutes(exit_) <= minutes(entry):
                exit_ = default[1]

        if entry is None or exit_ is None or minutes(exit_) <= minutes(entry):
            return self._make(d, None, None, note)

        return self._make(d, entry, exit_, note)

    # ------------------------------------------------------------------
    # Reading one line
    # ------------------------------------------------------------------
    @staticmethod
    def _find_date(line: str) -> date | None:
        match = DATE_RE.search(line)
        if match is None:
            return None
        day_, month, year = (int(g) for g in match.groups())
        try:
            return date(2000 + year, month, day_)
        except ValueError:
            return None

    @staticmethod
    def _find_times(line: str) -> list[time]:
        times = []
        for text in TIME_RE.findall(line):
            try:
                times.append(datetime.strptime(text, "%H:%M").time())
            except ValueError:
                continue
        return times

    @staticmethod
    def _find_note(line: str) -> str | None:
        # Only known holiday notes are kept, in their correct spelling
        for fragment, clean in HOLIDAY_NOTES.items():
            if fragment in line:
                return clean
        return None

    @staticmethod
    def _count(row: RowB) -> int:
        return (row.entry_time is not None) + (row.exit_time is not None)

    @staticmethod
    def _make(d: date, entry, exit_, note) -> RowB:
        total = None
        if entry is not None and exit_ is not None:
            worked = minutes(exit_) - minutes(entry)
            total = (Decimal(worked) / 60).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        return RowB(
            date=d,
            day=WEEKDAY_TO_DAY[d.weekday()],
            entry_time=entry,
            exit_time=exit_,
            total=total,
            notes=note,
        )