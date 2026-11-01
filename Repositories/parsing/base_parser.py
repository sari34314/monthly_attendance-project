import re
from abc import ABC, abstractmethod

from Models.report import Report
from Models.report_row import ReportRow


class BaseParser(ABC):
    """Turns OCR text into a Report. Subclasses define how one row is read."""

    def parse(self, text: str) -> Report:
        # Shared skeleton: same steps for every type
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        report = Report(employee_name="", company_name=self._find_company(lines))

        for line in lines:
            row = self._parse_row(line)
            if row is not None:
                report.rows.append(row)

        return self._finish(report, lines)

    def _find_company(self, lines: list[str]) -> str | None:
        # The first line with Hebrew letters, before the header line
        for line in lines:
            if "כניסה" in line:
                break
            if re.search(r"[א-ת]", line):
                return line
        return None

    def _finish(self, report: Report, lines: list[str]) -> Report:
        # Hook for subclasses that need a final step (e.g. A reads a summary)
        return report

    @abstractmethod
    def _parse_row(self, line: str) -> ReportRow | None:
        """Return a row built from the line, or None if it is not a data row."""