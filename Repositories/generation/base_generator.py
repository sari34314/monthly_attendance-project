import os
from abc import ABC, abstractmethod
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from Models.report import Report
from Models.report_row import ReportRow
from Repositories.common.constants import FONT_NAME, FONT_PATH
from Repositories.common.text_utils import rtl


class BaseGenerator(ABC):
    """Draws a Report as a PDF. Subclasses define the columns."""

    # Columns in reading order (the first column is drawn on the right side)
    headers: list[str] = []
    # Column widths in points, in the same order as headers
    column_widths: list[int] = []

    def generate(self, report: Report, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

        company_style = ParagraphStyle(
            "company", fontName=FONT_NAME, fontSize=14, leading=18, alignment=TA_CENTER
        )
        name_style = ParagraphStyle(
            "name", fontName=FONT_NAME, fontSize=12, leading=16, alignment=TA_CENTER
        )

        # Header row, data rows, and an optional summary row at the end
        table_rows = [self.headers] + [self._row_cells(row) for row in report.rows]
        summary = self._summary_cells(report)
        if summary is not None:
            table_rows.append(summary)

        # Hebrew reads right to left, so the first column goes on the right side
        visual_rows = [[rtl(cell) for cell in reversed(cells)] for cells in table_rows]

        table = Table(
            visual_rows, colWidths=list(reversed(self.column_widths)), repeatRows=1
        )

        style = [
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ]

        if summary is not None:
            style.append(("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey))
        style.extend(self._extra_styles(report))
        table.setStyle(TableStyle(style))

        story = [
            Paragraph(escape(rtl(report.company_name or "")), company_style),
            Paragraph(escape(rtl(report.employee_name)), name_style),
            Spacer(1, 10),
            table,
        ]

        SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30,
        ).build(story)

    @abstractmethod
    def _row_cells(self, row: ReportRow) -> list[str]:
        """Cells of one data row, in the same order as headers."""

    def _summary_cells(self, report: Report) -> list[str] | None:
        """Cells of the summary row, or None when the type has no summary."""
        return None

    def _extra_styles(self, report: Report) -> list:
        """Extra table styles (for example shaded rows). None by default."""
        return []