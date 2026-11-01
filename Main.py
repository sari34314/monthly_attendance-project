
from pathlib import Path

from Repositories.ocr.pdf_converter import pdf_page_to_text
from Repositories.pipeline import run_pipeline


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "inputs"
OUTPUT_DIR = BASE_DIR / "outputs"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(INPUT_DIR.glob("*.pdf")):
        try:
            text = pdf_page_to_text(str(pdf_path), page_number=1)

            output_path = OUTPUT_DIR / f"{pdf_path.stem}_output.pdf"

            run_pipeline(text, str(output_path))

            print(f"Created: {output_path.name}")

        except Exception as error:
            print(f"Failed to process {pdf_path.name}: {error}")


if __name__ == "__main__":
    main()
