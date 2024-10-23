from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.tools import StructuredTool
from langchain.prompts import ChatPromptTemplate
from notion_client import Client
from enum import Enum
from datetime import datetime

# Define valid tags based on your Notion schema
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

class Flashcard(BaseModel):
    title: str
    text: str
    tags: List[NeuracacheTag] = Field(default_factory=list)

class NeuracacheTool:
    """Tool for managing flashcards in Neuracache Notion database"""
    def __init__(self, notion_client: Client, database_id: str):
        self.notion = notion_client
        self.database_id = database_id

    def create_flashcard(self, title: str, text: str, tags: List[NeuracacheTag]) -> dict:
        """Create a flashcard in the Neuracache database"""
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
    def __init__(self, notion_token: str, openai_key: str, neuracache_db_id: str):
        # Initialize Notion client
        self.notion = Client(auth=notion_token)
        self.neuracache_db_id = neuracache_db_id
        
        # Initialize tool
        self.neuracache_tool = NeuracacheTool(self.notion, self.neuracache_db_id)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-3.5-turbo-0613",
            openai_api_key=openai_key
        )
        
        # Define available tags for the system
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
        
        Remember:
        - Each flashcard should focus on one clear concept
        - Text should be comprehensive but concise
        - Use appropriate technical terminology
        - Include relevant context
        - Only use tags from the available list
        """)

    async def process_flashcard(self, request_text: str) -> dict:
        """Process a flashcard request and create it in Notion"""
        # Use LLM to process the request and generate flashcard content
        messages = self.system_prompt.format_messages(
            available_tags=", ".join(self.available_tags)
        )
        
        user_prompt = f"""
        Create a flashcard from this request: {request_text}
        
        Respond in JSON format with these fields:
        - title: A clear, concise title for the flashcard
        - text: The detailed explanation or content
        - tags: List of relevant tags from the available options
        """
        
        messages.append(HumanMessage(content=user_prompt))
        
        response = self.llm.predict_messages(messages)
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

    async def search_flashcards(self, query: str) -> List[dict]:
        """Search existing flashcards"""
        response = self.notion.databases.query(
            database_id=self.neuracache_db_id,
            filter={
                "or": [
                    {
                        "property": "Title",
                        "title": {
                            "contains": query
                        }
                    },
                    {
                        "property": "Text",
                        "rich_text": {
                            "contains": query
                        }
                    }
                ]
            }
        )
        
        return [
            {
                "id": page["id"],
                "title": page["properties"]["Title"]["title"][0]["text"]["content"],
                "text": page["properties"]["Text"]["rich_text"][0]["text"]["content"],
                "tags": [tag["name"] for tag in page["properties"]["Tags"]["multi_select"]]
            }
            for page in response["results"]
        ]

# FastAPI app setup
app = FastAPI()
agent = None

@app.on_event("startup")
async def startup_event():
    global agent
    agent = NotionAgent(
        notion_token="your-notion-token",
        openai_key="your-openai-key",
        neuracache_db_id="your-neuracache-db-id"
    )

@app.post("/flashcard")
async def create_flashcard(request: FlashcardRequest):
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return await agent.process_flashcard(request.text)

@app.get("/search")
async def search_flashcards(q: str):
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return await agent.search_flashcards(q)

@app.get("/tags")
async def list_tags():
    """List all available tags"""
    return {"tags": [tag.value for tag in NeuracacheTag]}