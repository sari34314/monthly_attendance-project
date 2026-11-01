import re
from datetime import datetime
from decimal import Decimal

from Models.report import Report, ReportSummary
from Models.report_row import Day, RowA
from Repositories.parsing.base_parser import BaseParser

TIME_RE = re.compile(r"\b\d{2}:\d{2}\b")
NUMBER_RE = re.compile(r"\d+\.\d{2}")
DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")
DAYS_RE = re.compile(r"ימים\s*(\d+)")


class ParserA(BaseParser):
    def _parse_row(self, line: str) -> RowA | None:
        times = TIME_RE.findall(line)
        numbers = NUMBER_RE.findall(line)

        # A data row has three times (entry, exit, break) and five decimal numbers
        if len(times) < 3 or len(numbers) < 5:
            return None

        total, p100, p125, p150, shabbat = (Decimal(n) for n in numbers[:5])

        try:
            entry_time = datetime.strptime(times[0], "%H:%M").time()
            exit_time = datetime.strptime(times[1], "%H:%M").time()
            break_time = datetime.strptime(times[2], "%H:%M").time()
        except ValueError:
            print("Row with an invalid time, skipped:", line)
            return None

        return RowA(
            date=self._find_date(line),
            day=self._find_day(line, shabbat),
            entry_time=entry_time,
            exit_time=exit_time,
            total=total,
            workplace=self._find_workplace(line),
            break_time=break_time,
            percent_100=p100,
            percent_125=p125,
            percent_150=p150,
            shabbat_150=shabbat,
        )

    def _finish(self, report: Report, lines: list[str]) -> Report:
        report.summary = self._parse_summary(lines)
        return report

    def _find_date(self, line: str):
        match = DATE_RE.search(line)
        if match is None:
            return None
        try:
            return datetime.strptime(match.group(), "%d/%m/%Y").date()
        except ValueError:
            return None

    def _find_day(self, line: str, shabbat: Decimal) -> Day | None:
        for day in Day:
            if day.value in line:
                return day
        # The OCR garbles the word for Saturday, so Saturday hours mean it is Saturday
        return Day.SATURDAY if shabbat > 0 else None

    def _find_workplace(self, line: str) -> str | None:
        # The text before the first time, without the word "day" and the day name
        before_times = line[: TIME_RE.search(line).start()].replace("יום", "")
        for day in Day:
            before_times = before_times.replace(day.value, "")
        words = re.findall(r"[א-ת\"'׳״]+", before_times)
        return " ".join(words) or None

    def _parse_summary(self, lines: list[str]) -> ReportSummary | None:
        days = None
        summary_numbers = None

        for line in lines:
            if TIME_RE.search(line):
                continue  # A regular data row, skip

            numbers = NUMBER_RE.findall(line)
            if len(numbers) >= 5 and summary_numbers is None:
                summary_numbers = numbers[-5:]

            match = DAYS_RE.search(line)
            if match and days is None:
                days = int(match.group(1))

        if summary_numbers is None:
            return None

        total, p100, p125, p150, shabbat = (Decimal(n) for n in summary_numbers)

        return ReportSummary(
            days=days,
            total=total,
            percent_100=p100,
            percent_125=p125,
            percent_150=p150,
            shabbat_150=shabbat,
        )