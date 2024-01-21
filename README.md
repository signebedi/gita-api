# gita-api
a RESTful Bhagavad Gita API


#### Overview
This API allows users to fetch specific sections from the Bhagavad Gita based on chapter and verse references. It supports fetching an entire chapter (`7`), a specific verse (`7.2`), or a range of verses (`7.2-8`). Based on https://bible-api.com/, using https://github.com/gita/gita. 

#### Endpoints

##### GET /gita
Retrieves content from the Bhagavad Gita based on a given reference and author ID.

Parameters:
- `reference` (string): The chapter/verse reference in the format of `chapter`, `chapter.verse`, or `chapter.start_verse-end_verse`. Chapters range from 1 to 18, and verses are non-zero integers.
- `author_id` (int, optional): The ID of the author's translation to use. Defaults to 16 if not provided. Range: 1 to 21.

Response:
- A JSON object containing:
  - `author`: Name of the author for the translation.
  - `text`: List of strings with the content of the requested verses.
  - `chapter`: The chapter number.
  - `verses`: Specific verse or range of verses.
  - `reference`: Full reference as requested.

Errors:
- Returns a 400 error with an appropriate message if the reference format is invalid, the reference is not provided, or if no content is found for the given reference and author ID.

Example:

```
GET /gita?reference=3.5-7&author_id=18
```

Response:

```json
{
  "author": "Author Name",
  "text": ["Verse 3.5 content", "Verse 3.6 content", "Verse 3.7 content"],
  "chapter": 3,
  "verses": "5-7",
  "reference": "3.5-7"
}