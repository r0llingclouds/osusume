import requests
from openai import OpenAI
import os
import logging
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('anime_recommender')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ANILIST_API_URL = 'https://graphql.anilist.co'

# STEP 1: Get anime details by title
def get_anime_details(title):
    logger.info(f"Searching for anime details with title: '{title}'")
    
    query = '''
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        id
        title { romaji english }
        genres
        tags { name }
        averageScore
        popularity
      }
    }
    '''
    variables = {'search': title}
    
    try:
        logger.debug(f"Sending request to AniList API: {json.dumps(variables)}")
        start_time = time.time()
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables})
        elapsed_time = time.time() - start_time
        
        if response.status_code != 200:
            logger.error(f"AniList API request failed: Status {response.status_code}, Response: {response.text}")
            return None
            
        data = response.json()
        
        if 'errors' in data:
            logger.error(f"AniList API returned errors: {data['errors']}")
            return None
            
        anime = data['data']['Media']
        logger.info(f"Found anime: {anime['title']['english'] or anime['title']['romaji']} (ID: {anime['id']})")
        logger.info(f"Genres: {anime['genres']}")
        logger.info(f"Tags: {[tag['name'] for tag in anime['tags']][:5]}")
        logger.info(f"Popularity: {anime['popularity']}, Score: {anime['averageScore']}")
        logger.debug(f"API response time: {elapsed_time:.2f}s")
        
        return anime
        
    except Exception as e:
        logger.error(f"Error getting anime details: {str(e)}")
        return None

# STEP 2: Get similar anime based on genres and tags
def get_similar_anime(genres, tags, exclude_title, per_page=5):
    # logger.info(f"Finding similar anime based on genres: {genres} and tags: {tags}")
    # logger.info(f"Will exclude original title: '{exclude_title}' and return up to {per_page} results")
    
    query = '''
    query ($genres: [String], $tags: [String], $perPage: Int) {
      Page(page: 1, perPage: $perPage) {
        media(type: ANIME, genre_in: $genres, tag_in: $tags, sort: POPULARITY_DESC) {
          id
          title { romaji english }
          genres
          tags { name }
          averageScore
          popularity
        }
      }
    }
    '''
    variables = {'genres': genres, 'tags': tags, 'perPage': per_page + 5}  # Requesting extra to account for exclusions
    
    try:
        # logger.debug(f"Sending request to AniList API: {json.dumps(variables)}")
        start_time = time.time()
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables})
        elapsed_time = time.time() - start_time
        
        if response.status_code != 200:
            # logger.error(f"AniList API request failed: Status {response.status_code}, Response: {response.text}")
            return []
            
        data = response.json()
        
        if 'errors' in data:
            # logger.error(f"AniList API returned errors: {data['errors']}")
            return []
            
        results = data['data']['Page']['media']
        # logger.info(f"API returned {len(results)} anime before filtering")
        # logger.debug(f"API response time: {elapsed_time:.2f}s")

        # Exclude original title with detailed logging
        recommendations = []
        for anime in results:
            title_romaji = (anime['title']['romaji'] or '').lower()
            title_english = (anime['title']['english'] or '').lower()
            exclude_title_lower = exclude_title.lower()
            
            if exclude_title_lower in title_english or exclude_title_lower in title_romaji:
                # logger.debug(f"Excluding anime: {anime['title']['english'] or anime['title']['romaji']} (matches original title)")
                pass
            else:
                recommendations.append(anime)
                # logger.debug(f"Including anime: {anime['title']['english'] or anime['title']['romaji']} (ID: {anime['id']})")

        final_recommendations = recommendations[:per_page]
        # logger.info(f"Final recommendation count: {len(final_recommendations)}")
        
        # Log why each anime was selected
        for anime in final_recommendations:
            anime_title = anime['title']['english'] or anime['title']['romaji']
            matching_genres = set(genres) & set(anime['genres'])
            matching_tags = set(tags) & set([tag['name'] for tag in anime['tags']])
            
            # logger.info(f"Selected: {anime_title}")
            # logger.info(f"  - Matching genres ({len(matching_genres)}/{len(genres)}): {matching_genres}")
            # logger.info(f"  - Matching tags ({len(matching_tags)}/{len(tags)}): {matching_tags}")
            # logger.info(f"  - Popularity: {anime['popularity']}, Score: {anime['averageScore']}")
            
        return final_recommendations
        
    except Exception as e:
        # logger.error(f"Error getting similar anime: {str(e)}")
        return []

# Interpret user request to structured query using OpenAI
def interpret_user_request(user_request):
    logger.info(f"Interpreting user request: '{user_request}'")
    
    prompt = f"""
    Extract structured search criteria from the following user request.

    Examples:
    - \"I want an anime like Dumbbell Nan Kilo Moteru\" → {{\"type\": \"similar\", \"title\": \"Dumbbell Nan Kilo Moteru\"}}
    - \"recommend an isekai anime\" → {{\"type\": \"genre\", \"genre\": \"Isekai\"}}

    User request: \"{user_request}\"
    """

    try:
        logger.debug("Sending request to OpenAI API")
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=50
        )
        elapsed_time = time.time() - start_time
        
        result = response.choices[0].message.content.strip()
        logger.debug(f"OpenAI API response: {result}")
        logger.debug(f"API response time: {elapsed_time:.2f}s")
        
        interpreted_request = eval(result)
        logger.info(f"Interpreted request: {interpreted_request}")
        
        return interpreted_request
        
    except Exception as e:
        logger.error(f"Error interpreting user request: {str(e)}")
        logger.warning("Falling back to default interpretation")
        
        # Basic fallback parser
        if "like" in user_request.lower():
            # Extract title after "like"
            parts = user_request.lower().split("like")
            if len(parts) > 1:
                title = parts[1].strip()
                logger.info(f"Fallback parser extracted title: '{title}'")
                return {"type": "similar", "title": title}
        
        # Check for common genre keywords
        common_genres = ["action", "adventure", "comedy", "drama", "fantasy", "horror", "isekai", "romance", "sci-fi", "slice of life"]
        for genre in common_genres:
            if genre in user_request.lower():
                logger.info(f"Fallback parser detected genre: '{genre}'")
                return {"type": "genre", "genre": genre.capitalize()}
        
        # Default fallback
        logger.warning("Fallback parser could not interpret request, defaulting to generic search")
        return {"type": "genre", "genre": "Action"}

# Get anime by genre or tag
def get_anime_by_genre_or_tag(genre_or_tag, per_page=5):
    logger.info(f"Searching for anime with genre/tag: '{genre_or_tag}'")
    
    query = '''
    query ($genreOrTag: String, $perPage: Int) {
      Page(page: 1, perPage: $perPage) {
        media(type: ANIME, genre_in: [$genreOrTag], sort: POPULARITY_DESC) {
          id
          title { romaji english }
          genres
          averageScore
          popularity
        }
      }
    }
    '''
    variables = {'genreOrTag': genre_or_tag, 'perPage': per_page}
    
    try:
        logger.debug(f"Sending request to AniList API: {json.dumps(variables)}")
        start_time = time.time()
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables})
        elapsed_time = time.time() - start_time
        
        if response.status_code != 200:
            logger.error(f"AniList API request failed: Status {response.status_code}, Response: {response.text}")
            return []
            
        data = response.json()
        
        if 'errors' in data:
            logger.error(f"AniList API returned errors: {data['errors']}")
            return []
            
        results = data['data']['Page']['media']
        logger.info(f"Found {len(results)} anime for genre/tag '{genre_or_tag}'")
        logger.debug(f"API response time: {elapsed_time:.2f}s")
        
        # Log the results
        for anime in results:
            logger.debug(f"Found: {anime['title']['english'] or anime['title']['romaji']} (ID: {anime['id']})")
            logger.debug(f"  - Genres: {anime['genres']}")
            logger.debug(f"  - Popularity: {anime['popularity']}, Score: {anime['averageScore']}")
            
        return results
        
    except Exception as e:
        logger.error(f"Error getting anime by genre/tag: {str(e)}")
        return []

# Retry with alternatives using OpenAI
def retry_with_alternatives(original_genre):
    logger.info(f"Original genre '{original_genre}' returned no results, searching for alternatives")
    
    prompt = f"""
    The genre '{original_genre}' returned no results in an anime database search.
    Suggest 3 alternative genres or tags commonly used in anime databases that closely relate to '{original_genre}'.
    Return just a comma-separated list of alternatives.
    """

    try:
        logger.debug("Sending request to OpenAI API for alternatives")
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=20
        )
        elapsed_time = time.time() - start_time
        
        alternatives = response.choices[0].message.content.strip().split(", ")
        logger.info(f"OpenAI suggested alternatives: {alternatives}")
        logger.debug(f"API response time: {elapsed_time:.2f}s")
        
        return alternatives
        
    except Exception as e:
        logger.error(f"Error getting alternative genres: {str(e)}")
        logger.warning("Falling back to hardcoded alternatives")
        
        # Hardcoded fallbacks based on common genre mappings
        fallback_map = {
            "isekai": ["Fantasy", "Adventure", "Action"],
            "superhero": ["Action", "Drama", "Sci-Fi"],
            "cyberpunk": ["Sci-Fi", "Action", "Thriller"],
            "magical girl": ["Fantasy", "Mahou Shoujo", "Action"],
            "post-apocalyptic": ["Sci-Fi", "Drama", "Action"]
        }
        
        if original_genre.lower() in fallback_map:
            alternatives = fallback_map[original_genre.lower()]
        else:
            alternatives = ["Action", "Adventure", "Fantasy"]
            
        logger.info(f"Using fallback alternatives: {alternatives}")
        return alternatives

# Robust genre search with retry mechanism
def robust_genre_search(genre, per_page=5):
    logger.info(f"Performing robust genre search for: '{genre}'")
    
    results = get_anime_by_genre_or_tag(genre, per_page)
    if results:
        logger.info(f"Found {len(results)} anime with primary genre '{genre}'")
        return results

    logger.warning(f"No results found for genre '{genre}', trying alternatives")
    alternatives = retry_with_alternatives(genre)
    
    for i, alt in enumerate(alternatives):
        logger.info(f"Trying alternative {i+1}/{len(alternatives)}: '{alt}'")
        results = get_anime_by_genre_or_tag(alt, per_page)
        if results:
            logger.info(f"Found {len(results)} anime with alternative genre '{alt}'")
            return results
        else:
            logger.warning(f"No results found for alternative genre '{alt}'")

    logger.error(f"All searches failed. No anime found for '{genre}' or its alternatives")
    return []

# Main recommendation function
def recommend(user_request):
    logger.info(f"Starting recommendation process for request: '{user_request}'")
    
    try:
        criteria = interpret_user_request(user_request)
        
        if criteria['type'] == 'similar':
            title = criteria['title']
            logger.info(f"Processing 'similar' type request for title: '{title}'")
            
            anime_details = get_anime_details(title)
            if not anime_details:
                logger.error(f"Could not find details for anime '{title}'")
                print(f"Sorry, I couldn't find information about '{title}'. Please check the spelling or try another anime.")
                return
                
            genres = anime_details['genres']
            tags = [tag['name'] for tag in anime_details['tags']][:5]
            
            logger.info(f"Using {len(genres)} genres and {len(tags)} tags for similarity search")
            logger.debug(f"Genres: {genres}")
            logger.debug(f"Tags: {tags}")

            recommendations = get_similar_anime(genres, tags, title)
            
            if not recommendations:
                logger.warning(f"No similar anime found for '{title}'")
                print(f"I couldn't find any anime similar to '{title}'. This might be a unique anime or there could be an issue with the search criteria.")
                return
                
            print(f"\nRecommendations similar to '{title}':")
            for i, anime in enumerate(recommendations):
                anime_title = anime['title']['english'] or anime['title']['romaji']
                genre_str = ', '.join(anime['genres'])
                print(f"{i+1}. {anime_title}")
                print(f"   Genres: {genre_str}")
                print(f"   Popularity: {anime['popularity']}, Score: {anime['averageScore']}/100")
                
                # Show matching criteria for transparency
                matching_genres = set(genres) & set(anime['genres'])
                matching_tags = set(tags) & set([tag['name'] for tag in anime['tags']])
                print(f"   Matched: {len(matching_genres)} genres, {len(matching_tags)} tags")
                print()

        elif criteria['type'] == 'genre':
            genre = criteria['genre']
            logger.info(f"Processing 'genre' type request for genre: '{genre}'")
            
            recommendations = robust_genre_search(genre)

            if recommendations:
                print(f"\nRecommendations for genre '{genre}':")
                for i, anime in enumerate(recommendations):
                    anime_title = anime['title']['english'] or anime['title']['romaji']
                    genre_str = ', '.join(anime['genres'])
                    print(f"{i+1}. {anime_title}")
                    print(f"   Genres: {genre_str}")
                    print(f"   Popularity: {anime['popularity']}, Score: {anime['averageScore']}/100")
                    print()
            else:
                print(f"No recommendations found for '{genre}'. This might not be a recognized genre in the anime database.")
        
        else:
            logger.error(f"Unknown criteria type: {criteria['type']}")
            print("I couldn't understand your request. Please try asking for a specific anime or genre.")
            
    except Exception as e:
        logger.error(f"Error in recommendation process: {str(e)}")
        print("Sorry, an error occurred while processing your request. Please try again with a different query.")

# Example Usage
if __name__ == "__main__":
    print("🌟 Enhanced Anime Recommender 🌟")
    print("Ask for recommendations by anime (e.g., 'Find anime like Attack on Titan')")
    print("Or by genre (e.g., 'Recommend fantasy anime')")
    print("-" * 50)
    
    while True:
        user_request = input("\nEnter your anime request (or 'exit' to quit): ")
        
        if user_request.lower() in ['exit', 'quit', 'q']:
            break
            
        start_time = time.time()
        recommend(user_request)
        elapsed_time = time.time() - start_time
        logger.info(f"Total recommendation time: {elapsed_time:.2f}s")