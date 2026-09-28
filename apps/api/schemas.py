from pydantic import BaseModel, Field

from conjugation import ConjugatedForm


class WordEntry(BaseModel):
    written_form: str
    reading: str
    meanings: list[str]


class SearchResponse(BaseModel):
    query: str
    results: list[WordEntry]


class JmdictGlossResponse(BaseModel):
    text: str
    language: str


class JmdictReadingResponse(BaseModel):
    text: str
    no_kanji: bool
    restricted_to: list[str]


class JmdictSenseResponse(BaseModel):
    glosses: list[JmdictGlossResponse]
    parts_of_speech: list[str]
    restricted_to_written_forms: list[str]
    restricted_to_readings: list[str]
    misc: list[str] = Field(default_factory=list)


class JmdictEntryResponse(BaseModel):
    source_id: int
    is_common: bool
    written_forms: list[str]
    readings: list[JmdictReadingResponse]
    senses: list[JmdictSenseResponse]


class ConjugationCompletionResponse(BaseModel):
    written: str
    reading: str
    group: str
    form: str
    description: str


class InflectionResponse(BaseModel):
    source_ids: list[int]
    description: str
    descriptions: dict[int, list[str]] = Field(default_factory=dict)
    completions: dict[int, list[ConjugationCompletionResponse]] = Field(
        default_factory=dict
    )


class JmdictSearchResponse(BaseModel):
    query: str
    results: list[JmdictEntryResponse]
    limit: int
    offset: int
    has_more: bool
    inflection: InflectionResponse | None = None


class ConjugationTableResponse(BaseModel):
    written: str
    reading: str
    verb_class: str
    sense_positions: list[int]
    forms: list[ConjugatedForm]


class JmdictEntryDetailResponse(JmdictEntryResponse):
    conjugations: list[ConjugationTableResponse] = Field(default_factory=list)
    conjugations_incomplete: bool = False
