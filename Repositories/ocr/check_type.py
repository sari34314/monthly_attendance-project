
def detect_pdf_type(text: str) -> str:
    keywords = {
        "A": ["הפסקה", "מקום עבודה", "%"],
        "B": ["הערות"]
    }

    scores = {"A": 0, "B": 0}


    for pdf_type, words in keywords.items():
        other = "B" if pdf_type == "A" else "A"

        for word in words:
            count = text.count(word)
            scores[pdf_type] += count

            if count == 0:
                scores[other] += 1

    if scores["A"] > scores["B"]:
        return "A"
    elif scores["B"] > scores["A"]:
        return "B"
    else:
        return "Unknown"
