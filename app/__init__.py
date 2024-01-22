import re
import pandas as pd
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# Add rate limits
limiter = Limiter(get_remote_address, app=app, 
    default_limits=["200 per day", "50 per hour"],
)

# Load the JSON file into a DataFrame
df = pd.read_json('data/translation.json')
df2 = pd.read_json('data/verse.json')
df3 = pd.read_json('data/authors.json')
authors = list(df3[['id', 'name']].itertuples(index=False, name=None))

# Regular expressions for different types of references
CHAPTER_REGEX = re.compile(r'^([1-9]|1[0-8])$')
VERSE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9]+)$')
RANGE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9]+)-([1-9]|[1-9][0-9]+)$')


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


def get_reference(ref_type, chapter, verse, range_end, author_id):
    """
    Fetch the Gita content along with metadata based on the reference type and details.

    :param ref_type: str - The type of reference ('chapter', 'verse', or 'range').
    :param chapter: int - The chapter number.
    :param verse: int - The verse number (if applicable).
    :param range_end: int - The end verse number (if applicable).
    :param author_id: int - The author ID.
    :return: dict - A dictionary containing the text and metadata.
    """
    # Filter df2 based on the reference type to get the verse IDs
    if ref_type == 'chapter':
        verse_ids = df2[df2['chapter_number'] == chapter]['id'].tolist()
        full_reference = str(chapter)
    elif ref_type == 'verse':
        verse_ids = df2[(df2['chapter_number'] == chapter) & (df2['verse_number'] == verse)]['id'].tolist()
        full_reference = f"{chapter}.{verse}"
    elif ref_type == 'range':

        if not range_end:
            raise ValueError('Invalid reference type')

        verse_ids = df2[(df2['chapter_number'] == chapter) & (df2['verse_number'].between(verse, range_end))]['id'].tolist()
        full_reference = f"{chapter}.{verse}-{range_end}"
    else:
        raise ValueError('Invalid reference type')

    if not verse_ids:
        raise ValueError('No verses found for the given reference')

    # Use verse_ids to filter df and get descriptions for the specified author
    filtered_df = df[(df['verse_id'].isin(verse_ids)) & (df['author_id'] == author_id)]
    if filtered_df.empty:
        raise ValueError('No records found for the author and verses')

    # Prepare the output with metadata
    output = {
        "author": filtered_df.iloc[0]['authorName'],
        "text": filtered_df['description'].tolist(),
        "chapter": chapter,
        "verses": verse if ref_type == 'verse' else f"{verse}-{range_end}" if ref_type == 'range' else 'All',
        "reference": full_reference
    }

    return output

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html.jinja', authors=authors)

@app.route('/api/gita', methods=['GET'])
def get_gita_section():
    reference = request.args.get('reference')
    author_id = int(request.args.get('author_id', default='16'))

    # Check if reference is provided
    if not reference:
        return jsonify({'error': 'No reference provided'}), 400

    reference = reference.strip()

    try:
        # Validate reference type
        ref_type, chapter, verse, range_end = validate_ref_type(reference)

        # Fetch the relevant content
        gita_content = get_reference(ref_type, chapter, verse, range_end, author_id)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'content': gita_content}), 200

if __name__ == '__main__':
    app.run(debug=True)
