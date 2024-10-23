# notion_agent.py
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from langchain.agents import initialize_agent, AgentType
from langchain.tools import StructuredTool
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI  # Updated import
from notion_client import Client
from enum import Enum
from datetime import datetime
import json

# Load environment variables at startup
load_dotenv()

# Validate required environment variables
def validate_env_vars():
    required_vars = ["NOTION_TOKEN", "OPENAI_API_KEY", "NEURACACHE_DB_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please make sure they are set in your .env file"
        )

# Define your models and classes (as before)
class NeuracacheTag(str, Enum):
    ME = "M&E"
    SOFTWARE_DEV = "Software Dev"
    BEHAVIOR_SCIENCE = "Behavior Science"
    PUZZLES = "Puzzles"
    CIO = "CIO"
    CALIFORNIA = "California"
    DATA_SCIENCE = "Data Science"
    DEVOPS = "DevOps"
    TECH_INFRASTRUCTURE = "TechInfrastructure"
    ARCHIVED = "Archived"
    ECONOMICS = "Economics"

class FlashcardRequest(BaseModel):
    text: str
    tags: Optional[List[NeuracacheTag]] = None

class NeuracacheTool:
    def __init__(self, notion_client: Client, database_id: str):
        self.notion = notion_client
        self.database_id = database_id
        print(f"Initialized NeuracacheTool with database ID: {database_id}")  # Debug log

    def create_flashcard(self, title: str, text: str, tags: List[NeuracacheTag]) -> dict:
        print(f"Creating flashcard: {title}")  # Debug log
        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "Text": {"rich_text": [{"text": {"content": text}}]},
            "Tags": {"multi_select": [{"name": tag} for tag in tags]}
        }
        
        response = self.notion.pages.create(
            parent={"database_id": self.database_id},
            properties=properties
        )
        return {"status": "success", "page_id": response["id"]}

class NotionAgent:
    def __init__(self):
        # Load environment variables
        self.notion_token = os.getenv("NOTION_TOKEN")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.neuracache_db_id = os.getenv("NEURACACHE_DB_ID")
        
        print(f"Initializing NotionAgent with database ID: {self.neuracache_db_id}")  # Debug log
        
        # Initialize Notion client
        self.notion = Client(auth=self.notion_token)
        
        # Initialize tool
        self.neuracache_tool = NeuracacheTool(self.notion, self.neuracache_db_id)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
        temperature=0,
        model_name="gpt-3.5-turbo",  # Using the latest version
        openai_api_key=self.openai_key
        )
        
        # Define available tags
        self.available_tags = [tag.value for tag in NeuracacheTag]
        
        # Initialize system prompt
        self.system_prompt = ChatPromptTemplate.from_template("""
        You are an intelligent flashcard creation assistant that helps users create effective flashcards in Notion.
        
        Available tags: {available_tags}
        
        When processing a flashcard request:
        1. Create a clear, concise title that captures the key concept
        2. Format the text as a complete, well-structured explanation
        3. Select relevant tags from the available options
        4. For technical topics, include code examples when relevant
        5. For concepts, include concrete examples
        6. Break down complex ideas into digestible pieces
        
        Return your response in valid JSON format with these exact keys:
        {{"title": "The flashcard title", "text": "The detailed explanation", "tags": ["Tag1", "Tag2"]}}
""")

    async def process_flashcard(self, request_text: str) -> dict:
        print(f"Processing flashcard request: {request_text}")  # Debug log
        
        messages = self.system_prompt.format_messages(
            available_tags=", ".join(self.available_tags)
        )
        
        user_prompt = f"""
        Create a flashcard from this request: {request_text}
        """
        
        messages.append(HumanMessage(content=user_prompt))
        
        response = self.llm.invoke(messages)
        content = json.loads(response.content)
        
        # Validate tags
        valid_tags = [tag for tag in content["tags"] if tag in self.available_tags]
        
        # Create the flashcard
        result = self.neuracache_tool.create_flashcard(
            title=content["title"],
            text=content["text"],
            tags=valid_tags
        )
        
        return {
            "status": "success",
            "result": result,
            "flashcard": {
                "title": content["title"],
                "text": content["text"],
                "tags": valid_tags
            }
        }

# Initialize FastAPI app
app = FastAPI()
port = os.getenv("PORT", "8000")

# Initialize agent at startup
@app.on_event("startup")
async def startup_event():
    try:
        # Validate environment variables
        validate_env_vars()
        print("Environment variables validated successfully")  # Debug log
        
        # Initialize the agent
        app.state.agent = NotionAgent()
        print("NotionAgent initialized successfully")  # Debug log
    except Exception as e:
        print(f"Error during startup: {str(e)}")  # Debug log
        raise

@app.post("/flashcard")
async def create_flashcard(request: FlashcardRequest):
    if not hasattr(app.state, "agent"):
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return await app.state.agent.process_flashcard(request.text)

@app.get("/health")
async def health_check():
    """Check if the service is running and properly configured"""
    return {
        "status": "healthy",
        "env_vars_set": {
            "NOTION_TOKEN": bool(os.getenv("NOTION_TOKEN")),
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "NEURACACHE_DB_ID": bool(os.getenv("NEURACACHE_DB_ID"))
        }
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)