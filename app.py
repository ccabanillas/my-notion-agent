import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime
from openai import OpenAI
import re

print(f"Current working directory: {os.getcwd()}")
print(f"Contents of current directory: {os.listdir('.')}")

print("Before load_dotenv:")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")

load_dotenv(dotenv_path=".env", verbose=True)

print("After load_dotenv:")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

openai_client = OpenAI(api_key=openai_api_key)

notion = Client(auth=os.environ["NOTION_API_KEY"])
outcomes_database_id = os.environ["NOTION_OUTCOMES_DATABASE_ID"]
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
neuracache_database_id = os.environ["NOTION_NEURACACHE_DATABASE_ID"]

@app.route('/')
def hello_world():
    return 'Hello, World! Your Notion AI Agent is coming soon!'

def is_flashcard_request(content):
    return bool(re.search(r'\b(flashcard|flash card|neuracache)\b', content, re.IGNORECASE))
def generate_flashcard_content(prompt):
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates flash card content. Provide a concise question and answer pair in the following format:\nQuestion: [Your question here]\nAnswer: [Your answer here]"},
            {"role": "user", "content": f"Create a flash card about: {prompt}"}
        ]
    )
    content = response.choices[0].message.content.strip()
    
    # Split the content into question and answer
    parts = content.split("\n", 1)
    if len(parts) == 2 and parts[0].startswith("Question:") and parts[1].startswith("Answer:"):
        question = parts[0].replace("Question:", "").strip()
        answer = parts[1].replace("Answer:", "").strip()
    else:
        # Fallback in case the format is not as expected
        question = prompt
        answer = content

    return question, answer

def create_flashcard(content):
    # Extract the main topic from the voice input
    topic = re.sub(r'\b(flashcard|flash card|neuracache)\b', '', content, flags=re.IGNORECASE).strip()
    
    # Generate flash card content using OpenAI
    question, answer = generate_flashcard_content(topic)

    # Create the page in the Neuracache database
    properties = {
        "Title": {"title": [{"text": {"content": question}}]},
        "Text": {"rich_text": [{"text": {"content": answer}}]},
        "Tags": {"multi_select": [{"name": "Software Dev"}]},  # Default tag, adjust as needed
    }

    try:
        new_page = notion.pages.create(
            parent={"database_id": neuracache_database_id},
            properties=properties
        )
        return jsonify({
            "message": "Flash card created successfully", 
            "page_id": new_page["id"],
            "question": question,
            "answer": answer
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/add_page', methods=['POST'])
def add_page():
    content = request.json.get('content', '')

    if not content:
        return jsonify({"error": "No content provided"}), 400

    if is_flashcard_request(content):
        return create_flashcard(content)
    else:
        properties = {
            "Name": {"title": [{"text": {"content": content[:100]}}]},
            "NRANotes": {"rich_text": [{"text": {"content": content}}]},
            "Date": {"date": {"start": datetime.now().isoformat()}},
            "NRATiming": {"status": {"name": "Today"}},
            "WinTheWeek": {"checkbox": False}
        }

    try:
        new_page = notion.pages.create(
            parent={"database_id": outcomes_database_id},
            properties=properties
        )
        return jsonify({"message": "Page created successfully", "page_id": new_page["id"]}), 201
    except Exception as e:
        return jsonify({"error": str(e), "database_id": outcomes_database_id}), 500

if __name__ == '__main__':
    app.run(debug=True)