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
    gloss_type: str | None = None
    gender: str | None = None


class JmdictReadingResponse(BaseModel):
    text: str
    no_kanji: bool
    restricted_to: list[str]
    info: list[str] = Field(default_factory=list)


class JmdictReferenceTargetResponse(BaseModel):
    source_id: int
    sense_position: int | None = None


class JmdictReferenceResponse(BaseModel):
    text: str
    targets: list[JmdictReferenceTargetResponse] = Field(default_factory=list)


class JmdictLoanSourceResponse(BaseModel):
    text: str | None = None
    language: str
    source_type: str
    wasei: bool


class JmdictSenseResponse(BaseModel):
    glosses: list[JmdictGlossResponse]
    parts_of_speech: list[str]
    restricted_to_written_forms: list[str]
    restricted_to_readings: list[str]
    misc: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    dialects: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    cross_references: list[JmdictReferenceResponse] = Field(default_factory=list)
    antonyms: list[JmdictReferenceResponse] = Field(default_factory=list)
    loan_sources: list[JmdictLoanSourceResponse] = Field(default_factory=list)


class JmdictEntryResponse(BaseModel):
    source_id: int
    is_common: bool
    written_forms: list[str]
    readings: list[JmdictReadingResponse]
    senses: list[JmdictSenseResponse]
    written_form_info: dict[str, list[str]] = Field(default_factory=dict)


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
