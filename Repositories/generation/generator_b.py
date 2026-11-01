from reportlab.lib import colors

from Models.report import Report
from Models.report_row import RowB
from Repositories.generation.base_generator import BaseGenerator


class GeneratorB(BaseGenerator):
    # Reading order, the first column is drawn on the right side
    headers = ["תאריך", "יום בשבוע", "שעת כניסה", "שעת יציאה", 'סה"כ שעות', "הערות"]
    column_widths = [70, 70, 70, 70, 70, 150]

    def _row_cells(self, row: RowB) -> list[str]:
        # Same order as headers. Rows without hours show only the date and the day.
        return [
            self._format_date(row),
            row.day.value,
            self._format_time(row.entry_time),
            self._format_time(row.exit_time),
            str(row.total) if row.total is not None else "",
            row.notes or "",
        ]

    def _extra_styles(self, report: Report) -> list:
        # Shade the rows without hours (Saturday, holidays), like the original
        styles = []
        for index, row in enumerate(report.rows, start=1):  # row 0 is the header
            if not row.has_hours:
                styles.append(("BACKGROUND", (0, index), (-1, index), colors.lightgrey))
        return styles

    @staticmethod
    def _format_date(row: RowB) -> str:
        # Same format as the original: 4/9/22
        d = row.date
        return f"{d.day}/{d.month}/{d.year % 100:02d}"

    @staticmethod
    def _format_time(t) -> str:
        # Same format as the original: 8:30
        return f"{t.hour}:{t.minute:02d}" if t is not None else ""