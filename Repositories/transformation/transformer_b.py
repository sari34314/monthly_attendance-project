import calendar
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal

from Models.report_row import RowB
from Repositories.common.constants import WEEKDAY_TO_DAY
from Repositories.common.time_utils import minutes, shift_time, to_time
from Repositories.transformation.base_transformer import BaseTransformer

SATURDAY = 5
FRIDAY = 4
FRIDAY_LATEST_EXIT = time(12, 0)
MAX_SHIFT_MINUTES = 60
MAX_TRIES = 50


class TransformerB(BaseTransformer):
    def _new_rows(self, rows: list, year: int, month: int) -> list:
        # Build the new month day by day, instead of matching rows one to one
        source_rows = [row for row in rows if row.has_hours]
        if not source_rows:
            raise ValueError("No row with hours to build the new month from")

        last_day = calendar.monthrange(year, month)[1]
        new_rows = []
        work_index = 0

        for number in range(1, last_day + 1):
            current = date(year, month, number)

            # Saturday is always an empty row
            if current.weekday() == SATURDAY:
                new_rows.append(self._empty_row(current))
                continue

            # Other days take the hours of the original working rows, in order
            source = source_rows[work_index % len(source_rows)]
            work_index += 1
            new_rows.append(self._work_row(source, current))

        return new_rows

    def _empty_row(self, current: date) -> RowB:
        return RowB(
            date=current,
            day=WEEKDAY_TO_DAY[current.weekday()],
            entry_time=None,
            exit_time=None,
            total=None,
            notes=None,
        )

    def _work_row(self, source: RowB, current: date) -> RowB:
        entry, exit_ = self._random_hours(
            source.entry_time, source.exit_time, current.weekday() == FRIDAY
        )
        worked = minutes(exit_) - minutes(entry)
        total = (Decimal(worked) / 60).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return RowB(
            date=current,
            day=WEEKDAY_TO_DAY[current.weekday()],
            entry_time=entry,
            exit_time=exit_,
            total=total,
            notes=None,  # Type B notes are never created
        )

    def _random_hours(self, entry: time, exit_: time, is_friday: bool):
        # Latest allowed exit: 12:00 on Friday, any time on other days
        latest = minutes(FRIDAY_LATEST_EXIT) if is_friday else 24 * 60 - 1

        for _ in range(MAX_TRIES):
            new_exit = shift_time(
                exit_, self._random.randint(-MAX_SHIFT_MINUTES, MAX_SHIFT_MINUTES)
            )
            new_exit = to_time(min(minutes(new_exit), latest))
            new_entry = shift_time(
                entry, self._random.randint(-MAX_SHIFT_MINUTES, MAX_SHIFT_MINUTES)
            )

            # The entry must be before the exit
            if minutes(new_entry) < minutes(new_exit):
                return new_entry, new_exit

        # No valid draw: keep the original hours (with the Friday limit)
        return entry, to_time(min(minutes(exit_), latest))