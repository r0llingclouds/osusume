# get parent directory
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# add parent directory to sys.path
import sys
sys.path.append(parent_dir)
from typing import Optional, List, Literal
from pydantic import BaseModel

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



# prompt = "I want an isekai anime with some comedy"
# crew = Crew(
#     agents=[mapper],
#     tasks=[map_request],
#     process=Process.sequential,
# )
# crew.kickoff(inputs={"user_request": prompt})

# params = {k: v for k, v in map_request.output.json_dict.items() if v is not None}
# print(params)