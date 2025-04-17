from typing import Optional, List, Literal
from pydantic import BaseModel
from crewai import Agent, Task, LLM
import os

# Initialize LLM (using GPT-4o from OpenAI)
llm = LLM(
    model="gpt-4.1",
    api_key=os.getenv('OPENAI_API_KEY'),
    max_tokens=2000,
    temperature=0
)

# 1 ── strict schema
class AnimeSearchParams(BaseModel):
    search_term: Optional[str] = None
    season:     Optional[Literal["WINTER", "SPRING", "SUMMER", "FALL"]] = None
    year:       Optional[int]  = None
    genres:     Optional[List[str]] = None
    tags:       Optional[List[str]] = None
    sort:       Optional[str] = None
    page:       Optional[int] = None
    per_page:   Optional[int] = None
    like_animes:   Optional[str] = None

    model_config = {"extra": "forbid"}

# 2 ── agent
mapper = Agent(
    name="AniListRequestMapper",
    role="Filter extractor",
    goal="Return only the filters in the user's request, as minimal JSON.",
    backstory="An anime librarian who knows the difference between genres and tags.",
    allow_delegation=False,
    llm=llm
)

# 3 ── task  – strict rules for genre vs tag + no nulls
OFFICIAL_GENRES = [
  "Action",
  "Adventure",
  "Comedy",
  "Drama",
  "Ecchi",
  "Fantasy",
  "Hentai",
  "Horror",
  "Mahou Shoujo",
  "Mecha",
  "Music",
  "Mystery",
  "Psychological",
  "Romance",
  "Sci-Fi",
  "Slice of Life",
  "Sports",
  "Supernatural",
  "Thriller"
]

map_request = Task(
    description=(
        "USER_REQUEST:\n"
        "{user_request}\n\n"
        "Produce **one JSON object** that validates against AnimeSearchParams.\n"
        "Rules:\n"
        f"• Only items in this list may appear in `genres`: {OFFICIAL_GENRES}.\n"
        "• Any other descriptive phrase (moods, sub‑genres like 'School Life', "
        "adjectives like 'Wholesome') must go into `tags`.\n"
        "• Title‑case every word (e.g. 'school‑life' → 'School Life').\n"
        "Don't necessarily include genres unless they are specified in the request.\n"
        "• Omit every key whose value would be null.\n\n"
        "Example:\n"
        "USER_REQUEST:  Recommend a dark fantasy from 2020.\n"
        "OUTPUT: {\"genres\": [\"Fantasy\"], \"tags\": [\"Dark\"], \"year\": 2020}"
    ),
    expected_output="A JSON dict with only the mentioned filters, no nulls.",
    output_json=AnimeSearchParams,
    agent=mapper,
)


# prompt = "I want an isekai anime with some comedy"
# crew = Crew(
#     agents=[mapper],
#     tasks=[map_request],
#     process=Process.sequential,
# )
# crew.kickoff(inputs={"user_request": prompt})

# params = {k: v for k, v in map_request.output.json_dict.items() if v is not None}
# print(params)