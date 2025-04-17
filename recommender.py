"""
AniList Search Tool for CrewAI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A robust, CrewAI‑compatible tool for querying the AniList public API.

Features
--------
* Search by keyword, season, year, genres, tags, and sort order.
* Optional "like_animes" boost: infer genres/tags from a seed list of
  anime titles to build a taste profile.
* Strict Pydantic **v2** schema for LLM‑friendly argument validation.
* Graceful HTTP error handling and sensible time‑outs.
* Zero side‑effect logging (debug statements removed).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type, TypedDict

import requests
from pydantic import BaseModel, Field, field_validator
from crewai.tools import BaseTool
from anilist_query_searcher import search_anime
from analyzer import get_relevant_tags_and_genres
# --------------------------------------------------------------------------- #
#  Configuration & logging
# --------------------------------------------------------------------------- #

_ANILIST_API_URL: str = "https://graphql.anilist.co"
_REQUEST_TIMEOUT_S: int = 10

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Typed response helpers
# --------------------------------------------------------------------------- #

class Tag(TypedDict):
    id: int
    name: str
    rank: int
    isMediaSpoiler: bool

class Anime(TypedDict):
    id: int
    title: Dict[str, Optional[str]]
    genres: List[str]
    tags: List[Tag]
    averageScore: Optional[int]
    episodes: Optional[int]
    format: Optional[str]
    status: Optional[str]
    seasonYear: Optional[int]
    coverImage: Dict[str, str]

# --------------------------------------------------------------------------- #
#  Low‑level helper
# --------------------------------------------------------------------------- #

def _fetch_from_anilist(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Send a GraphQL request to the AniList public API and return the JSON body."""
    try:
        resp = requests.post(
            _ANILIST_API_URL,
            json={"query": query, "variables": variables},
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Network error talking to AniList: {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(
            f"AniList query failed (HTTP {resp.status_code}): {resp.text}"
        )

    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"AniList returned errors: {payload['errors']!r}")

    return payload

# --------------------------------------------------------------------------- #
#  Pydantic v2 input schema
# --------------------------------------------------------------------------- #

class SearchAnimeToolInput(BaseModel):
    """Arguments accepted by the :class:`SearchAnimeTool`."""

    search_term: Optional[str] = Field(
        None, description="Keyword to search in titles (Romaji or English).",
    )
    season: Optional[str] = Field(
        None,
        pattern=r"^(WINTER|SPRING|SUMMER|FALL)$",
        description='Season filter: "WINTER", "SPRING", "SUMMER", or "FALL".',
    )
    year: Optional[int] = Field(
        None,
        ge=1960,
        le=2100,
        description="Season year, e.g. 2024.",
    )
    genre: Optional[str] = Field(None, description="A single genre to filter by.")
    genres: Optional[List[str]] = Field(None, description="Multiple genres to filter by.")
    tags: Optional[List[str]] = Field(None, description="AniList tags to filter by.")
    sort: Optional[List[str]] = Field(
        default_factory=lambda: ["POPULARITY_DESC"],
        description='AniList sort keys, default `["POPULARITY_DESC"]`.',
    )
    page: int = Field(1, ge=1, description="1‑based page number.")
    per_page: int = Field(20, ge=1, le=50, description="Page size (max 50).")
    like_animes: Optional[str] = Field(
        None,
        description="Comma‑separated seed anime titles to build a taste profile.",
    )

    # Normalise blank strings to None so CrewAI can do `is not None`
    @field_validator("search_term", "season", "genre", "like_animes", mode="before")
    def _blank_to_none(cls, v):  # noqa: N805
        if isinstance(v, str) and not v.strip():
            return None
        return v

# --------------------------------------------------------------------------- #
#  CrewAI tool definition
# --------------------------------------------------------------------------- #

class SearchAnimeTool(BaseTool):
    """CrewAI tool **search_anime** – query AniList and return JSON anime list."""

    name: str = "search_anime"
    description: str = (
        "Search AniList for anime using free‑text title keywords, season/year, "
        "genres, tags, and sort order. Returns a JSON array of matching anime."
    )
    args_schema: Type[BaseModel] = SearchAnimeToolInput

    def _run(self, **kwargs) -> List[Anime]:  # noqa: N802
        params = SearchAnimeToolInput(**kwargs)

        variables: Dict[str, Any] = {
            "page": params.page,
            "perPage": params.per_page,
            "sort": params.sort,
        }

        if params.search_term:
            variables["search"] = params.search_term
        if params.season:
            variables["season"] = params.season
        if params.year:
            variables["seasonYear"] = params.year
        if params.genre:
            variables["genre"] = params.genre
        if params.genres:
            variables["genres"] = params.genres
        if params.tags:
            variables["tags"] = params.tags

        # Taste profile expansion
        if params.like_animes:
            taste_genres, taste_tags = self._build_taste_profile(params.like_animes)
            if taste_genres:
                variables["genres"] = sorted(
                    set(variables.get("genres", [])) | taste_genres
                )
            if taste_tags:
                variables["tags"] = sorted(
                    set(variables.get("tags", [])) | taste_tags
                )

        data = _fetch_from_anilist(_GRAPHQL_QUERY, variables)
        return data["data"]["Page"]["media"]

    async def _arun(self, **kwargs) -> Any:  # noqa: D401
        return self._run(**kwargs)

    # --------------------------------------------------------------------- #
    #  Private helpers
    # --------------------------------------------------------------------- #

    def _build_taste_profile(self, like_animes: str) -> tuple[set[str], set[str]]:
        """Aggregate genres & tags from a comma‑separated list of anime titles."""

        genres_acc: set[str] = set()
        tags_acc: set[str] = set()

        for raw in like_animes.split(","):
            title = raw.strip()
            if not title:
                continue
            hits = search_anime(title)
            if not hits:
                continue
            first = hits[0]
            g, t = get_relevant_tags_and_genres(
                first["title"].get("english") or first["title"].get("romaji"),
                first["genres"],
                [tag["name"] for tag in first["tags"]],
            )
            genres_acc.update(g)
            tags_acc.update(t)

        return genres_acc, tags_acc

# --------------------------------------------------------------------------- #
#  Static GraphQL query
# --------------------------------------------------------------------------- #

_GRAPHQL_QUERY: str = """
query (
  $search: String, $season: MediaSeason, $seasonYear: Int,
  $genre: String, $genres: [String], $tags: [String],
  $page: Int, $perPage: Int, $sort: [MediaSort]
) {
  Page(page: $page, perPage: $perPage) {
    media(
      search: $search, type: ANIME, season: $season,
      seasonYear: $seasonYear, genre: $genre, genre_in: $genres,
      tag_in: $tags, sort: $sort
    ) {
      id
      title { romaji english }
      genres
      tags { id name rank isMediaSpoiler }
      averageScore
      episodes
      format
      status
      seasonYear
      coverImage { medium }
    }
  }
}
""".strip()
