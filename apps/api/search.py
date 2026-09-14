def normalize_query(query: str) -> str:
    normalized_query: str = query
    if not normalized_query:
        raise ValueError("Search query must not be empty")
    return normalized_query
