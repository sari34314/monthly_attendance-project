from Models.report_row import Day

# Default seed, so the same input always gives the same output
DEFAULT_SEED = 42
# The year of every generated report
OUTPUT_YEAR = 2026

# A font with Hebrew letters (Arial is installed on Windows)
FONT_NAME = "Arial"
FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

# Python weekday(): Monday = 0 ... Sunday = 6
WEEKDAY_TO_DAY = {
    0: Day.MONDAY,
    1: Day.TUESDAY,
    2: Day.WEDNESDAY,
    3: Day.THURSDAY,
    4: Day.FRIDAY,
    5: Day.SATURDAY,
    6: Day.SUNDAY,
}

# Known holiday notes. The OCR garbles them, so a fragment is enough to recognize one.
# Order matters: the longer text must come first.
HOLIDAY_NOTES = {}