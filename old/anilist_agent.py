import os
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import requests

# Define the valid sort values that AniList API accepts
VALID_SORT_VALUES = [
    "POPULARITY_DESC", "POPULARITY",
    "SCORE_DESC", "SCORE",
    "TRENDING_DESC", "TRENDING",
    "UPDATED_AT_DESC", "UPDATED_AT",
    "START_DATE_DESC", "START_DATE",
    "END_DATE_DESC", "END_DATE",
    "FAVORITES_DESC", "FAVORITES",
    "ID_DESC", "ID",
    "TITLE_ROMAJI_DESC", "TITLE_ROMAJI", 
    "TITLE_ENGLISH_DESC", "TITLE_ENGLISH",
    "TITLE_NATIVE_DESC", "TITLE_NATIVE",
    "EPISODES_DESC", "EPISODES"
]

# Define the schema for the tool inputs
class AnimeSearchToolSchema(BaseModel):
    search_term: Optional[str] = Field(default=None, description="Text to search in anime titles")
    season: Optional[str] = Field(default=None, description="Season (WINTER, SPRING, SUMMER, FALL)")
    year: Optional[int] = Field(default=None, description="Year for seasonal anime")
    genre: Optional[str] = Field(default=None, description="Single genre to filter by")
    genres: Optional[List[str]] = Field(default=None, description="List of genres to filter by")
    tags: Optional[List[str]] = Field(default=None, description="List of tags to filter by")
    sort: Optional[Union[str, List[str]]] = Field(
        default="POPULARITY_DESC", 
        description=f"Sort order. Valid values: {', '.join(VALID_SORT_VALUES)}"
    )
    page: int = Field(default=1, description="Page number")
    per_page: int = Field(default=20, description="Results per page")

# Domain model - The core entities and functionality
class AnimeSearchTool(BaseTool):
    """Tool for searching anime using the AniList GraphQL API."""
    
    name: str = "Anime Search Tool"
    description: str = "Search for anime with various filters including name, season, year, genres, and tags."
    args_schema: type[BaseModel] = AnimeSearchToolSchema
    
    def fetch_from_anilist(self, query, variables):
        """
        Make a request to the AniList GraphQL API
        
        Args:
            query (str): GraphQL query
            variables (dict): Variables for the query
            
        Returns:
            dict: JSON response from the API
        """
        url = 'https://graphql.anilist.co'
        
        # Make the HTTP request
        response = requests.post(url, json={'query': query, 'variables': variables})
        
        # Check for errors
        if response.status_code != 200:
            raise Exception(f"Query failed with status code {response.status_code}. Response: {response.text}")
        
        # Return the JSON response
        return response.json()
    
    def _normalize_sort(self, sort_value):
        """
        Maps common user sort terms to valid AniList sort values.
        
        Args:
            sort_value: The user-provided sort value
            
        Returns:
            str: A valid AniList sort value
        """
        if not sort_value:
            return "POPULARITY_DESC"
            
        # Convert to string if it's not already
        if not isinstance(sort_value, str):
            return sort_value
            
        # Map of common terms to valid sort values
        sort_mapping = {
            "popularity": "POPULARITY_DESC",
            "popular": "POPULARITY_DESC",
            "rating": "SCORE_DESC",
            "score": "SCORE_DESC",
            "highly rated": "SCORE_DESC",
            "high rating": "SCORE_DESC",
            "trending": "TRENDING_DESC",
            "newest": "START_DATE_DESC",
            "latest": "START_DATE_DESC",
            "recent": "UPDATED_AT_DESC",
            "updated": "UPDATED_AT_DESC",
            "favorites": "FAVORITES_DESC",
        }
        
        # Check for exact match in valid values (case-insensitive)
        for valid_value in VALID_SORT_VALUES:
            if sort_value.upper() == valid_value:
                return valid_value
                
        # Check for match in our mapping
        lower_sort = sort_value.lower()
        if lower_sort in sort_mapping:
            return sort_mapping[lower_sort]
            
        # Default to popularity if no match found
        return "POPULARITY_DESC"
    
    def _run(self, search_term=None, season=None, year=None, genre=None, 
             genres=None, tags=None, sort="POPULARITY_DESC", page=1, per_page=20):
        """
        Execute the anime search with the provided parameters.
        """
        query = '''
        query ($search: String, $season: MediaSeason, $seasonYear: Int, $genre: String, $genres: [String], $tags: [String], $page: Int, $perPage: Int, $sort: [MediaSort]) {
            Page(page: $page, perPage: $perPage) {
                media(
                    search: $search, 
                    type: ANIME,
                    season: $season,
                    seasonYear: $seasonYear,
                    genre: $genre,
                    genre_in: $genres,
                    tag_in: $tags,
                    sort: $sort
                ) {
                    id
                    title {
                        romaji
                        english
                    }
                    genres
                    tags {
                        id
                        name
                        rank
                        isMediaSpoiler
                    }
                    description
                    averageScore
                    episodes
                    format
                    status
                    seasonYear
                    coverImage {
                        medium
                    }
                }
            }
        }
        '''
        
        # Build variables dict, only including non-None values
        variables = {}
        if search_term:
            variables["search"] = search_term
        if season:
            # Ensure season is in uppercase
            if isinstance(season, str):
                variables["season"] = season.upper()
        if year:
            variables["seasonYear"] = year
        if genre:
            variables["genre"] = genre
        if genres:
            variables["genres"] = genres
        if tags:
            variables["tags"] = tags
            
        # Normalize sort parameter
        if sort:
            if isinstance(sort, list):
                variables["sort"] = [self._normalize_sort(s) for s in sort]
            else:
                variables["sort"] = [self._normalize_sort(sort)]
        
        variables["page"] = page
        variables["perPage"] = per_page
        
        response = self.fetch_from_anilist(query, variables)
        return response['data']['Page']['media']

# Define the Agent
def create_anime_agent():
    """Create and return the Anime Search Agent."""
    
    # Create the tool instance
    anime_search_tool = AnimeSearchTool()
    
    # Create the agent with the search tool
    anime_agent = Agent(
        role="Anime Search Specialist",
        goal="Help users find anime that match their preferences and interests",
        backstory="""You are an expert in anime with extensive knowledge of different genres, 
        seasons, and popular titles. Your purpose is to help users discover anime 
        that they will enjoy based on their search criteria.""",
        verbose=True,
        tools=[anime_search_tool],
        allow_delegation=False
    )
    
    return anime_agent

# Define the Task
def create_anime_search_task(agent, user_request):
    """Create a task for the agent based on the user's request."""
    
    task = Task(
        description=f"""
        Analyze the following user request and search for anime that match their criteria:
        
        "{user_request}"
        
        1. Extract search parameters (search term, season, year, genre, etc.) from the user request
        2. Use the Anime Search Tool to find matching anime
        3. Format the results in a clear, readable manner
        4. If the results don't seem relevant, try different search parameters
        5. Provide brief descriptions of each recommended anime
        
        Valid sort values: {', '.join(VALID_SORT_VALUES)}
        If user asks for "rating" or "score", use "SCORE_DESC".
        For seasonal searches, make sure season is one of: WINTER, SPRING, SUMMER, FALL (uppercase).
        """,
        agent=agent,
        expected_output="""A list of recommended anime with titles, descriptions, 
        genres, and scores that match the user's request."""
    )
    
    return task

# Main function to handle user requests
def get_anime_recommendations(user_request):
    """Process a user request and return anime recommendations."""
    
    # Create the agent
    anime_agent = create_anime_agent()
    
    # Create the task based on the user request
    anime_task = create_anime_search_task(anime_agent, user_request)
    
    # Create a crew with just our anime agent
    anime_crew = Crew(
        agents=[anime_agent],
        tasks=[anime_task],
        verbose=True  # Use boolean as required
    )
    
    # Execute the task and get results
    result = anime_crew.kickoff()
    
    return result

# Example usage
if __name__ == "__main__":
    # Example user request
    user_request = "I'm looking for isekai anime also ecchi"
    
    # Get recommendations
    recommendations = get_anime_recommendations(user_request)
    
    # Print the results
    print("\nAnime Recommendations:")
    print(recommendations)