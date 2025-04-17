from crewai import Agent, Crew, Task, Process, LLM
from src.request_parser import AnimeSearchParams, OFFICIAL_GENRES
from src.recommender import SearchAnimeTool
import os



anime_tool = SearchAnimeTool()

llm = LLM(
    model="gpt-4.1",
    api_key=os.getenv('OPENAI_API_KEY'),
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

anime_researcher = Agent(
    role="Anime Researcher",
    goal="Find animes that match a user query.",
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

crew = Crew(
    agents=[mapper, anime_researcher],
    tasks=[map_request, recommendation_task],
    process=Process.sequential,
)

print("="*100)
print("Request: I want an isekai anime with some comedy")
result = crew.kickoff(inputs={"user_request": "I want an isekai anime with some comedy"})
print(result)
print("="*100)

print("="*100)
print("Request: I want an tennis anime")
result = crew.kickoff(inputs={"user_request": "I want an isekai anime with some comedy"})
print(result)
print("="*100)

print("="*100)
print("Request: I want an anime like ghost in the shell")
result = crew.kickoff(inputs={"user_request": "I want an anime like ghost in the shell"})
print(result)
print("="*100)

print("="*100)
print("Request: I want an anime like Akira")
result = crew.kickoff(inputs={"user_request": "I want an anime like Akira"})
print(result)
print("="*100)