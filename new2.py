import os
import requests
import json
from typing import Type, Dict, Any
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool


llm = LLM(
    model="gpt-4o",
) 
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
    allow_delegation=False,
    llm=llm
)

anilist_query_agent = Agent(
    role='AniList Query Agent',
    goal='Formulate and execute AniList API queries based on user preferences to find suitable anime recommendations.',
    backstory=(
        "You are a specialist in interacting with the AniList GraphQL API. "
        "Your most important rule: NEVER give up after a single failed query! "
        "When your initial search returns no results, you must try variations: "
        "1. Switch between genre/tag searches (especially for concepts like 'isekai')"
        "2. Try related terms or combinations of standard categories"
        "3. Document all your attempts before considering a general fallback"
        "Your reputation depends on finding relevant results for the original request!"
    ),
    tools=[anilist_tool],
    verbose=True,
    allow_delegation=False,
    llm=llm
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
    allow_delegation=False,
    llm=llm
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
        "\n\nFALLBACK RULES - VERY IMPORTANT:"
        "\n1. If your query returns no results, DO NOT immediately resort to a general query with no filters."
        "\n2. Instead, ALWAYS TRY VARIATIONS of your search terms first:"
        "\n   - For genres that return no results (like 'isekai'), try searching as a TAG instead"
        "\n   - Try related terms (e.g., if 'isekai' fails, try 'transported to another world' as a tag)"
        "\n   - Try combining standard genres that typically represent the concept (e.g., 'Fantasy' + 'Adventure')"
        "\n3. ONLY as an absolute last resort, when all variations have been tried, use a general query"
        "\n4. DOCUMENT YOUR ATTEMPTS in your thought process so we can see what variations you tried"
        "\n\n"
        "Example (genre query): {"
        "  'query': 'query ($page: Int, $perPage: Int, $genre: String) { Page(page: $page, perPage: $perPage) { media(type: ANIME, genre: $genre, sort: POPULARITY_DESC) { id title { romaji english } genres popularity } } }', "
        "  'variables': { 'page': 1, 'perPage': 5, 'genre': 'Fantasy' } "
        "}. \n"
        "Example (tag query - USE THIS FOR TERMS LIKE 'ISEKAI'): {"
        "  'query': 'query ($page: Int, $perPage: Int, $tag: String) { Page(page: $page, perPage: $perPage) { media(type: ANIME, tag: $tag, sort: POPULARITY_DESC) { id title { romaji english } genres tags { name } popularity } } }', "
        "  'variables': { 'page': 1, 'perPage': 5, 'tag': 'Isekai' } "
        "}. \n"
        "Example (multi-genre query - USE THIS AS FALLBACK): {"
        "  'query': 'query ($page: Int, $perPage: Int, $genres: [String]) { Page(page: $page, perPage: $perPage) { media(type: ANIME, genre_in: $genres, sort: POPULARITY_DESC) { id title { romaji english } genres popularity } } }', "
        "  'variables': { 'page': 1, 'perPage': 5, 'genres': ['Fantasy', 'Adventure'] } "
        "}. \n"
        "The query is {user_prompt}"
    ),
    expected_output=(
        "A JSON string containing anime results that match the user's request - or the closest variation you could find. "
        "You MUST show your attempts to find variations before falling back to general results."
    ),
    agent=anilist_query_agent,
    context=[analyze_request_task]
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
    # agents=[preference_analyzer],
    # tasks=[analyze_request_task],
    agents=[anilist_query_agent],
    tasks=[find_candidates_task],

    # agents=[preference_analyzer, anilist_query_agent],
    # tasks=[analyze_request_task, find_candidates_task],
    verbose=False # Shows agent reasoning and actions
)

# --- Testing Function ---

def test_isekai_query():
    """
    Test function to verify the improved fallback behavior for isekai queries.
    This can be added to your main script for testing.
    """
    print("Testing isekai query with improved fallback logic...")
    
    # Direct query to the AniList API using tag instead of genre
    isekai_test_query = {
        "query": """
        query ($page: Int, $perPage: Int, $tag: String) {
            Page(page: $page, perPage: $perPage) {
                media(type: ANIME, tag: $tag, sort: POPULARITY_DESC) {
                    id
                    title {
                        romaji
                        english
                    }
                    genres
                    tags {
                        name
                    }
                    popularity
                }
            }
        }
        """,
        "variables": {
            "page": 1,
            "perPage": 5,
            "tag": "Isekai"  # Using tag instead of genre
        }
    }
    
    # Test using your AniList tool
    result = anilist_tool._run(isekai_test_query["query"], isekai_test_query["variables"])
    print("Test result:")
    print(result)
    
    # Check if we got results
    import json
    response = json.loads(result)
    if response.get("data", {}).get("Page", {}).get("media", []):
        print("SUCCESS: Found isekai anime by using tag search!")
        return True
    else:
        print("FAILED: Still no results. Additional fallback needed.")
        
        # Try a fallback to Fantasy + Adventure genres
        fallback_query = {
            "query": """
            query ($page: Int, $perPage: Int, $genres: [String]) {
                Page(page: $page, perPage: $perPage) {
                    media(type: ANIME, genre_in: $genres, sort: POPULARITY_DESC) {
                        id
                        title {
                            romaji
                            english
                        }
                        genres
                        popularity
                    }
                }
            }
            """,
            "variables": {
                "page": 1,
                "perPage": 5,
                "genres": ["Fantasy", "Adventure"]
            }
        }
        
        result = anilist_tool._run(fallback_query["query"], fallback_query["variables"])
        print("Fallback result:")
        print(result)
        return False

# --- Execution ---

if __name__ == "__main__":
    # Run the test function to verify the tag search works
    # Uncomment the line below to test before running the main program
    # test_isekai_query()
    
    print("Welcome to the Anime Recommender Crew!")
    print("---------------------------------------")
    user_input = input("Enter your anime recommendation request: ")
    inputs = {'user_prompt': user_input}
    result = anime_crew.kickoff(inputs=inputs)
    
    print("--- Final Recommendation ---")
    print(result)