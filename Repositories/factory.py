from Repositories.generation.generator_a import GeneratorA
from Repositories.generation.generator_b import GeneratorB
from Repositories.parsing.parser_a import ParserA
from Repositories.parsing.parser_b import ParserB
from Repositories.transformation.transformer_a import TransformerA
from Repositories.transformation.transformer_b import TransformerB

# One row per report type. Adding a type means adding one line here.
PROCESSORS = {
    "A": (ParserA, TransformerA, GeneratorA),
    "B": (ParserB, TransformerB, GeneratorB),
}


def get_processors(pdf_type: str) -> tuple:
    """Return (parser class, transformer class, generator class) for a type."""
    try:
        return PROCESSORS[pdf_type]
    except KeyError:
        raise ValueError(f"Unsupported report type: {pdf_type!r}") from None