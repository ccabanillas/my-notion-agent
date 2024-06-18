from fastapi import FastAPI, HTTPException
from transformers import pipeline
import requests

app = FastAPI()

NOTION_API_KEY = "your_notion_api_key"
DATABASE_IDS = {
    'task': 'your_task_database_id',
    'flashcard': 'your_flashcard_database_id',
    'general': 'your_general_database_id'
}

classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")

def create_notion_page(api_key, database_id, title, content):
    url = 'https://api.notion.com/v1/pages'
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16"
    }
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def classify_page(title):
    if 'task' in title.lower():
        return 'task'
    elif 'flashcard' in title.lower():
        return 'flashcard'
    else:
        return 'general'

@app.post("/add_notion_page/")
async def add_notion_page(title: str, content: str):
    page_type = classify_page(title)
    database_id = DATABASE_IDS[page_type]
    result = create_notion_page(NOTION_API_KEY, database_id, title, content)
    if result.get('object') == 'error':
        raise HTTPException(status_code=400, detail=result)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)