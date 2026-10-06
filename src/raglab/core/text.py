"""Text helpers every layer can use. Standard library only."""


def normalise_space(text: str) -> str:
    """Every run of whitespace as one space, trimmed."""
    return " ".join(text.split())


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance: insertions, deletions and substitutions, each of cost 1."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b))
            )
        previous = current
    return previous[-1]


def character_error_rate(hypothesis: str, reference: str) -> float:
    """Edit distance between the two texts over the reference's length, after whitespace runs are
    made single spaces (line breaks are layout, not characters a reader reads)."""
    ref = normalise_space(reference)
    if not ref:
        raise ValueError("the reference text is empty")
    return edit_distance(normalise_space(hypothesis), ref) / len(ref)
