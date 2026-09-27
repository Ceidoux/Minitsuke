from dataclasses import dataclass

from sudachipy import Dictionary, SplitMode

MAX_SENTENCE_LENGTH = 1_000


@dataclass(frozen=True)
class SentenceToken:
    surface: str
    start: int
    end: int
    dictionary_form: str
    normalized_form: str
    reading: str
    part_of_speech: tuple[str, ...]
    is_unknown: bool


class SentenceAnalyzer:
    def __init__(self) -> None:
        self._dictionary = Dictionary(dict="core")

    def analyze(self, text: str) -> tuple[SentenceToken, ...]:
        if not text.strip():
            raise ValueError("Sentence must not be empty")

        if len(text) > MAX_SENTENCE_LENGTH:
            raise ValueError(
                f"Sentence must contain at most {MAX_SENTENCE_LENGTH} characters"
            )

        tokenizer = self._dictionary.create()
        tokens = []

        for morpheme in tokenizer.tokenize(text, SplitMode.C):
            start = morpheme.begin()
            end = morpheme.end()

            tokens.append(
                SentenceToken(
                    surface=text[start:end],
                    start=start,
                    end=end,
                    dictionary_form=morpheme.dictionary_form(),
                    normalized_form=morpheme.normalized_form(),
                    reading=morpheme.reading_form(),
                    part_of_speech=tuple(morpheme.part_of_speech()),
                    is_unknown=morpheme.is_oov(),
                )
            )

        return tuple(tokens)
