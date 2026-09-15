from pydantic import BaseModel


class WordEntry(BaseModel):
    written_form: str
    reading: str
    meanings: list[str]


class SearchResponse(BaseModel):
    query: str
    results: list[WordEntry]
