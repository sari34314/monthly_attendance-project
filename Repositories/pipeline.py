from Models.report import Report
from Repositories.common.constants import DEFAULT_SEED
from Repositories.factory import get_processors
from Repositories.ocr.check_type import detect_pdf_type


def run_pipeline(text: str, output_path: str, seed: int = DEFAULT_SEED) -> Report:
    """Run the whole pipeline: detect type, parse, transform, generate.

    Receives the OCR text of one page and the path of the output PDF.
    Returns the new (transformed) report.
    """
    pdf_type = detect_pdf_type(text)
    parser_class, transformer_class, generator_class = get_processors(pdf_type)

    report = parser_class().parse(text)
    new_report = transformer_class(seed).transform(report)
    generator_class().generate(new_report, output_path)

    return new_report
