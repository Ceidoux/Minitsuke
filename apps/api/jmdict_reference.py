from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceCandidate:
    form: str
    reading: str | None = None
    sense_position: int | None = None


def parse_reference_candidates(text: str) -> tuple[ReferenceCandidate, ...]:
    """Propose interpretations; dictionary lookup must validate them."""
    cleaned = text.strip()

    if not cleaned:
        return ()

    candidates: dict[ReferenceCandidate, None] = {}

    def add_variants(surface: str, sense_position: int | None) -> None:
        if not surface:
            return

        candidates[
            ReferenceCandidate(
                form=surface,
                sense_position=sense_position,
            )
        ] = None

        for position, character in enumerate(surface):
            if character != "・":
                continue

            form = surface[:position]
            reading = surface[position + 1 :]

            if not form or not reading:
                continue

            candidates[
                ReferenceCandidate(
                    form=form,
                    reading=reading,
                    sense_position=sense_position,
                )
            ] = None

    # The complete string may itself be a dictionary form.
    add_variants(cleaned, None)

    surface, separator, suffix = cleaned.rpartition("・")

    if (
        separator
        and surface
        and suffix.isascii()
        and suffix.isdecimal()
        and len(suffix) <= 9
    ):
        sense_position = int(suffix)

        if sense_position > 0:
            add_variants(surface, sense_position)

    return tuple(candidates)
