import calendar
import copy
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal

import pytest

from Models.report import Report
from Models.report_row import RowA
from Repositories.common.constants import OUTPUT_YEAR
from Repositories.generation.generator_a import GeneratorA
from Repositories.transformation.base_transformer import NAMES
from Repositories.transformation.transformer_a import WEEKDAY_TO_DAY, TransformerA

SEEDS = range(20)
MONTHS = range(1, 13)

# Dates of the real sample file (October 2022)
SAMPLE_DAYS = [2, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17,
               18, 20, 21, 22, 23, 25, 26, 27, 28, 30, 31]


def make_row(d):
    zero = Decimal("0.00")
    return RowA(
        date=d,
        day=WEEKDAY_TO_DAY[d.weekday()] if d else None,
        entry_time=time(8, 0),
        exit_time=time(15, 0),
        total=Decimal("6.50"),
        workplace="test place",
        break_time=time(0, 30),
        percent_100=Decimal("6.50"),
        percent_125=zero,
        percent_150=zero,
        shabbat_150=zero,
    )


def make_report(days=SAMPLE_DAYS):
    rows = [make_row(date(2022, 10, d)) for d in days]
    return Report(employee_name="", rows=rows, company_name="test company")


def minutes(t):
    return t.hour * 60 + t.minute


def run(seed, report=None):
    return TransformerA(seed).transform(report or make_report())


# ----------------------------------------------------------------------
# Determinism
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
# Month and year
# ----------------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_year_is_the_output_year(seed):
    for row in run(seed).rows:
        assert row.date.year == OUTPUT_YEAR


@pytest.mark.parametrize("seed", SEEDS)
def test_all_rows_are_in_one_month(seed):
    months = {row.date.month for row in run(seed).rows}
    assert len(months) == 1
    assert 1 <= months.pop() <= 12


def test_month_is_drawn_from_the_seed():
    months = {run(seed).rows[0].date.month for seed in SEEDS}
    assert len(months) > 1


@pytest.mark.parametrize("month", MONTHS)
@pytest.mark.parametrize("seed", range(5))
def test_every_month_gives_valid_ascending_dates(seed, month):
    # Calls the date step directly, to check all 12 months (including February)
    dates = [row.date for row in make_report().rows]
    new = TransformerA(seed)._new_dates(dates, OUTPUT_YEAR, month)

    last_day = calendar.monthrange(OUTPUT_YEAR, month)[1]
    assert len(new) == len(dates)
    assert all(a < b for a, b in zip(new, new[1:]))
    assert all(d.year == OUTPUT_YEAR and d.month == month for d in new)
    assert all(1 <= d.day <= last_day for d in new)


@pytest.mark.parametrize("seed", range(5))
def test_date_moves_at_most_one_day_in_a_31_day_month(seed):
    # In a month with 31 days the day numbers fit as they are, so a row
    # can only move by the allowed one day
    original = make_report()
    dates = [row.date for row in original.rows]
    new = TransformerA(seed)._new_dates(dates, OUTPUT_YEAR, 1)

    for old_date, new_date in zip(dates, new):
        assert abs(new_date.day - old_date.day) <= 1


def test_more_rows_than_days_in_the_month_raises():
    dates = [date(2022, 10, d) for d in range(1, 32)]
    with pytest.raises(ValueError):
        TransformerA(1)._new_dates(dates, OUTPUT_YEAR, 2)


# ----------------------------------------------------------------------
# Invariants, checked on many seeds
# ----------------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_row_count_is_kept(seed):
    assert len(run(seed).rows) == len(SAMPLE_DAYS)


@pytest.mark.parametrize("seed", SEEDS)
def test_dates_are_strictly_ascending(seed):
    dates = [row.date for row in run(seed).rows]
    assert all(a < b for a, b in zip(dates, dates[1:]))


@pytest.mark.parametrize("seed", SEEDS)
def test_day_name_matches_date(seed):
    for row in run(seed).rows:
        assert row.day == WEEKDAY_TO_DAY[row.date.weekday()]


@pytest.mark.parametrize("seed", SEEDS)
def test_exit_is_after_entry(seed):
    for row in run(seed).rows:
        assert minutes(row.exit_time) > minutes(row.entry_time)


@pytest.mark.parametrize("seed", SEEDS)
def test_times_move_at_most_60_minutes(seed):
    original = make_report()
    new = run(seed, original)
    for old_row, row in zip(original.rows, new.rows):
        assert abs(minutes(row.entry_time) - minutes(old_row.entry_time)) <= 60
        assert abs(minutes(row.exit_time) - minutes(old_row.exit_time)) <= 60


@pytest.mark.parametrize("seed", SEEDS)
def test_break_moves_at_most_5_minutes(seed):
    original = make_report()
    new = run(seed, original)
    for old_row, row in zip(original.rows, new.rows):
        assert abs(minutes(row.break_time) - minutes(old_row.break_time)) <= 5


@pytest.mark.parametrize("seed", SEEDS)
def test_total_is_exit_minus_entry_minus_break(seed):
    for row in run(seed).rows:
        worked = (
            minutes(row.exit_time) - minutes(row.entry_time) - minutes(row.break_time)
        )
        expected = (Decimal(worked) / 60).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        assert row.total == expected


@pytest.mark.parametrize("seed", SEEDS)
def test_hour_columns_add_up_to_total(seed):
    for row in run(seed).rows:
        columns = (
            row.percent_100 + row.percent_125 + row.percent_150 + row.shabbat_150
        )
        assert columns == row.total


@pytest.mark.parametrize("seed", SEEDS)
def test_summary_matches_rows(seed):
    report = run(seed)
    rows = report.rows
    assert report.summary.days == len(rows)
    assert report.summary.total == sum(r.total for r in rows)
    assert report.summary.percent_100 == sum(r.percent_100 for r in rows)
    assert report.summary.percent_125 == sum(r.percent_125 for r in rows)
    assert report.summary.percent_150 == sum(r.percent_150 for r in rows)
    assert report.summary.shabbat_150 == sum(r.shabbat_150 for r in rows)


@pytest.mark.parametrize("seed", SEEDS)
def test_name_comes_from_the_names_list(seed):
    assert run(seed).employee_name in NAMES


# ----------------------------------------------------------------------
# Edge cases
# ----------------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_missing_date_is_filled_and_order_is_kept(seed):
    report = make_report()
    report.rows[5].date = None
    report.rows[6].date = None

    new = run(seed, report)

    dates = [row.date for row in new.rows]
    assert all(d is not None for d in dates)
    assert all(a < b for a, b in zip(dates, dates[1:]))


@pytest.mark.parametrize("seed", SEEDS)
def test_consecutive_dates_stay_valid(seed):
    # Little room to move: 28 rows fit in every month, even February
    new = run(seed, make_report(days=list(range(1, 29))))
    dates = [row.date for row in new.rows]
    assert all(a < b for a, b in zip(dates, dates[1:]))
    assert len({(d.year, d.month) for d in dates}) == 1


# ----------------------------------------------------------------------
# Generate
# ----------------------------------------------------------------------
def test_generate_creates_a_pdf(tmp_path):
    report = run(seed=1)
    output = tmp_path / "out.pdf"

    GeneratorA().generate(report, str(output))

    assert output.exists()
    assert output.stat().st_size > 0