from crewai import Agent, Task, Crew
from langchain.tools import BaseTool
from typing import Dict, Any, Optional, Type
import json
import re

class AnimeRequestTool(BaseTool):
    name: str = "map_request_to_json"  # Type annotation required
    description: str = "Maps a user anime request to AniList API parameters"  # Type annotation required
    return_direct: bool = True  # Type annotation required
    
    def _run(self, user_request: str) -> Dict[str, Any]:
        """
        Maps a user request to JSON parameters for the AniList API search_anime function.
        
        Args:
            user_request: The user's anime recommendation request
            
        Returns:
            Dict with parameters for the search_anime function
        """
        # Simple mapping logic
        params = {}
        
        # Check for search terms
        if any(term in user_request.lower() for term in ["like", "similar to", "such as"]):
            for term in ["like", "similar to", "such as"]:
                if term in user_request.lower():
                    parts = user_request.lower().split(term)
                    if len(parts) > 1:
                        search_term = parts[1].split(".")[0].split("!")[0].split("?")[0].strip()
                        params["search_term"] = search_term
                        break
        
        # Check for genres
        genres = []
        genre_list = ["action", "adventure", "comedy", "drama", "fantasy", "horror", 
                    "mystery", "romance", "sci-fi", "slice of life", "sports", "thriller"]
        
        for genre in genre_list:
            if genre in user_request.lower():
                genres.append(genre.title())
        
        if len(genres) == 1:
            params["genre"] = genres[0]
        elif len(genres) > 1:
            params["genres"] = genres
            
        # Check for season
        seasons = {"winter": "WINTER", "spring": "SPRING", "summer": "SUMMER", "fall": "FALL"}
        for season_name, season_value in seasons.items():
            if season_name in user_request.lower():
                params["season"] = season_value
                break
                
        # Check for year
        year_match = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', user_request)
        if year_match:
            params["year"] = int(year_match.group(0))
        
        # Check for tags
        tags = []
        tag_list = ["time travel", "school", "magic", "mecha", "psychological"]
        for tag in tag_list:
            if tag in user_request.lower():
                tags.append(tag.title())
        
        if tags:
            params["tags"] = tags
        
        # Default parameters
        params.setdefault("sort", "POPULARITY_DESC")
        params.setdefault("page", 1)
        params.setdefault("per_page", 10)
            
        return params
    
    async def _arun(self, user_request: str) -> Dict[str, Any]:
        """Async implementation of the tool"""
        return self._run(user_request)


class AnimeAgent:
    def __init__(self):
        # Create the tool instance
        anime_request_tool = AnimeRequestTool()
        
        # Create the agent with the tool
        self.agent = Agent(
            role="Anime Recommendation Agent",
            goal="Map user requests to AniList API parameters",
            backstory="You help users find anime by converting their requests to API parameters",
            verbose=True,
            tools=[anime_request_tool]
        )
        
        # Store tool for direct access
        self.mapping_tool = anime_request_tool
    
    def create_mapping_task(self, user_request: str) -> Task:
        return Task(
            description=f"Convert this request to AniList API parameters: '{user_request}'",
            expected_output="JSON object with parameters for the AniList API",
            agent=self.agent,
            context=[
                {"role": "system", "content": "Convert natural language anime requests into API parameters"},
                {"role": "user", "content": user_request}
            ]
        )
    
    def map_request_to_json(self, user_request: str) -> Dict[str, Any]:
        """Direct access to the mapping function"""
        return self.mapping_tool._run(user_request)


# Example usage
if __name__ == "__main__":
    # Create agent
    anime_agent = AnimeAgent()
    
    # Test with example request
    example_request = "I want to watch action anime like Attack on Titan"
    
    # Create a task
    task = anime_agent.create_mapping_task(example_request)
    
    # Create a crew with this task
    crew = Crew(
        agents=[anime_agent.agent],
        tasks=[task],
        verbose=True
    )
    
    # In a real implementation, you would run:
    # result = crew.kickoff()
    
    # For demonstration, directly call the mapping function
    result = anime_agent.map_request_to_json(example_request)
    print("API Parameters:")
    print(json.dumps(result, indent=2))