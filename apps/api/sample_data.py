from schemas import WordEntry

SAMPLE_WORDS: tuple[WordEntry, ...] = (
    WordEntry(
        written_form="食べる",
        reading="たべる",
        meanings=["to eat"],
    ),
    WordEntry(
        written_form="食事",
        reading="しょくじ",
        meanings=["meal"],
    ),
    WordEntry(
        written_form="学校",
        reading="がっこう",
        meanings=["school"],
    ),
)
