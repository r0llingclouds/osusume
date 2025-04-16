"""
AniList API Module

A collection of functions to interact with the AniList GraphQL API.
This module provides easy access to anime and manga data through simple function calls.
"""

import requests
import json


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


def get_media_by_id(media_id, media_type="ANIME"):
    """
    Get media (anime or manga) by ID
    
    Args:
        media_id (int): ID of the media
        media_type (str): Type of media ("ANIME" or "MANGA")
        
    Returns:
        dict: Media details
    """
    query = '''
    query ($id: Int, $type: MediaType) {
        Media (id: $id, type: $type) {
            id
            title {
                romaji
                english
                native
            }
            description
            genres
            averageScore
            episodes
            duration
            status
            seasonYear
            season
            format
            coverImage {
                large
            }
            studios {
                nodes {
                    name
                }
            }
        }
    }
    '''
    
    variables = {
        'id': media_id,
        'type': media_type
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Media']


def search_anime_old(search_term, limit=10):
    """
    Search for anime by name
    
    Args:
        search_term (str): The search term
        limit (int): Maximum number of results
        
    Returns:
        list: List of search results
    """
    query = '''
    query ($search: String, $perPage: Int) {
        Page(page: 1, perPage: $perPage) {
            media(search: $search, type: ANIME) {
                id
                title {
                    romaji
                    english
                }
                genres
                averageScore
                episodes
                format
                seasonYear
                coverImage {
                    medium
                }
            }
        }
    }
    '''
    
    variables = {
        "search": search_term,
        "perPage": limit
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


def search_manga(search_term, limit=10):
    """
    Search for manga by name
    
    Args:
        search_term (str): The search term
        limit (int): Maximum number of results
        
    Returns:
        list: List of search results
    """
    query = '''
    query ($search: String, $perPage: Int) {
        Page(page: 1, perPage: $perPage) {
            media(search: $search, type: MANGA) {
                id
                title {
                    romaji
                    english
                }
                genres
                averageScore
                chapters
                volumes
                format
                status
                coverImage {
                    medium
                }
            }
        }
    }
    '''
    
    variables = {
        "search": search_term,
        "perPage": limit
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


def get_popular_anime(page=1, per_page=10):
    """
    Get popular anime sorted by popularity
    
    Args:
        page (int): Page number
        per_page (int): Results per page
        
    Returns:
        list: List of popular anime
    """
    query = '''
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(type: ANIME, sort: POPULARITY_DESC) {
                id
                title {
                    romaji
                    english
                }
                popularity
                genres
                averageScore
                format
                seasonYear
            }
        }
    }
    '''
    
    variables = {
        "page": page,
        "perPage": per_page
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


def get_popular_manga(page=1, per_page=10):
    """
    Get popular manga sorted by popularity
    
    Args:
        page (int): Page number
        per_page (int): Results per page
        
    Returns:
        list: List of popular manga
    """
    query = '''
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(type: MANGA, sort: POPULARITY_DESC) {
                id
                title {
                    romaji
                    english
                }
                popularity
                genres
                averageScore
                format
                chapters
                volumes
                status
            }
        }
    }
    '''
    
    variables = {
        "page": page,
        "perPage": per_page
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


def get_seasonal_anime(year, season):
    """
    Get anime from a specific season
    
    Args:
        year (int): Year 
        season (str): Season ("WINTER", "SPRING", "SUMMER", "FALL")
        
    Returns:
        list: List of anime from that season
    """
    query = '''
    query ($season: MediaSeason, $seasonYear: Int) {
        Page(page: 1, perPage: 20) {
            media(type: ANIME, season: $season, seasonYear: $seasonYear, sort: POPULARITY_DESC) {
                id
                title {
                    romaji
                    english
                }
                genres
                averageScore
                episodes
                status
                coverImage {
                    medium
                }
            }
        }
    }
    '''
    
    variables = {
        "season": season,
        "seasonYear": year
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


def get_anime_by_genre(genre, page=1, per_page=20):
    """
    Get anime by genre
    
    Args:
        genre (str): Genre to search for
        page (int): Page number
        per_page (int): Results per page
        
    Returns:
        list: List of anime matching the genre
    """
    query = '''
    query ($genre: String, $page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(type: ANIME, genre: $genre, sort: POPULARITY_DESC) {
                id
                title {
                    romaji
                    english
                }
                genres
                averageScore
                episodes
                format
                seasonYear
            }
        }
    }
    '''
    
    variables = {
        "genre": genre,
        "page": page,
        "perPage": per_page
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


def get_manga_by_genre(genre, page=1, per_page=20):
    """
    Get manga by genre
    
    Args:
        genre (str): Genre to search for
        page (int): Page number
        per_page (int): Results per page
        
    Returns:
        list: List of manga matching the genre
    """
    query = '''
    query ($genre: String, $page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(type: MANGA, genre: $genre, sort: POPULARITY_DESC) {
                id
                title {
                    romaji
                    english
                }
                genres
                averageScore
                chapters
                volumes
                format
                status
            }
        }
    }
    '''
    
    variables = {
        "genre": genre,
        "page": page,
        "perPage": per_page
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']


def get_anime_recommendations(anime_id):
    """
    Get recommendations based on an anime
    
    Args:
        anime_id (int): ID of the anime
        
    Returns:
        tuple: (source_anime, list_of_recommendations)
    """
    query = '''
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            title {
                romaji
                english
            }
            recommendations(sort: RATING_DESC, perPage: 10) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            romaji
                            english
                        }
                        genres
                        averageScore
                        seasonYear
                    }
                }
            }
        }
    }
    '''
    
    variables = {
        "id": anime_id
    }
    
    response = fetch_from_anilist(query, variables)
    source_anime = response['data']['Media']
    recommendations = source_anime['recommendations']['nodes']
    return source_anime, [rec['mediaRecommendation'] for rec in recommendations]


def get_manga_recommendations(manga_id):
    """
    Get recommendations based on a manga
    
    Args:
        manga_id (int): ID of the manga
        
    Returns:
        tuple: (source_manga, list_of_recommendations)
    """
    query = '''
    query ($id: Int) {
        Media(id: $id, type: MANGA) {
            id
            title {
                romaji
                english
            }
            recommendations(sort: RATING_DESC, perPage: 10) {
                nodes {
                    mediaRecommendation {
                        id
                        title {
                            romaji
                            english
                        }
                        genres
                        averageScore
                        format
                    }
                }
            }
        }
    }
    '''
    
    variables = {
        "id": manga_id
    }
    
    response = fetch_from_anilist(query, variables)
    source_manga = response['data']['Media']
    recommendations = source_manga['recommendations']['nodes']
    return source_manga, [rec['mediaRecommendation'] for rec in recommendations]


def get_user_anime_list(username):
    """
    Get a user's anime list
    
    Args:
        username (str): Username on AniList
        
    Returns:
        list: User's anime list categories
    """
    query = '''
    query ($username: String) {
        MediaListCollection(userName: $username, type: ANIME) {
            lists {
                name
                entries {
                    media {
                        id
                        title {
                            romaji
                            english
                        }
                        coverImage {
                            medium
                        }
                    }
                    score
                    status
                }
            }
        }
    }
    '''
    
    variables = {
        "username": username
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['MediaListCollection']['lists']


def get_user_manga_list(username):
    """
    Get a user's manga list
    
    Args:
        username (str): Username on AniList
        
    Returns:
        list: User's manga list categories
    """
    query = '''
    query ($username: String) {
        MediaListCollection(userName: $username, type: MANGA) {
            lists {
                name
                entries {
                    media {
                        id
                        title {
                            romaji
                            english
                        }
                        coverImage {
                            medium
                        }
                    }
                    score
                    status
                }
            }
        }
    }
    '''
    
    variables = {
        "username": username
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['MediaListCollection']['lists']


def get_anime_characters_and_staff(anime_id):
    """
    Get detailed information about characters and staff for an anime
    
    Args:
        anime_id (int): ID of the anime
        
    Returns:
        dict: Anime details including characters and staff
    """
    query = '''
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            title {
                romaji
                english
            }
            characters(sort: ROLE, perPage: 10) {
                nodes {
                    name {
                        full
                    }
                    image {
                        medium
                    }
                    gender
                    description
                }
            }
            staff(perPage: 10) {
                nodes {
                    name {
                        full
                    }
                    primaryOccupations
                    image {
                        medium
                    }
                }
            }
        }
    }
    '''
    
    variables = {
        "id": anime_id
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Media']


def get_airing_schedule(anime_id):
    """
    Get the airing schedule for an anime
    
    Args:
        anime_id (int): ID of the anime
        
    Returns:
        list: List of airing episodes
    """
    query = '''
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            title {
                romaji
                english
            }
            status
            airingSchedule {
                nodes {
                    episode
                    airingAt
                    timeUntilAiring
                }
            }
        }
    }
    '''
    
    variables = {
        "id": anime_id
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Media']


def get_anime_stats(anime_id):
    """
    Get statistical information about an anime
    
    Args:
        anime_id (int): ID of the anime
        
    Returns:
        dict: Anime statistics
    """
    query = '''
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            title {
                romaji
                english
            }
            stats {
                scoreDistribution {
                    score
                    amount
                }
                statusDistribution {
                    status
                    amount
                }
            }
            rankings {
                rank
                type
                season
                allTime
            }
            trends {
                nodes {
                    date
                    trending
                    popularity
                }
            }
        }
    }
    '''
    
    variables = {
        "id": anime_id
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Media']


def get_anime_by_tags(tags, page=1, per_page=20):
    """
    Get anime by tags
    
    Args:
        tags (list): List of tags to search for
        page (int): Page number
        per_page (int): Results per page
        
    Returns:
        list: List of anime matching the tags
    """
    query = '''
    query ($tags: [String], $page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(type: ANIME, tag_in: $tags, sort: POPULARITY_DESC) {
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
                seasonYear
            }
        }
    }
    '''
    
    variables = {
        "tags": tags,
        "page": page,
        "perPage": per_page
    }
    
    response = fetch_from_anilist(query, variables)
    return response['data']['Page']['media']



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