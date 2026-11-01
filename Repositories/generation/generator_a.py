from Models.report import Report
from Models.report_row import RowA
from Repositories.common.time_utils import minutes
from Repositories.generation.base_generator import BaseGenerator


class GeneratorA(BaseGenerator):
    headers = [
        "תאריך", "יום", "מקום עבודה", "כניסה", "יציאה", "הפסקה",
        'סה"כ', "100%", "125%", "150%", "שבת 150%",
    ]
    column_widths = [62, 42, 62, 40, 40, 40, 40, 40, 40, 40, 50]

    def _row_cells(self, row: RowA) -> list[str]:
        # Same order as headers
        return [
            row.date.strftime("%d/%m/%Y"),
            row.day.value,
            row.workplace or "",
            row.entry_time.strftime("%H:%M"),
            row.exit_time.strftime("%H:%M"),
            row.break_time.strftime("%H:%M"),
            str(row.total),
            str(row.percent_100),
            str(row.percent_125),
            str(row.percent_150),
            str(row.shabbat_150),
        ]

    def _summary_cells(self, report: Report) -> list[str] | None:
        summary = report.summary
        if summary is None:
            return None

        # The break total is computed from the rows, it has no field in the model
        total_break = sum(minutes(row.break_time) for row in report.rows)

        # The days count goes under the date column, the other totals under their own
        return [
            str(summary.days),
            "",
            "",
            "",
            "",
            f"{total_break // 60:02d}:{total_break % 60:02d}",
            str(summary.total),
            str(summary.percent_100),
            str(summary.percent_125),
            str(summary.percent_150),
            str(summary.shabbat_150),
        ]