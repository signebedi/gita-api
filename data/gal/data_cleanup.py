import pandas as pd

# Load the JSON file into a DataFrame
df = pd.read_csv('data/gal/full_corpus_latin_library.csv', sep="|")
authors_df = pd.read_json('data/gal/authors.json')
authors = list(authors_df[['id', 'name']].itertuples(index=False, name=None))
authors_dict = dict(authors)

# Function to map author_id to authorName
def get_author_name(author_id):
    return authors_dict.get(author_id, "Unknown")

# Select the correct commentary
df = df.loc[df['Commentary'] == "BG"]

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


# Read the english into memory
english_df = pd.read_json('data/gal/english.json')
english_df = english_df.loc[english_df['Commentary'] == "BG"]

# Add author ID
english_df['author_id'] = 17

# Add the full ref field
# english_df['full_ref'] = "Caes." + " " + english_df['Commentary'] + " " + english_df['chapter_number'].astype(str) + "." + english_df['verse_number'].astype(str)

# Now that the english is in place, apply the author IDs
english_df['authorName'] = english_df['author_id'].apply(get_author_name)

english_df = english_df.loc[:, ~english_df.columns.isin(['Commentary'])]

df_concatenated = pd.concat([df, english_df], ignore_index=True)

df_concatenated.to_json('data/gal/cleaned_data.json')
