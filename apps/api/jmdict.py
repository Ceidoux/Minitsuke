from dataclasses import dataclass
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class JmdictGloss:
    text: str
    language: str


@dataclass(frozen=True)
class JmdictSense:
    glosses: tuple[JmdictGloss, ...]


@dataclass(frozen=True)
class JmdictEntry:
    source_id: int
    written_forms: tuple[str, ...]
    readings: tuple[str, ...]
    senses: tuple[JmdictSense, ...]


def parse_entry(element: ET.Element) -> JmdictEntry:
    source_id_text = element.findtext("ent_seq")
    if source_id_text is None:
        raise ValueError("JMdict entry is missing ent_seq")

    written_forms = tuple(
        node.text for node in element.findall("k_ele/keb") if node.text is not None
    )

    readings = tuple(
        node.text for node in element.findall("r_ele/reb") if node.text is not None
    )

    senses = tuple(
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
            )
        )
        for sense in element.findall("sense")
    )

    return JmdictEntry(
        source_id=int(source_id_text),
        written_forms=written_forms,
        readings=readings,
        senses=senses,
    )
