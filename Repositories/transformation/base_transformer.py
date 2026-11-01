import random
from abc import ABC
from datetime import date

from Models.report import Report
from Models.report_row import ReportRow
from Repositories.common.constants import DEFAULT_SEED, OUTPUT_YEAR

NAMES = [
    "דוד לוי",
    "מיכל כהן",
    "יוסי אברהם",
    "רונית מזרחי",
    "אבי פרידמן",
    "נועה שטרן",
]


class BaseTransformer(ABC):
    """Builds a new Report from a real one. Subclasses define dates and rows."""

    def __init__(self, seed: int = DEFAULT_SEED):
        # Own random generator, so the same seed always gives the same output
        self._random = random.Random(seed)

    def transform(self, report: Report) -> Report:
        # Shared skeleton: the original report is never modified.
        # The month is drawn once per report, the year is fixed.
        month = self._random.randint(1, 12)

        new_rows = self._new_rows(report.rows, OUTPUT_YEAR, month)

        new_report = Report(
            employee_name=self._random.choice(NAMES),
            rows=new_rows,
            company_name=report.company_name,
        )
        return self._finish(new_report)

    def _new_rows(self, rows: list, year: int, month: int) -> list:
        # Default: every original row gets one new date (same number of rows).
        # A subclass that builds the whole month itself overrides this method.
        new_dates = self._new_dates([row.date for row in rows], year, month)
        return [
            self._transform_row(row, new_date)
            for row, new_date in zip(rows, new_dates)
        ]

    def _finish(self, report: Report) -> Report:
        # Hook: A builds its summary here, B does nothing
        return report

    def _new_dates(self, dates: list, year: int, month: int) -> list:
        """Return the dates for the new rows, same length as the input."""
        raise NotImplementedError

    def _transform_row(self, row: ReportRow, new_date: date) -> ReportRow:
        """Return a new row built from the original row and its new date."""
        raise NotImplementedError