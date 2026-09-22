from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from sqlalchemy.orm import Session

from database import get_session
from jmdict_entry_service import load_entry_by_source_id
from jmdict_search import search_jmdict
from schemas import JmdictEntryResponse, JmdictSearchResponse
from search import normalize_query

app = FastAPI(title="Minitsuke")


@app.get("/api/v1/search")
def search(
    q: str,
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
    languages: Annotated[list[str] | None, Query()] = None,
) -> JmdictSearchResponse:
    try:
        cleaned_query = normalize_query(q)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    enabled_languages = (
        ("eng",) if languages is None else tuple(dict.fromkeys(languages))
    )

    return search_jmdict(
        session,
        cleaned_query,
        languages=enabled_languages,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/entries/{source_id}")
def get_entry(
    source_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    session: Annotated[Session, Depends(get_session)],
    languages: Annotated[list[str] | None, Query()] = None,
) -> JmdictEntryResponse:
    enabled_languages = (
        ("eng",) if languages is None else tuple(dict.fromkeys(languages))
    )

    entry = load_entry_by_source_id(
        session,
        source_id,
        languages=enabled_languages,
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Dictionary entry not found",
        )

    return entry
