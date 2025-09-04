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

SYSTEM_PROMPT = """\
You are an AI assistant specialized in analyzing and extracting information from French legal codes using MCP Tools (e.g., Code des Assurances, Code pénal). Your primary task is to parse legal text, identify key concepts, and provide accurate, concise, and contextually relevant responses.

Follow these guidelines:
1. **Understand Legal Context**: Interpret the input in the context of French law, focusing on domain-specific terminology (e.g., 'assurance,' 'contrat,' 'sinistre,' 'indemnisation,' 'responsabilité').
2. **Extract Key Information**: Prioritize extracting relevant keywords, provisions, or concepts using tools to query the provided database.
3. **Handle French Language**: Account for French linguistic nuances, including proper nouns, legal jargon, and multi-word expressions (e.g., 'responsabilité civile').
4. **Provide Structured Responses**: Summarize findings clearly, citing specific articles or sections (e.g., 'Article L121-1'). If clarification is needed, ask the user for additional context.
5. **Only use the tools**: Leverage available tools to query the legal code database, ensuring responses are grounded in the source text.

Respond in a professional and precise manner, avoiding irrelevant details. If the input is ambiguous, request clarification to ensure accuracy.
"""

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
        system_prompt=SYSTEM_PROMPT,
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
    
@app.post("/set-json-file")
async def set_json_file(file_path: str = Query(...)):
    """Change the JSON file used by the MCP server."""
    valid_files = [
        "../data/output/code_assurances.json",
        "../data/output/code_penal.json",
        "../data/output/code_travail.json"
    ]
    if file_path not in valid_files:
        logger.error(f"Invalid file path: {file_path}")
        return {"error": f"Invalid file path. Choose from: {valid_files}"}
    
    try:
        client = BasicMCPClient(MCP_SERVER_URL)
        tool_spec = McpToolSpec(client=client)
        tools = await tool_spec.to_tool_list_async()
        
        # Find the reload_json_file tool
        reload_tool = next((tool for tool in tools if tool.metadata.name == "reload_json_file"), None)
        if not reload_tool:
            logger.error("reload_json_file tool not found")
            return {"error": "reload_json_file tool not found"}
        
        # Call the tool
        result = await reload_tool(file_path=file_path)
        result_json = json.loads(str(result))
        return result_json
    except Exception as e:
        logger.error(f"Error changing JSON file: {e}")
        return {"error": str(e)}
