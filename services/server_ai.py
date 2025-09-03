import json
import os
import asyncio
import datetime
import logging
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# LlamaIndex LLM & MCP imports
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from llama_index.core.agent.workflow import FunctionAgent, ToolCall, ToolCallResult
from llama_index.core.workflow import Context
from llama_index.tools.mcp import McpToolSpec, BasicMCPClient

load_dotenv()

# ---- Setup ----
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all during dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging config
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/sse")
HISTORY_FILE = "../logging/interaction_history.json"

# Load previous history if exists
if not os.path.exists("../logging"):
    os.makedirs("../logging")
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            interaction_history = json.load(f)
    except Exception as e:
        logger.error(f"Could not load history: {e}")
        interaction_history = []
else:
    interaction_history = []


# ---- Helper Functions ----
def get_llm(model: str):
    if model == "ollama":
        return Ollama(model="llama3.2:1b")
    elif model == "gpt":
        return OpenAI(model="gpt-4o-mini")
    else:
        return Ollama(model="phi4-mini:3.8b")


async def create_agent(model: str):
    """Create an MCP-powered agent with chosen LLM."""
    llm = get_llm(model)
    Settings.llm = llm

    client = BasicMCPClient(MCP_SERVER_URL)
    tool_spec = McpToolSpec(client=client)
    tools = await tool_spec.to_tool_list_async()

    agent = FunctionAgent(
        name="LegalAgent",
        description="Agent that assists with parsing French legal code using MCP tools.",
        tools=tools,
        llm=llm,
        system_prompt=(
            "You are a legal assistant specialized in French law. "
            "Always use available MCP tools to search and reference articles."
        ),
    )
    return agent


# ---- API Models ----
class AskRequest(BaseModel):
    query: str
    model: str = "ollama"


# ---- API Routes ----

@app.post("/ask")
async def ask(req: AskRequest):
    """Ask the LLM a question about the code using MCP tools, log interaction."""
    start_time = datetime.datetime.now()
    tool_calls = []
    tool_outputs = []

    try:
        agent = await create_agent(req.model)
        ctx = Context(agent)
        handler = agent.run(req.query, ctx=ctx)

        async for event in handler.stream_events():
            if isinstance(event, ToolCall):
                tool_calls.append({
                    "tool_name": event.tool_name,
                    "tool_kwargs": event.tool_kwargs
                })
            elif isinstance(event, ToolCallResult):
                try:
                    output = json.loads(str(event.tool_output))
                except json.JSONDecodeError:
                    output = str(event.tool_output)
                tool_outputs.append({
                    "tool_name": event.tool_name,
                    "tool_output": output
                })

        response = await handler
        answer = str(response)

        # Log interaction
        interaction = {
            "time": start_time.isoformat(),
            "prompt": req.query,
            "model": req.model,
            "response_time": (datetime.datetime.now() - start_time).total_seconds(),
            "answer": answer,
            "tool_calls": tool_calls,
            "tool_outputs": tool_outputs
        }
        interaction_history.append(interaction)

        # Save log
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(interaction_history, f, ensure_ascii=False, indent=2)

        return {"answer": answer}

    except Exception as e:
        logger.error(f"Error in /ask: {e}")
        error_entry = {
            "time": start_time.isoformat(),
            "prompt": req.query,
            "model": req.model,
            "response_time": (datetime.datetime.now() - start_time).total_seconds(),
            "answer": f"Error: {str(e)}",
            "tool_calls": tool_calls,
            "tool_outputs": tool_outputs
        }
        interaction_history.append(error_entry)

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(interaction_history, f, ensure_ascii=False, indent=2)

        return {"error": str(e)}
