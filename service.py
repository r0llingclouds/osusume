# File: /Users/tirsolopezausens/Documents/osusume/service.py

import os
import json
from typing import List
from pydantic import BaseModel, AnyHttpUrl, RootModel
from crewai import Agent, Crew, Task, Process, LLM
from src.request_parser import AnimeSearchParams, OFFICIAL_GENRES
from src.recommender import SearchAnimeTool


class RecommendationItem(BaseModel):
    title: str
    description: str
    image_url: AnyHttpUrl


class RecommendationsResponse(RootModel[List[RecommendationItem]]):
    """
    Pydantic root model wrapping a list of RecommendationItem.
    """
    pass


class service:
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
            "Rules:\n"
            f"• Only items in this list may appear in `genres`: {OFFICIAL_GENRES}.\n"
            "• Any other descriptive phrase must go into `tags`.\n"
            "• Title-case every word.\n"
            "• Omit keys with null values.\n\n"
            "Example:\n"
            "USER_REQUEST: Recommend a dark fantasy from 2020.\n"
            "OUTPUT: {\"genres\": [\"Fantasy\"], \"tags\": [\"Dark\"], \"year\": 2020}"
        ),
        expected_output="A JSON dict with only the mentioned filters, no nulls.",
        output_json=AnimeSearchParams,
        agent=mapper
    )

    anime_researcher = Agent(
        role="Anime Researcher",
        goal="Find anime that match a user query.",
        backstory="You are a seasoned anime critic.",
        tools=[anime_tool],
        llm=llm
    )

    recommendation_task = Task(
        description=(
            "Using the `search_anime` tool, find five anime matching the user’s filters. "
            "For each result, extract:\n"
            "  - `title`: English if available, else Romaji\n"
            "  - `description`: a one-sentence justification\n"
            "  - `image_url`: the `coverImage.medium` URL\n"
            "Return a bare JSON array of these objects."
        ),
        expected_output="A JSON array matching RecommendationsResponse schema.",
        output_json=RecommendationsResponse,
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
        Execute the Crew pipeline and parse its output into a list of RecommendationItem.
        """
        crew_output = self.build_crew().kickoff(
            inputs={"user_request": user_request}
        )  # CrewOutput

        # 1️⃣ Try Pydantic model
        if getattr(crew_output, 'pydantic', None) is not None:
            response_model: RecommendationsResponse = crew_output.pydantic
            return response_model.root

        # 2️⃣ Try JSON dict (handles wrapper formats)
        raw_json = getattr(crew_output, 'json_dict', None)
        if raw_json is not None:
            if isinstance(raw_json, dict):
                # extract list from single-key wrapper (e.g. {'root': [...]})
                values = list(raw_json.values())
                if len(values) == 1 and isinstance(values[0], list):
                    data_list = values[0]
                else:
                    raise RuntimeError(f"Unexpected JSON structure: {raw_json}")
            elif isinstance(raw_json, list):
                data_list = raw_json
            else:
                raise RuntimeError(f"Unexpected JSON structure: {raw_json}")
        else:
            # 3️⃣ Fallback to raw JSON string
            raw_output = getattr(crew_output, 'raw', None)
            if raw_output is None:
                raise RuntimeError("No output returned from Crew.")
            try:
                data_list = json.loads(raw_output)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse recommendations JSON: {e}\nRaw output: {raw_output}")

        # Validate and return RecommendationItem list
        return [RecommendationItem.parse_obj(elem) for elem in data_list]

# Module-level helper
_service = service()

def get_recommendations(user_request: str) -> List[RecommendationItem]:
    return _service.get_recommendations(user_request)
