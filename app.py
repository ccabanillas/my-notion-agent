import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime

load_dotenv()

app = Flask(__name__)

notion = Client(auth=os.environ["NOTION_API_KEY"])
database_id = os.environ["NOTION_DATABASE_ID"]

@app.route('/')
def hello_world():
    return 'Hello, World! Your Notion AI Agent is coming soon!'

@app.route('/add_page', methods=['POST'])
def add_page():
    content = request.json.get('content', '')
    
    if not content:
        return jsonify({"error": "No content provided"}), 400

    properties = {
        "Name": {"title": [{"text": {"content": content[:100]}}]},
        "NextRightActionNotes": {"rich_text": [{"text": {"content": content}}]},
        "Date": {"date": {"start": datetime.now().isoformat()}},
        "NextActionTiming": {"status": {"name": "Today"}},  # Default to "ThisWeek"
        "WinTheWeek": {"checkbox": False}  # Default to unchecked
    }

    try:
        new_page = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
        return jsonify({"message": "Page created successfully", "page_id": new_page["id"]}), 201
    except Exception as e:
        return jsonify({"error": str(e), "database_id": database_id}), 500

if __name__ == '__main__':
    app.run(debug=True)