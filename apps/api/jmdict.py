from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

COMMON_PRIORITY_TAGS = frozenset({"news1", "ichi1", "spec1", "spec2", "gai1"})


@dataclass(frozen=True)
class JmdictGloss:
    text: str
    language: str


@dataclass(frozen=True)
class JmdictSense:
    glosses: tuple[JmdictGloss, ...]
    restricted_to_written_forms: tuple[str, ...] = ()
    restricted_to_readings: tuple[str, ...] = ()
    parts_of_speech: tuple[str, ...] = ()


@dataclass(frozen=True)
class JmdictReading:
    text: str
    restricted_to: tuple[str, ...] = ()
    no_kanji: bool = False


@dataclass(frozen=True)
class JmdictEntry:
    source_id: int
    written_forms: tuple[str, ...]
    readings: tuple[JmdictReading, ...]
    senses: tuple[JmdictSense, ...]
    is_common: bool = False


def parse_entry(element: ET.Element) -> JmdictEntry:
    source_id_text = element.findtext("ent_seq")
    if source_id_text is None or not source_id_text.strip():
        raise ValueError("JMdict entry is missing ent_seq")

    try:
        source_id = int(source_id_text)
    except ValueError as error:
        raise ValueError("JMdict ent_seq must be an integer") from error

    written_forms = tuple(
        node.text for node in element.findall("k_ele/keb") if node.text is not None
    )

    readings = tuple(
        JmdictReading(
            text=reading_text,
            restricted_to=tuple(
                node.text
                for node in reading.findall("re_restr")
                if node.text is not None
            ),
            no_kanji=reading.find("re_nokanji") is not None,
        )
        for reading in element.findall("r_ele")
        if (reading_text := reading.findtext("reb")) is not None
    )
    if not readings:
        raise ValueError("JMdict entry must contain at least one reading")

    if any(not reading.text.strip() for reading in readings):
        raise ValueError("JMdict reading must not be blank")

    senses: list[JmdictSense] = []
    previous_parts_of_speech: tuple[str, ...] = ()

    for sense in element.findall("sense"):
        explicit_parts_of_speech = tuple(
            node.text for node in sense.findall("pos") if node.text is not None
        )

        parts_of_speech = explicit_parts_of_speech or previous_parts_of_speech
        previous_parts_of_speech = parts_of_speech

        senses.append(
            JmdictSense(
                glosses=tuple(
                    JmdictGloss(
                        text=node.text,
                        language=node.get(
                            "{http://www.w3.org/XML/1998/namespace}lang",
                            "eng",
                        ),
                    )
                    for node in sense.findall("gloss")
                    if node.text is not None
                ),
                restricted_to_written_forms=tuple(
                    node.text
                    for node in sense.findall("stagk")
                    if node.text is not None
                ),
                restricted_to_readings=tuple(
                    node.text
                    for node in sense.findall("stagr")
                    if node.text is not None
                ),
                parts_of_speech=parts_of_speech,
            )
        )
    if not senses:
        raise ValueError("JMdict entry must contain at least one sense")
    is_common = any(
        node.text in COMMON_PRIORITY_TAGS
        for path in ("k_ele/ke_pri", "r_ele/re_pri")
        for node in element.findall(path)
    )
    return JmdictEntry(
        source_id=source_id,
        written_forms=written_forms,
        readings=readings,
        senses=tuple(senses),
        is_common=is_common,
    )


def read_jmdict(path: Path) -> Iterator[JmdictEntry]:
    with path.open("rb") as source:
        events = ET.iterparse(source, events=("start", "end"))
        _, root = next(events)

        if root.tag != "JMdict":
            raise ValueError("Expected JMdict root element")

        for event, element in events:
            if event == "end" and element.tag == "entry":
                entry = parse_entry(element)
                root.remove(element)
                element.clear()
                yield entry
