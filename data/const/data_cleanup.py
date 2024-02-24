import re
import pandas as pd

def process_markdown_constitution(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    data = []
    current_chapter = ''
    current_section = 0
    current_text = ''

    for line in lines:
        text_list = line.split('\\')
        full_ref = text_list[0]
        chapter = full_ref.split(".")[0]
        verse = full_ref.split(".")[1]

        description = "".join(text_list[1:])

        data.append({
            'full_ref': full_ref,
            'chapter_number': chapter,
            'verse_number': verse,
            'description': description.strip()
        })

    return data


# Process the markdown formatted constitution text
constitution_data = process_markdown_constitution('data/const/const.txt')

# Convert the structured data to a DataFrame
df = pd.DataFrame(constitution_data)

# Assign columns for authorName and author_id for consistency
df['author_id'] = 16
df['authorName'] = 'U.S. Constitution'

# Write the DataFrame to a JSON file, matching your output structure
output_file = 'data/const/cleaned_data.json'
df.to_json(output_file)

print(f"Processed data written to {output_file}")