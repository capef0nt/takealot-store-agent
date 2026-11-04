from azure.identity import DefaultAzureCredential 
from azure.ai.projects import AIProjectClient
from dotenv import load_dotenv
from config import settings
import os 

load_dotenv()
cfg = settings()

credential = DefaultAzureCredential()

client = AIProjectClient(endpoint=cfg.project_endpoint, credential=credential)

print(cfg.project_endpoint)

for agent in client.agents.list():
    print(agent.id, "|", agent.name)

print("ok")