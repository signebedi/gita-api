import pandas as pd

# Load the JSON file into a DataFrame
df = pd.read_json('data/translation.json')
df2 = pd.read_json('data/verse.json')
df3 = pd.read_json('data/authors.json')
authors = list(df3[['id', 'name']].itertuples(index=False, name=None))
authors_dict = dict(authors)

# Function to map author_id to authorName
def get_author_name(author_id):
    return authors_dict.get(author_id, "Unknown")

# Apply the function to df2
df['authorName'] = df['author_id'].apply(get_author_name)

# Merge df with df2 on the matching verse_id and verse_number
merged_df = pd.merge(df, df2, left_on='verse_id', right_on='verse_number')

# Update the 'verseNumber' and 'chapter_id' fields in df
df['verse_number'] = merged_df['verse_number']
df['chapter_number'] = merged_df['chapter_number']
df['full_ref'] = df.apply(lambda row: f"{row['chapter_number']}.{row['verse_number']}", axis=1)



df.to_json('data/cleaned_data.json')