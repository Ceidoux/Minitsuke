from fastapi import FastAPI, HTTPException

from search import normalize_query

app = FastAPI(title="SmartJisho")


@app.get("/api/v1/search")
def search(q: str) -> dict[str, str]:
    try:
        cleaned_query = normalize_query(q)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {"query": cleaned_query}
