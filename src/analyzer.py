# get parent directory
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# add parent directory to sys.path
import sys
sys.path.append(parent_dir)


from openai import OpenAI
client = OpenAI()

def get_relevant_tags_and_genres(title: str, genres: list, tags: list) -> tuple[list, list]:
    response = client.responses.create(
        model="gpt-4.1",
        input="Return ONLY a python list of the 3 most relevant tags for the anime " + title + " with the genres " + str(genres) + " and the tags " + str(tags)
    )

    relevant_genres = [genres[0]]

    try:
        relevant_tags = eval(response.output_text)
    except:
        print("Error")
        print(response.output_text)
        relevant_tags = [tags[0]]
        
    return relevant_genres, relevant_tags