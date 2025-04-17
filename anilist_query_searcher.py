"""
AniList API Module

A collection of functions to interact with the AniList GraphQL API.
This module provides easy access to anime and manga data through simple function calls.
"""

import requests


def fetch_from_anilist(query, variables):
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


def search_anime(
    search_term=None,
    season=None,
    year=None,
    genre=None,
    genres=None,
    tags=None,
    sort="POPULARITY_DESC",
    page=1,
    per_page=20
):
    """
    A general function to search for anime with various filters.
    This function replaces and combines the functionality of:
    - search_anime()
    - get_seasonal_anime()
    - get_anime_by_genre()
    - get_anime_by_tags()
    
    Args:
        search_term (str, optional): Text to search in anime titles
        season (str, optional): Season ("WINTER", "SPRING", "SUMMER", "FALL")
        year (int, optional): Year for seasonal anime
        genre (str, optional): Single genre to filter by
        genres (list, optional): List of genres to filter by
        tags (list, optional): List of tags to filter by
        sort (str or list, optional): Sort order (default: "POPULARITY_DESC")
        page (int, optional): Page number (default: 1)
        per_page (int, optional): Results per page (default: 20)
        
    Returns:
        list: List of anime matching the criteria
    
    Examples:
        # Search anime by name (previous search_anime)
        results = search_anime(search_term="Attack on Titan", per_page=10)
        
        # Get seasonal anime (previous get_seasonal_anime)
        results = search_anime(year=2023, season="WINTER")
        
        # Get anime by genre (previous get_anime_by_genre)
        results = search_anime(genre="Action", page=1, per_page=20)
        
        # Get anime by tags (previous get_anime_by_tags)
        results = search_anime(tags=["Time Travel", "Post-Apocalyptic"], page=1, per_page=20)
        
        # Combine multiple filters
        results = search_anime(
            season="SUMMER",
            year=2022,
            genres=["Romance", "Comedy"],
            sort="SCORE_DESC"
        )
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
        variables["season"] = season
    if year:
        variables["seasonYear"] = year
    if genre:
        variables["genre"] = genre
    if genres:
        variables["genres"] = genres
    if tags:
        variables["tags"] = tags
    if sort:
        if isinstance(sort, list):
            variables["sort"] = sort
        else:
            variables["sort"] = [sort]
    
    variables["page"] = page
    variables["perPage"] = per_page
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


# search_results = search_anime(
#     tags=["Volleyball"],
#     per_page=5
# )
# print("All results:")
# for anime in search_results:
#     print(f"- {anime['title']['english'] or anime['title']['romaji']}")
#     print(f"  Genres: {', '.join(anime['genres'])}")
#     print(f"  Tags: {', '.join([tag['name'] for tag in anime['tags']])}")
#     print("-" * 60)