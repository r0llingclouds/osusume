# File: /Users/tirsolopezausens/Documents/osusume/service.py

import os
import json
from typing import List
from pydantic import BaseModel, AnyHttpUrl
from crewai import Agent, Crew, Task, Process, LLM
from src.request_parser import AnimeSearchParams, OFFICIAL_GENRES
from src.recommender import SearchAnimeTool


class RecommendationItem(BaseModel):
    title: str
    description: str
    image_url: AnyHttpUrl


class service:
    anime_tool = SearchAnimeTool()
    llm = LLM(
        model="gpt-4.1",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=2000,
        temperature=0
    )

    # Step 1: extract filters from user request
    mapper = Agent(
        name="AniListRequestMapper",
        role="Filter extractor",
        goal="Return only the filters in the user's request as minimal JSON.",
        backstory="An anime librarian who knows the difference between genres and tags.",
        allow_delegation=False,
        llm=llm
    )
    map_request = Task(
        description=(
            "USER_REQUEST:\n"
            "{user_request}\n\n"
            "Produce **one JSON object** that validates against AnimeSearchParams.\n"
            "Rules:\n"
            f"• Only items in this list may appear in `genres`: {OFFICIAL_GENRES}.\n"
            "• Any other descriptive phrase (moods, sub-genres like 'School Life', adjectives like 'Wholesome') must go into `tags`.\n"
            "• Title-case every word (e.g. 'school-life' → 'School Life').\n"
            "• Omit every key whose value would be null."
        ),
        expected_output="A JSON dict with only the mentioned filters, no nulls.",
        output_json=AnimeSearchParams,
        agent=mapper
    )

    # Step 2: retrieve recommendations including cover image URL
    anime_researcher = Agent(
        role="Anime Researcher",
        goal="Find anime that match a user query, using search_anime tool and return JSON.",
        backstory="You are a seasoned anime critic.",
        tools=[anime_tool],
        llm=llm
    )
    recommendation_task = Task(
        description=(
            "Using the `search_anime` tool, find five anime matching the user's filters.\n"
            "For each result, extract three fields:\n"
            "  - `title`: English if available, else Romaji\n"
            "  - `description`: a one-sentence justification\n"
            "  - `image_url`: the `coverImage.medium` URL\n"
            "Return **only** a JSON array of objects, e.g. "
            "[{\"title\":\"X\",\"description\":\"Y\",\"image_url\":\"Z\"}, ...]"
        ),
        expected_output="A JSON array string matching list of recommendations",
        agent=anime_researcher,
        llm=llm
    )

    def build_crew(self) -> Crew:
        return Crew(
            agents=[self.mapper, self.anime_researcher],
            tasks=[self.map_request, self.recommendation_task],
            process=Process.sequential
        )

    def get_recommendations(self, user_request: str) -> List[RecommendationItem]:
        """
        Execute the Crew pipeline, parse its raw JSON output, and return typed items.
        """
        crew_output = self.build_crew().kickoff(
            inputs={"user_request": user_request}
        )  # CrewOutput

        # debug
        # print(crew_output)

        raw_json = getattr(crew_output, 'raw', None)
        if raw_json is None:
            raise RuntimeError("No raw output returned from Crew.")

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse recommendations JSON: {e}\nRaw: {raw_json}")

        if not isinstance(data, list):
            raise RuntimeError(f"Expected JSON array but got {type(data).__name__}: {data}")

        return [RecommendationItem.parse_obj(item) for item in data]


# Module-level helper
_service = service()

def get_recommendations(user_request: str) -> List[RecommendationItem]:
    return _service.get_recommendations(user_request)
