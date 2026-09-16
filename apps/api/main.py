from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from database import get_session
from schemas import SearchResponse
from search import find_words, normalize_query

app = FastAPI(title="SmartJisho")


@app.get("/api/v1/search")
def search(
    q: str,
    session: Annotated[Session, Depends(get_session)],
) -> SearchResponse:
    try:
        cleaned_query = normalize_query(q)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return SearchResponse(
        query=cleaned_query,
        results=find_words(session, cleaned_query),
    )
