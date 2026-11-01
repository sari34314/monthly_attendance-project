try:
    from bidi import get_display  # python-bidi 0.5 and newer
except ImportError:
    from bidi.algorithm import get_display  # older python-bidi


def rtl(text: str) -> str:
    """Reorder Hebrew text to visual order, because reportlab draws left to right."""
    return get_display(text) if text else text