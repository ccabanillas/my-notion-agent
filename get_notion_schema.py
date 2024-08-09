import os
import json
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

notion = Client(auth=os.environ["NOTION_API_KEY"])
database_id = os.environ["NOTION_DATABASE_ID"]

database = notion.databases.retrieve(database_id)
print(json.dumps(database['properties'], indent=2))