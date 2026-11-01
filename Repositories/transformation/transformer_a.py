import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from Models.report import Report, ReportSummary
from Models.report_row import Day, RowA
from Repositories.common.time_utils import minutes, shift_time, to_time
from Repositories.transformation.base_transformer import BaseTransformer
from Repositories.common.constants import WEEKDAY_TO_DAY


class TransformerA(BaseTransformer):
    def _new_dates(self, dates: list, year: int, month: int) -> list:
        filled = self._fill_missing_dates(dates)
        moved = self._move_to_month(filled, year, month)
        return self._shift_dates(moved)

    def _move_to_month(self, dates: list, year: int, month: int) -> list:
        last_day = calendar.monthrange(year, month)[1]
        count = len(dates)

        if count > last_day:
            raise ValueError("More rows than days in the new month")

        # Keep the original day number, but never after the end of the month
        days = [min(d.day, last_day) for d in dates]

        # From the end: leave room for the rows after each row
        for i in range(count - 1, -1, -1):
            days[i] = min(days[i], last_day - (count - 1 - i))

        # From the start: every row is at least one day after the previous one
        for i in range(1, count):
            days[i] = max(days[i], days[i - 1] + 1)

        return [date(year, month, day) for day in days]

    def _finish(self, report: Report) -> Report:
        report.summary = self._build_summary(report.rows)
        return report

    def _fill_missing_dates(self, dates: list) -> list:
        known = [i for i, d in enumerate(dates) if d is not None]
        if not known:
            raise ValueError("No row has a date, cannot fill missing dates")

        filled = list(dates)

        # Virtual boundaries: the day before the month starts and the day after it ends
        first = dates[known[0]]
        last = dates[known[-1]]
        start_bound = first.replace(day=1) - timedelta(days=1)
        last_day = calendar.monthrange(last.year, last.month)[1]
        end_bound = last.replace(day=last_day) + timedelta(days=1)

        # Anchors: virtual start, every known date, virtual end
        anchors = (
            [(-1, start_bound)]
            + [(i, dates[i]) for i in known]
            + [(len(dates), end_bound)]
        )

        # Spread the missing rows evenly between each pair of neighbor anchors
        for (left_i, left_date), (right_i, right_date) in zip(anchors, anchors[1:]):
            missing = right_i - left_i - 1
            gap = (right_date - left_date).days
            for step in range(1, missing + 1):
                days_after_left = (gap * step + (missing + 1) // 2) // (missing + 1)
                filled[left_i + step] = left_date + timedelta(days=days_after_left)

        return filled

    def _shift_dates(self, dates: list) -> list:
        one_day = timedelta(days=1)

        # Latest allowed date for each row, so that the rows after it still fit
        latest = [None] * len(dates)
        for i in range(len(dates) - 1, -1, -1):
            last_day = calendar.monthrange(dates[i].year, dates[i].month)[1]
            limit = min(dates[i] + one_day, dates[i].replace(day=last_day))
            if i < len(dates) - 1:
                limit = min(limit, latest[i + 1] - one_day)
            latest[i] = limit

        new_dates = []
        for i, original in enumerate(dates):
            # Earliest allowed: one day back, same month, after the previous row
            earliest = max(original - one_day, original.replace(day=1))
            if new_dates:
                earliest = max(earliest, new_dates[-1] + one_day)

            if latest[i] < earliest:
                raise ValueError("Cannot shift dates, check the original dates")

            offset = self._random.randint(0, (latest[i] - earliest).days)
            new_dates.append(earliest + timedelta(days=offset))

        return new_dates

    def _transform_row(self, row: RowA, new_date: date) -> RowA:
        # Break: up to 5 minutes more or less
        break_minutes = max(0, minutes(row.break_time) + self._random.randint(-5, 5))

        new_entry, new_exit, worked_minutes = self._random_times(
            row.entry_time, row.exit_time, break_minutes
        )

        total = (Decimal(worked_minutes) / 60).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # The day name always comes from the new date, so they stay in sync
        new_day = WEEKDAY_TO_DAY[new_date.weekday()]
        is_shabbat = new_day == Day.SATURDAY
        zero = Decimal("0.00")

        return RowA(
            date=new_date,
            day=new_day,
            entry_time=new_entry,
            exit_time=new_exit,
            total=total,
            workplace=row.workplace,
            break_time=to_time(break_minutes),
            percent_100=zero if is_shabbat else total,
            percent_125=zero,
            percent_150=zero,
            shabbat_150=total if is_shabbat else zero,
        )

    def _random_times(self, entry, exit_, break_minutes: int):
        new_entry = shift_time(entry, self._random.randint(-60, 60))
        new_exit = shift_time(exit_, self._random.randint(-60, 60))
        worked = minutes(new_exit) - minutes(new_entry) - break_minutes

        # If the new times are not valid, keep the original times
        if worked <= 0:
            new_entry, new_exit = entry, exit_
            worked = minutes(exit_) - minutes(entry) - break_minutes

        return new_entry, new_exit, worked

    def _build_summary(self, rows: list[RowA]) -> ReportSummary:
        zero = Decimal("0.00")
        return ReportSummary(
            days=len(rows),
            total=sum((r.total for r in rows), zero),
            percent_100=sum((r.percent_100 for r in rows), zero),
            percent_125=sum((r.percent_125 for r in rows), zero),
            percent_150=sum((r.percent_150 for r in rows), zero),
            shabbat_150=sum((r.shabbat_150 for r in rows), zero),
        )