from dataclasses import dataclass, field
from decimal import Decimal

from Models.report_row import ReportRow


@dataclass
class ReportSummary:
    days: int | None
    total: Decimal
    percent_100: Decimal
    percent_125: Decimal
    percent_150: Decimal
    shabbat_150: Decimal


@dataclass
class Report:
    employee_name: str
    rows: list[ReportRow] = field(default_factory=list)
    company_name: str | None = None
    summary: ReportSummary | None = None