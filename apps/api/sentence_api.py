from functools import lru_cache
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_session
from sentence_analysis import MAX_SENTENCE_LENGTH, SentenceAnalyzer
from sentence_grouping import group_sentence
from sentence_service import resolve_sentence

router = APIRouter(prefix="/api/v1", tags=["sentence analysis"])


class SentenceAnalysisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_SENTENCE_LENGTH)


class SentenceTokenResponse(BaseModel):
    surface: str
    start: int
    end: int
    dictionary_form: str
    normalized_form: str
    reading: str
    part_of_speech: list[str]
    is_unknown: bool
    candidate_source_ids: list[int]


class SentenceGroupResponse(BaseModel):
    surface: str
    start: int
    end: int
    candidate_source_ids: list[int]
    tokens: list[SentenceTokenResponse]


class SentenceAnalysisResponse(BaseModel):
    text: str
    offset_unit: str = "unicode_code_points"
    groups: list[SentenceGroupResponse]


_analyzer_lock = Lock()


@lru_cache(maxsize=1)
def _cached_analyzer() -> SentenceAnalyzer:
    return SentenceAnalyzer()


def get_sentence_analyzer() -> SentenceAnalyzer:
    with _analyzer_lock:
        return _cached_analyzer()


@router.post("/analyze", response_model=SentenceAnalysisResponse)
def analyze_sentence(
    request: SentenceAnalysisRequest,
    session: Annotated[Session, Depends(get_session)],
    analyzer: Annotated[SentenceAnalyzer, Depends(get_sentence_analyzer)],
) -> SentenceAnalysisResponse:
    if not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Sentence must not be empty",
        )

    resolved = resolve_sentence(
        session,
        request.text,
        analyzer=analyzer,
    )
    groups = group_sentence(request.text, resolved)

    return SentenceAnalysisResponse(
        text=request.text,
        groups=[
            SentenceGroupResponse(
                surface=group.surface,
                start=group.start,
                end=group.end,
                candidate_source_ids=[
                    candidate.source_id for candidate in group.candidates
                ],
                tokens=[
                    SentenceTokenResponse(
                        surface=item.token.surface,
                        start=item.token.start,
                        end=item.token.end,
                        dictionary_form=item.token.dictionary_form,
                        normalized_form=item.token.normalized_form,
                        reading=item.token.reading,
                        part_of_speech=list(item.token.part_of_speech),
                        is_unknown=item.token.is_unknown,
                        candidate_source_ids=[
                            candidate.source_id for candidate in item.candidates
                        ],
                    )
                    for item in group.tokens
                ],
            )
            for group in groups
        ],
    )
