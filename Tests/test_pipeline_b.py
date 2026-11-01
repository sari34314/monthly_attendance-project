import calendar
import copy
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal

import pytest

from Models.report import Report
from Models.report_row import RowB
from Repositories.common.constants import OUTPUT_YEAR, WEEKDAY_TO_DAY
from Repositories.factory import get_processors
from Repositories.generation.generator_b import GeneratorB
from Repositories.parsing.parser_b import ParserB
from Repositories.transformation.base_transformer import NAMES
from Repositories.transformation.transformer_b import TransformerB

SEEDS = range(20)

SOURCE_ENTRY = time(8, 30)
SOURCE_EXIT = time(12, 0)

# A realistic OCR output of a type B file (September 2022): garbled days,
# lost dates (18/9, 20/9), a lost date line (4/9), a broken exit time (12/9)
OCR_SAMPLE = """
| 1/9/22 | חמישי | 8:30 | | 12:00 |[ 3.50 | 00 |
| 2/9/22 | שישי | 8:30 | | 12:00 || 3.50 | 00 |
:03/9/22 = השבת ןו 0 0 - - -- |
7 --
| 5/9/22 |[ | שי | 8:30 | 12:00 | 3.50 |
| 6/9/22 | שלישי | 8:30 | | 12:00 | |( 350 | |
| 7/9/22 | רביעי | 8:30 | 12:00 | 3.50 | |
| 8/9/22 | חמישי | 8:30 | 12:00 | | 350 | 000 |
| 9/9/22 | שישי |[ 8:30 | | 12:00 || 350[ 00|
09722 שבת | לש | המ ומ - |
| 11/9/22 | ראשון |[ 8:30 | | 12:00 || 350 | 00|
| 12/9/22 |[ | שיר | 8:30 || 1200 | 350 | 00|
| 13/9/22 | שלישי | 8:30 || 12:00 | 3.50 | 00|
| 14/9/22 | רביעי | 8:30 | | 12:00 || 350 | 000 |
| 15/9/22 | חמישי | 8:30 | 12:00 | 3.50 | 20|
| 16/9/22 | | שישי | 8:30 | 12:00 | 3.50 | 00|
922 | ואשון | 8:30 || 12:00 | 3.50 | |
| 19/9/22 | | שני | 8:30 || 12:00 | | 3.50 | 0 |
| 922 | שישי | 8:30 | 12:00 | |( 3.50 |[ |
| 21/9/22 | רביעי | 8:30 | 12:00 | 3.50 | 0 |
| 22/9/22 | חמישי | 8:30 | 12:00 | 3.50 | - |
| 23/9/22 | | שישי | 8:30 | 12:00 | | 3.50 | 00|
| 24/9/22: | שב קה כ --- | |
| 25/9/22 | ראשון | 8:30 | 12:00 | 3.50 |ערב ראש השנה
| 26/9/22 | | שמ | | | = |אש השנה,
| 27/9/22 | שלישי | | | | | = |אש השנה,
| 28/9/22 | רביעי || 8:30 || 12:00 | | 3.50 [ 00|
| 29/9/22 | המישי | 8:30 || 12:00 | |( 3.50 | 00|
| 30/9/22 || שיש | 8:30 || 12:00 | | 3.50 | 00|
"""


def minutes(t):
    return t.hour * 60 + t.minute


def make_row(d):
    day = WEEKDAY_TO_DAY[d.weekday()]

    if d.weekday() == 5:  # Saturday: an empty row
        return RowB(
            date=d, day=day, entry_time=None, exit_time=None, total=None, notes=None
        )

    return RowB(
        date=d,
        day=day,
        entry_time=SOURCE_ENTRY,
        exit_time=SOURCE_EXIT,
        total=Decimal("3.50"),
        notes=None,
    )


def make_report():
    rows = [make_row(date(2022, 9, n)) for n in range(1, 31)]
    return Report(employee_name="", rows=rows, company_name=None)


def run(seed, report=None):
    return TransformerB(seed).transform(report or make_report())


# ----------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def parsed():
    return ParserB().parse(OCR_SAMPLE)


def by_day(report, n):
    return next(r for r in report.rows if r.date.day == n)


def test_parser_builds_the_full_month(parsed):
    assert len(parsed.rows) == 30
    assert [r.date for r in parsed.rows] == [date(2022, 9, n) for n in range(1, 31)]


def test_parser_day_matches_date(parsed):
    for row in parsed.rows:
        assert row.day == WEEKDAY_TO_DAY[row.date.weekday()]


@pytest.mark.parametrize("n", [3, 10, 17, 24])
def test_parser_saturdays_are_empty(parsed, n):
    row = by_day(parsed, n)
    assert not row.has_hours
    assert row.total is None
    assert row.notes is None


@pytest.mark.parametrize("n", [4, 12, 18, 20])
def test_parser_recovers_rows_the_ocr_damaged(parsed, n):
    row = by_day(parsed, n)
    assert row.entry_time == time(8, 30)
    assert row.exit_time == time(12, 0)
    assert row.total == Decimal("3.50")


@pytest.mark.parametrize("n", [25, 26, 27])
def test_parser_former_holidays_are_regular_workdays(parsed, n):
    # Holiday notes are not kept, so these rows get the common hours
    row = by_day(parsed, n)
    assert row.entry_time == time(8, 30)
    assert row.exit_time == time(12, 0)
    assert row.total == Decimal("3.50")


def test_parser_has_no_notes(parsed):
    assert all(r.notes is None for r in parsed.rows)


def test_parser_without_dates_returns_no_rows():
    assert ParserB().parse("no dates here").rows == []


# ----------------------------------------------------------------------
# Transformer: determinism
# ----------------------------------------------------------------------
def test_same_seed_gives_identical_output():
    assert run(seed=7) == run(seed=7)


def test_different_seeds_give_different_output():
    assert run(seed=1) != run(seed=2)


def test_original_report_is_not_modified():
    original = make_report()
    snapshot = copy.deepcopy(original)
    run(seed=3, report=original)
    assert original == snapshot


# ----------------------------------------------------------------------
# Transformer: month and year
# ----------------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_year_is_the_output_year(seed):
    for row in run(seed).rows:
        assert row.date.year == OUTPUT_YEAR


@pytest.mark.parametrize("seed", SEEDS)
def test_rows_cover_every_day_of_one_month(seed):
    rows = run(seed).rows
    first = rows[0].date
    last_day = calendar.monthrange(first.year, first.month)[1]

    assert 1 <= first.month <= 12
    assert [r.date for r in rows] == [
        date(first.year, first.month, n) for n in range(1, last_day + 1)
    ]


def test_month_is_drawn_from_the_seed():
    months = {run(seed).rows[0].date.month for seed in SEEDS}
    assert len(months) > 1


# ----------------------------------------------------------------------
# Transformer: invariants, checked on many seeds
# ----------------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_day_name_matches_date(seed):
    for row in run(seed).rows:
        assert row.day == WEEKDAY_TO_DAY[row.date.weekday()]


@pytest.mark.parametrize("seed", SEEDS)
def test_saturdays_are_empty_rows(seed):
    for row in run(seed).rows:
        if row.date.weekday() == 5:
            assert not row.has_hours
            assert row.total is None
            assert row.notes is None


@pytest.mark.parametrize("seed", SEEDS)
def test_every_other_day_has_hours(seed):
    for row in run(seed).rows:
        if row.date.weekday() != 5:
            assert row.has_hours


@pytest.mark.parametrize("seed", SEEDS)
def test_notes_are_never_created(seed):
    for row in run(seed).rows:
        assert row.notes is None


@pytest.mark.parametrize("seed", SEEDS)
def test_exit_is_after_entry(seed):
    for row in run(seed).rows:
        if row.has_hours:
            assert minutes(row.exit_time) > minutes(row.entry_time)


@pytest.mark.parametrize("seed", SEEDS)
def test_times_move_at_most_60_minutes(seed):
    # Every source row has the same hours, so each new row is compared to them
    for row in run(seed).rows:
        if row.has_hours:
            assert abs(minutes(row.entry_time) - minutes(SOURCE_ENTRY)) <= 60
            assert abs(minutes(row.exit_time) - minutes(SOURCE_EXIT)) <= 60


@pytest.mark.parametrize("seed", SEEDS)
def test_friday_exit_is_not_after_12(seed):
    for row in run(seed).rows:
        if row.has_hours and row.date.weekday() == 4:
            assert minutes(row.exit_time) <= 12 * 60


@pytest.mark.parametrize("seed", SEEDS)
def test_total_is_exit_minus_entry(seed):
    for row in run(seed).rows:
        if row.has_hours:
            worked = minutes(row.exit_time) - minutes(row.entry_time)
            expected = (Decimal(worked) / 60).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            assert row.total == expected


@pytest.mark.parametrize("seed", SEEDS)
def test_name_comes_from_the_names_list(seed):
    assert run(seed).employee_name in NAMES


@pytest.mark.parametrize("seed", SEEDS)
def test_type_b_has_no_summary(seed):
    assert run(seed).summary is None


# ----------------------------------------------------------------------
# Transformer: edge cases
# ----------------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_few_source_rows_still_fill_the_whole_month(seed):
    # Three working rows are reused in order until the month is full
    rows = [make_row(date(2022, 9, n)) for n in (1, 2, 4)]
    report = Report(employee_name="", rows=rows, company_name=None)

    new = run(seed, report)

    for row in new.rows:
        assert row.has_hours == (row.date.weekday() != 5)


def test_report_without_working_rows_raises():
    rows = [make_row(date(2022, 9, 3))]  # A Saturday: no hours
    report = Report(employee_name="", rows=rows, company_name=None)

    with pytest.raises(ValueError):
        run(1, report)


# ----------------------------------------------------------------------
# Generator and factory
# ----------------------------------------------------------------------
def test_generate_creates_a_pdf(tmp_path):
    report = run(seed=1)
    output = tmp_path / "out_b.pdf"

    GeneratorB().generate(report, str(output))

    assert output.exists()
    assert output.stat().st_size > 0


def test_generator_formats_like_the_original():
    cells = GeneratorB()._row_cells(make_row(date(2022, 9, 4)))
    assert cells[0] == "4/9/22"
    assert cells[2] == "8:30"
    assert cells[3] == "12:0" + "0"
    assert cells[4] == "3.50"


def test_generator_shows_the_output_year():
    cells = GeneratorB()._row_cells(make_row(date(OUTPUT_YEAR, 3, 4)))
    assert cells[0] == f"4/3/{OUTPUT_YEAR % 100:02d}"


def test_factory_returns_the_type_b_classes():
    parser, transformer, generator = get_processors("B")
    assert (parser, transformer, generator) == (ParserB, TransformerB, GeneratorB)


def test_factory_rejects_an_unknown_type():
    with pytest.raises(ValueError):
        get_processors("Unknown")