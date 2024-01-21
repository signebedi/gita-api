import re
import pandas as pd
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load the JSON file into a DataFrame
df = pd.read_json('data/translation.json')

# Regular expressions for different types of references
CHAPTER_REGEX = re.compile(r'^([1-9]|1[0-8])$')
VERSE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9]+)$')
RANGE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9]+)-([1-9]|[1-9][0-9]+)$')



@app.route('/gita', methods=['GET'])
def get_gita_section():
    reference = request.args.get('reference')
    author_id = int(request.args.get('author_id', default='16'))

    # Check if reference is provided
    if not reference:
        return jsonify({'error': 'No reference provided'}), 400


    # Validate and parse the reference
    if CHAPTER_REGEX.match(reference):
        ref_type = 'chapter'
        chapter = int(reference)
    elif VERSE_REGEX.match(reference):
        ref_type = 'verse'
        chapter, verse = map(int, reference.split('.'))
    elif RANGE_REGEX.match(reference):
        ref_type = 'range'
        chapter, verse_range = reference.split('.')
        start_verse, end_verse = map(int, verse_range.split('-'))
    else:
        return jsonify({'error': 'Invalid reference format'}), 400

    # Query the DataFrame for the relevant content
    try:
        if ref_type == 'chapter':
            verses = df[(df['author_id'] == author_id) & (df['verseNumber'].between(chapter * 100 + 1, chapter * 100 + 100))]
        elif ref_type == 'verse':
            verses = df[(df['author_id'] == author_id) & (df['verseNumber'] == chapter * 100 + verse)]
        else:  # ref_type == 'range'
            verses = df[(df['author_id'] == author_id) & (df['verseNumber'].between(chapter * 100 + start_verse, chapter * 100 + end_verse))]

        if verses.empty:
            raise ValueError('No records found')

        gita_content = verses['description'].tolist()
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'content': gita_content}), 200

if __name__ == '__main__':
    app.run(debug=True)
