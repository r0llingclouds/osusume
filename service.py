"""
osusume.service
~~~~~~~~~~~~~~~
Public helpers that other front‑ends (Gradio, CLI, etc.) can import.

* build_crew()          → returns a memoised Crew instance
* get_recommendations() → runs one request through the crew
"""

from functools import lru_cache
import os
from crewai import Agent, Crew, Task, Process, LLM

# ──────────────────────────────── internal imports ───────────────────────────
from src.request_parser import AnimeSearchParams, OFFICIAL_GENRES
from src.recommender import SearchAnimeTool

# ────────────────────────────── crew construction ────────────────────────────
anime_tool = SearchAnimeTool()

llm = LLM(
    model="gpt-4.1",
    api_key=os.getenv("OPENAI_API_KEY"),
    max_tokens=2000,
    temperature=0
)

mapper = Agent(
    name="AniListRequestMapper",
    role="Filter extractor",
    goal="Return only the filters in the user's request, as minimal JSON.",
    backstory="An anime librarian who knows the difference between genres and tags.",
    allow_delegation=False,
    llm=llm
)

map_request = Task(
    description=(
        "USER_REQUEST:\n"
        "{user_request}\n\n"
        "Produce **one JSON object** that validates against AnimeSearchParams.\n"
        f"• Only items in this list may appear in `genres`: {OFFICIAL_GENRES}.\n"
        "• Any other descriptive phrase must go into `tags`.\n"
        "• Title‑case every word.\n"
        "• Omit every key whose value would be null."
    ),
    expected_output="A JSON dict with only the mentioned filters, no nulls.",
    output_json=AnimeSearchParams,
    agent=mapper,
)

anime_researcher = Agent(
    role="Anime Researcher",
    goal="Find anime that match a user query.",
    backstory="You are a seasoned anime critic.",
    tools=[anime_tool],
    llm=llm
)

recommendation_task = Task(
    description="Using AniList, compile a list of five anime that match the query.",
    expected_output="Five recommendations with one‑sentence justifications.",
    agent=anime_researcher,
    llm=llm
)

@lru_cache(maxsize=1)
def build_crew() -> Crew:
    """Return a singleton Crew instance (built once per Python process)."""
    return Crew(
        agents=[mapper, anime_researcher],
        tasks=[map_request, recommendation_task],
        process=Process.sequential,
    )

# ─────────────────────────────── public helper ───────────────────────────────
def get_recommendations(user_request: str) -> str:
    """
    Run the user's query through the crew and return the raw result string
    (Markdown‑formatted recommendations).
    """
    crew = build_crew()
    result = crew.kickoff(inputs={"user_request": user_request})

    # CrewAI ≤0.30 returns a CrewOutput object; turn it into Markdown text
    try:
        # Newer versions expose .output (string) or .content
        return result.output  # type: ignore[attr-defined]
    except AttributeError:
        # Fallback: rely on __str__() – good enough for Gradio
        return str(result)