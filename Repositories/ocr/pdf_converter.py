import re
from datetime import datetime

import pytesseract
from pdf2image import convert_from_path
from PIL import ImageOps

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

POPPLER_PATH = r"C:\poppler\poppler-26.09.0\Library\bin"

TIME_RE = re.compile(r"\b\d{2}:\d{2}\b")
DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")


def render_page(pdf_path: str, page_number: int):
    pages = convert_from_path(
        pdf_path,
        dpi=400,
        first_page=page_number,
        last_page=page_number,
        poppler_path=POPPLER_PATH,
    )
    image = pages[0].convert("L")
    return ImageOps.autocontrast(image)


def extract_dates(image) -> list[str]:
    data = pytesseract.image_to_data(
        image,
        lang="eng",
        config="--psm 11 -c tessedit_char_whitelist=0123456789/",
        output_type=pytesseract.Output.DICT,
    )

    found = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not DATE_RE.fullmatch(word):
            continue
        try:
            datetime.strptime(word, "%d/%m/%Y")
        except ValueError:
            print("תאריך לא תקין, דילגתי:", word)
            continue
        found.append((data["top"][i], word))

    found.sort()  # לפי מיקום אנכי, מלמעלה למטה
    return [date_text for _, date_text in found]

def add_dates_to_rows(text: str, dates: list[str]) -> str:
    lines = text.splitlines()

    # שורת נתונים = שורה עם לפחות שלוש שעות
    data_lines = [i for i, line in enumerate(lines) if len(TIME_RE.findall(line)) >= 3]

    if len(data_lines) != len(dates):
        print(
            "מספר התאריכים לא תואם למספר השורות:",
            len(dates),
            len(data_lines),
        )
        return text

    for i, date_text in zip(data_lines, dates):
        lines[i] = f"{date_text} {lines[i]}"

    return "\n".join(lines)


def pdf_page_to_text(pdf_path: str, page_number: int = 1) -> str:
    image = render_page(pdf_path, page_number)

    text = pytesseract.image_to_string(
        image,
        lang="heb",
        config="--psm 6",
    )
    dates = extract_dates(image)

    return clean_text(add_dates_to_rows(text, dates))

def clean_text(text: str) -> str:
    text = text.replace("\x0c", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()


