"""
gita/__init__.py: logic for the RESTful Bhagavad Gita API 
Copyright (C) 2024 Sig Janoska-Bedi

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import re
import pandas as pd
from fuzzywuzzy import process, fuzz


__version__ = "4.0.0"
__name__ = "gita"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"



# turn off warnings to avoid a rather silly one being dropped in the terminal,
# see https://stackoverflow.com/a/20627316/13301284. 
pd.options.mode.chained_assignment = None


# Regular expressions for different types of references
CHAPTER_REGEX = re.compile(r'^([1-9]|1[0-8])$')
VERSE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9])$')
RANGE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9])-([1-9]|[1-9][0-9])$')


def validate_ref_type(reference):
    """
    Validate the reference and determine its type.

    :param reference: str - The reference string to validate.
    :return: tuple - A tuple containing the reference type and additional details.
    """
    if CHAPTER_REGEX.match(reference):
        return 'chapter', int(reference), None, None

    elif VERSE_REGEX.match(reference):
        chapter, verse = map(int, reference.split('.'))
        return 'verse', chapter, verse, None

    elif RANGE_REGEX.match(reference):
        chapter_part, verse_range = reference.split('.')
        chapter = int(chapter_part)
        start_verse, end_verse = map(int, verse_range.split('-'))

        if start_verse >= end_verse:
            raise ValueError("Invalid verse range: start verse should be less than end verse")

        return 'range', chapter, start_verse, end_verse

    else:
        raise ValueError('Invalid reference format')



def get_reference(ref_type, chapter, verse, range_end, author_id, df):
    """
    Fetch the Gita content along with metadata based on the reference type and details, including a list of pin citations.

    :param ref_type: str - The type of reference ('chapter', 'verse', or 'range').
    :param chapter: int - The chapter number.
    :param verse: int - The verse number (if applicable).
    :param range_end: int - The end verse number (if applicable).
    :param author_id: int - The author ID.
    :param df: DataFrame - The single dataset containing all the necessary information.
    :return: dict - A dictionary containing the text and metadata, including pin citations.
    """
    # Filter based on the reference type
    if ref_type == 'chapter':
        filtered_df = df[(df['chapter_number'] == chapter) & (df['author_id'] == author_id)]
        ref_list = [f"{chapter}.{v}" for v in filtered_df['verse_number'].unique()]
        full_reference = str(chapter)
    elif ref_type == 'verse':
        filtered_df = df[(df['chapter_number'] == chapter) & (df['verse_number'] == verse) & (df['author_id'] == author_id)]
        ref_list = [f"{chapter}.{verse}"]
        full_reference = f"{chapter}.{verse}"
    elif ref_type == 'range':
        if not range_end:
            raise ValueError('Invalid reference type')
        filtered_df = df[(df['chapter_number'] == chapter) & (df['verse_number'].between(verse, range_end)) & (df['author_id'] == author_id)]
        ref_list = [f"{chapter}.{v}" for v in range(verse, range_end + 1)]
        full_reference = f"{chapter}.{verse}-{range_end}"
    else:
        raise ValueError('Invalid reference type')

    if filtered_df.empty:
        raise ValueError('No records found for the given reference and author')

    # Prepare the output with metadata and ref_list
    output = {
        "author": filtered_df.iloc[0]['authorName'],
        "text": filtered_df['description'].tolist(),
        "chapter": str(chapter),
        "verses": str(verse) if ref_type == 'verse' else f"{verse}-{range_end}" if ref_type == 'range' else 'All',
        "reference": full_reference,
        "ref_list": ref_list
    }

    return output




def preprocess(text):
    # Example preprocessing steps
    text = text.lower()  # Lowercase
    text = re.sub(r'\W+', ' ', text)  # Remove non-alphanumeric characters
    return text

def get_highest_match_score(row, search_query):
    description = preprocess(row['description'])
    words = description.split()  # Consider a more advanced tokenizer
    search_query = preprocess(search_query)
    matches = process.extract(search_query, words, scorer=fuzz.WRatio)
    # You can aggregate or select from matches here
    return max(matches, key=lambda x: x[1])[1] if matches else 0

def get_basic_match_score(row, search_query):
    description = preprocess(row['description'])
    search_query = preprocess(search_query)
    match_score = fuzz.token_sort_ratio(search_query, description)
    # print(match_score)
    return match_score


def get_match_score(row, search_query):
    description = preprocess(row['description'])
    search_query = preprocess(search_query)
    bonus = 0
    if search_query in description:  
        # Check for exact match
        bonus = 25    
    match_score = min(fuzz.token_sort_ratio(search_query, description) + bonus, 100)
    return match_score


def perform_fuzzy_search(search_query, df, author_id=16, threshold=10):
    """
    Perform a fuzzy search on segmented text descriptions in the dataframe for a specific author_id.

    :param search_query: str - The search query string.
    :param dataframe: DataFrame - The pandas dataframe to search in.
    :param author_id: int - The author ID for filtering the dataframe.
    :param threshold: int - The threshold for fuzzy matching.
    :return: dict - A dictionary containing the text and metadata.
    """
    # print(type(df), type(author_id))

    # Filter dataframe for the specific author_id
    df = df[df['author_id'] == author_id]


    # Apply the function to compute match scores
    # df['match_score'] = df.apply(lambda row: get_highest_match_score(row, search_query), axis=1)
    df['match_score'] = df.apply(lambda row: get_match_score(row, search_query), axis=1)

    # Sort the DataFrame by match score
    df_sorted = df.sort_values(by='match_score', ascending=False)

    df_sorted = df_sorted.loc[df_sorted['match_score'] >= threshold]
    
    if df_sorted.empty:
        raise ValueError('No records found that match your query')

    # Limit length to the top 15 records
    if len(df_sorted) > 15:
        results = df_sorted[:15]
    else:
        results = df_sorted

    ref_list = results['full_ref'].tolist()
    match_scores = results['match_score'].tolist()
    author = results['authorName'].iloc[0]
    text = results['description'].tolist()
    # print(results['match_score'].tolist())


    # Prepare the output with metadata and ref_list
    output = {
        "author": author,
        "text": text,
        "ref_list": ref_list,
        "match_scores": match_scores,
    }

    return output
