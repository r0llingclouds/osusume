import os
import requests
import json
from typing import Type, Dict, Any
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool

# --- AniList API Tool Input Schema ---
class AniListToolInput(BaseModel):
    """Input schema for the AniListAPITool."""
    query: str = Field(..., description="The GraphQL query string.")
    variables: Dict[str, Any] = Field(..., description="The dictionary of variables for the GraphQL query.")

# --- AniList API Tool ---

class AniListAPITool(BaseTool):
    name: str = "AniList API Tool"
    description: str = (
        "Executes a GraphQL query against the AniList API (https://graphql.anilist.co). "
        "Input must be a dictionary containing 'query' (string) and 'variables' (dict)."
    )
    api_url: str = 'https://graphql.anilist.co'
    args_schema: Type[BaseModel] = AniListToolInput # Use the updated schema

    def _run(self, query: str, variables: Dict[str, Any]) -> str:
        """
        Executes the AniList GraphQL query.
        Receives query and variables directly via the args_schema.
        """
        try:
            if not query or not isinstance(variables, dict):
                # This check might be redundant due to pydantic validation, but kept for safety
                return "Error: Tool requires a 'query' string and a 'variables' dictionary."

            # Make the HTTP API request
            response = requests.post(self.api_url, json={'query': query, 'variables': variables})
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return json.dumps(response.json(), indent=2)

        except requests.exceptions.RequestException as e:
            return f"Error connecting to AniList API: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

# Instantiate the tool
anilist_tool = AniListAPITool()

# --- Agents ---

preference_analyzer = Agent(
    role='Preference Analysis Agent',
    goal='Analyze the user\'s request to understand their anime preferences (genres, liked anime).',
    backstory=(
        "You are an expert in understanding natural language related to anime tastes. "
        "Your goal is to extract key information like preferred genres or specific anime titles mentioned by the user. "
        "Output a dictionary containing 'genres' (list of strings) and 'liked_anime' (string or null)."
    ),
    verbose=True,
    allow_delegation=False
)

anilist_query_agent = Agent(
    role='AniList Query Agent',
    goal='Formulate and execute AniList API queries based on user preferences to find suitable anime recommendations.',
    backstory=(
        "You are a specialist in interacting with the AniList GraphQL API. "
        "You receive structured preferences (genres, liked anime) and use them to search for relevant anime. "
        "First, if a liked anime is provided, query its details to find its genres. "
        "Then, query for popular anime matching the identified genres (either from the liked anime or directly from the user's request). "
        "Return the raw list of anime candidates found."
    ),
    tools=[anilist_tool],
    verbose=True,
    allow_delegation=False
)

recommendation_formatter = Agent(
    role='Recommendation Formatting Agent',
    goal='Format the list of anime candidates into a user-friendly recommendation list.',
    backstory=(
        "You receive a list of anime data from the AniList Query Agent. "
        "Your job is to present these recommendations clearly to the user, listing the titles and perhaps their genres. "
        "Filter out redundant information and make the output easy to read."
    ),
    verbose=True,
    allow_delegation=False
)

# --- Tasks ---

# Task 1: Analyze User Request
analyze_request_task = Task(
    description=(
        "Analyze the user's input: '{user_prompt}'. "
        "Identify preferred genres and any specific anime titles mentioned. "
        "Output a dictionary summarizing these preferences, for example: "
        "{{'genres': ['action', 'adventure'], 'liked_anime': 'Demon Slayer'}} or "
        "{{'genres': ['sci-fi'], 'liked_anime': null}}. "
        "If no specific preferences are found, indicate that, perhaps suggesting general popular anime."
    ),
    expected_output=(
        "A dictionary containing two keys: 'genres' (a list of strings) and 'liked_anime' (a string or null)."
    ),
    agent=preference_analyzer
)

# Task 2: Find Anime Candidates
find_candidates_task = Task(
    description=(
        "Based on the analyzed preferences from the previous task (containing 'genres' list and 'liked_anime'), formulate and execute queries using the AniList API Tool. "
        "1. Determine the target genres: If 'liked_anime' is present, prioritize querying its genres first. Otherwise, use the 'genres' list directly from the context. "
        "2. Formulate the GraphQL query: "
        "   - Define necessary variables (e.g., $page: Int, $perPage: Int, $genres: [String], $genre: String). Set default values like page=1, perPage=5. "
        "   - Use the Page(page: $page, perPage: $perPage) field structure. "
        "   - Filter media: Use 'media(type: ANIME, sort: POPULARITY_DESC, ...)' "
        "   - Apply genre filters: If multiple genres, add 'genre_in: $genres'. If single genre, add 'genre: $genre'. "
        "   - Request fields: id, title { romaji english }, genres, popularity. "
        "3. Execute the query using the AniList API Tool with the correct query string and variables dictionary. "
        "4. Fallback Logic: If the query with specific genre(s) returns no results (or causes an error initially), try again by querying for general popular anime (sort: POPULARITY_DESC, no genre filter) as a last resort, still using the Page(page: $page, perPage: $perPage) structure. "
        "IMPORTANT: When using the AniList API Tool, the 'Action Input' MUST be a dictionary with two keys: 'query' (string) and 'variables' (dictionary). \n"
        "Example (multi-genre): {{" 
        "  'query': 'query ($page: Int, $perPage: Int, $genres: [String]) {{ Page(page: $page, perPage: $perPage) {{ media(type: ANIME, genre_in: $genres, sort: POPULARITY_DESC) {{ id title {{ romaji english }} genres popularity }} }} }}', "
        "  'variables': {{ 'page': 1, 'perPage': 5, 'genres': ['Ecchi', 'Slice of Life'] }} "
        "}}. \n"
        "Example (single-genre): {{" 
        "  'query': 'query ($page: Int, $perPage: Int, $genre: String) {{ Page(page: $page, perPage: $perPage) {{ media(type: ANIME, genre: $genre, sort: POPULARITY_DESC) {{ id title {{ romaji english }} genres popularity }} }} }}', "
        "  'variables': {{ 'page': 1, 'perPage': 5, 'genre': 'Sci-Fi' }} "
        "}}. \n"
        "Example (fallback): {{" 
        "  'query': 'query ($page: Int, $perPage: Int) {{ Page(page: $page, perPage: $perPage) {{ media(type: ANIME, sort: POPULARITY_DESC) {{ id title {{ romaji english }} genres popularity }} }} }}', "
        "  'variables': {{ 'page': 1, 'perPage': 5 }} "
        "}}."
    ),
    expected_output=(
        "A JSON string containing the raw list of anime candidates found from the AniList API, including titles, genres, and popularity. This might be an empty list if no matches were found initially or due to errors."
    ),
    agent=anilist_query_agent,
    context=[analyze_request_task] # Depends on the output of the analysis task
)

# Task 3: Format Recommendations
format_recommendations_task = Task(
    description=(
        "Take the raw JSON list of anime candidates found by the AniList Query Agent. "
        "Process this list and format it into a clean, readable recommendation message for the user. "
        "List the recommended anime titles clearly, perhaps numbered. Include their genres. "
        "Example: 'Based on your preferences, here are some anime recommendations:\n1. Title One (Genres: Action, Sci-Fi)\n2. Title Two (Genres: Adventure, Fantasy)'"
    ),
    expected_output=(
        "A user-friendly string containing the formatted list of anime recommendations with titles and genres."
    ),
    agent=recommendation_formatter,
    context=[find_candidates_task] # Depends on the output of the candidate finding task
)


# --- Crew ---

anime_crew = Crew(
    agents=[preference_analyzer, anilist_query_agent, recommendation_formatter],
    tasks=[analyze_request_task, find_candidates_task, format_recommendations_task],
    process=Process.sequential, # Tasks will run in order
    verbose=False # Shows agent reasoning and actions
)

# --- Execution ---

if __name__ == "__main__":
    print("Welcome to the Anime Recommender Crew!")
    print("---------------------------------------")
    # Example usage:
    # user_input = "I really liked Attack on Titan, suggest something similar."
    user_input = input("Enter your anime recommendation request: ")
    # user_input = "Any good comedy anime?"
    # user_input = "Suggest some anime for me." # General request

    inputs = {'user_prompt': user_input}
    result = anime_crew.kickoff(inputs=inputs)

    print("--- Final Recommendation ---")
    print(result) 