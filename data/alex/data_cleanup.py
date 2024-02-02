import pandas as pd

# Load the JSON file into a DataFrame
df = pd.read_csv('data/alex/full_corpus_latin_library.csv', sep="|")
authors_df = pd.read_json('data/alex/authors.json')
authors = list(authors_df[['id', 'name']].itertuples(index=False, name=None))
authors_dict = dict(authors)

# Function to map author_id to authorName
def get_author_name(author_id):
    return authors_dict.get(author_id, "Unknown")

# Select the correct commentary
df = df.loc[df['Commentary'] == "Alex"]


# Apply the author-setting function to df (doesn't really apply here)
df['author_id'] = 16
df['authorName'] = df['author_id'].apply(get_author_name)

# Rename 
df['verse_number'] = df['Passage']
df['chapter_number'] = df['Book']
df['full_ref'] = df['Cite']
df['description'] = df['Text']

# Add book id
df['book_id'] = '2'

# Drop bloat categories
df = df[['authorName', 'author_id', 'description', 'verse_number', 'chapter_number', 'full_ref', 'book_id']]

df.to_json('data/alex/cleaned_data.json')

