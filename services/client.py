import asyncio
import json
import logging
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from dotenv import load_dotenv
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult, ToolCall
from llama_index.core.workflow import Context
import os
import time
import datetime

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

class CodeHelperApp:
    def __init__(self, root, server_url: str, code_type: str, model: str):
        self.root = root
        self.root.title(f"{code_type} MCP Assistant")
        self.root.geometry("600x400")
        self.server_url = server_url
        self.code_type = code_type
        self.model = model
        self.history = []  # List to store interaction history

        # Set history file path and load existing history
        self.history_file = "./logging/interaction_history.json"
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error loading history file: {e}")
                self.history = []
            except Exception as e:
                logger.error(f"Error accessing history file: {e}")
                self.history = []

        # Setup LLM
        if model == "ollama":
            llm = Ollama(model="llama3.2:1b")
        elif model == "gpt":
            llm = OpenAI(model="gpt-4o-mini")
        else:
            llm = Ollama(model="phi4-mini:3.8b")
        Settings.llm = llm

        # Initialize MCP client
        self.mcp_client = BasicMCPClient(server_url)
        self.mcp_tool = McpToolSpec(client=self.mcp_client)

        # Initialize agent and context
        self.loop = asyncio.get_event_loop()
        self.tools = self.loop.run_until_complete(self.get_tools())
        self.agent = self.loop.run_until_complete(self.get_agent())
        self.agent_context = Context(self.agent)

        # Create UI elements
        self.model_frame = ttk.Frame(root)
        self.model_frame.pack(pady=5)
        
        self.model_text = tk.StringVar()
        self.model_text.set(f"Current model: {self.model}")
        self.current_model_text = ttk.Label(self.model_frame, textvariable=self.model_text)
        self.current_model_text.pack(side="left", padx=5)
        
        self.model1_button = ttk.Button(self.model_frame, text="GPT", command=lambda: self.switch_model("gpt"))
        self.model1_button.pack(side="left", padx=5)
        
        self.model2_button = ttk.Button(self.model_frame, text="Llama", command=lambda: self.switch_model("ollama"))
        self.model2_button.pack(side="left", padx=5)
        
        self.label = ttk.Label(root, text=f"Enter query for {code_type} (e.g., 'Article L432-1' or 'state guarantees'):")
        self.label.pack(pady=5)

        self.query_entry = ttk.Entry(root, width=50)
        self.query_entry.pack(pady=5)
        self.query_entry.bind("<Return>", self.search)

        self.search_button = ttk.Button(root, text="Search", command=self.search)
        self.search_button.pack(pady=5)
        
        self.result_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=15)
        self.result_text.pack(pady=10, padx=10)

        self.exit_button = ttk.Button(root, text="Exit", command=self.exit)
        self.exit_button.pack(pady=5)

        # Loading indicator
        self.loading_label = ttk.Label(root, text="")
        self.loading_label.pack(pady=5)

    async def get_tools(self):
        return await self.mcp_tool.to_tool_list_async()

    async def get_agent(self):
        return FunctionAgent(
            name=f"{self.code_type.replace(' ', '')}Agent",
            description=f"An agent that assists with parsing the French {self.code_type}.",
            tools=self.tools,
            llm=Settings.llm,
            system_prompt=SYSTEM_PROMPT,
        )

    async def handle_user_message(self, message_content: str, verbose: bool = False):
        start_time = time.time()  # Record start time
        tool_outputs = []  # Store tool outputs
        tool_calls = []
        try:
            handler = self.agent.run(message_content, ctx=self.agent_context)
            async for event in handler.stream_events():
                if verbose and isinstance(event, ToolCall):
                    logger.info(f"Calling tool {event.tool_name} with kwargs {event.tool_kwargs}")
                    tool_calls.append({
                        "tool_name": event.tool_name,
                        "tool_kwargs": event.tool_kwargs
                    })
                elif verbose and isinstance(event, ToolCallResult):
                    # Convert ToolOutput to JSON-serializable format
                    try:
                        # Try to parse tool_output as JSON string
                        tool_output = json.loads(str(event.tool_output))
                    except json.JSONDecodeError:
                        # If not JSON, convert to string
                        tool_output = str(event.tool_output)
                    logger.info(f"Tool {event.tool_name} returned {tool_output}")
                    tool_outputs.append({
                        "tool_name": event.tool_name,
                        "tool_output": tool_output
                    })
            response = await handler
            end_time = time.time()  # Record end time
            response_time = end_time - start_time

            # Store interaction in history
            interaction = {
                "time": str(datetime.datetime.now()),
                "prompt": message_content,
                "model": self.model,
                "response_time": response_time,
                "answer": str(response),
                "tool_calls": tool_calls,
                "tool_outputs": tool_outputs
            }
            self.history.append(interaction)

            # Ensure logging directory exists
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

            # Save history to JSON file (append mode)
            try:
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error saving history to file: {e}")

            return str(response)
        except Exception as e:
            logger.error(f"Error handling user message: {e}")
            end_time = time.time()
            response_time = end_time - start_time
            interaction = {
                "time": str(datetime.datetime.now()),
                "prompt": message_content,
                "model": self.model,
                "response_time": response_time,
                "answer": f"Error: {str(e)}",
                "tool_calls": tool_calls,
                "tool_outputs": tool_outputs
            }
            self.history.append(interaction)
            try:
                # Ensure logging directory exists
                os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error saving history to file: {e}")
            return json.dumps({"error": str(e)})
        
    def switch_model(self, input:str):
        if input == "ollama":
            llm = Ollama(model="llama3.2:1b")
        else:
            llm = OpenAI(model="gpt-4o-mini")
        Settings.llm = llm
        self.model = input
        self.tools = self.loop.run_until_complete(self.get_tools())
        self.agent = self.loop.run_until_complete(self.get_agent())
        self.agent_context = Context(self.agent)

        # Provide user feedback
        self.loading_label.config(text=f"Switched to {input}")
        self.root.update()
        logger.info(f"Switched to model: {input}, {Settings.llm}")
        # Clear loading label after a short delay
        self.root.after(2000, lambda: self.loading_label.config(text=""))
        self.model_text.set(f"Current model: {self.model}")

    def search(self, event=None):
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Input Error", "Please enter a query.")
            return

        self.loading_label.config(text="Searching...")
        self.search_button.config(state="disabled")
        self.root.update()

        try:
            response = self.loop.run_until_complete(
                self.handle_user_message(query, verbose=True)
            )
            self.result_text.delete(1.0, tk.END)
            try:
                parsed_response = json.loads(response)
                if "error" in parsed_response:
                    self.result_text.insert(tk.END, f"Error: {parsed_response['error']}\n")
                elif not parsed_response.get("articles"):
                    self.result_text.insert(tk.END, "No articles found matching the query.\n")
                else:
                    self.result_text.insert(tk.END, "Search Results:\n\n")
                    for article in parsed_response["articles"]:
                        self.result_text.insert(tk.END, f"Article {article['article_id']}:\n")
                        # Display available fields, handle missing summary/keywords
                        if "summary" in article:
                            self.result_text.insert(tk.END, f"  Summary: {article['summary']}\n")
                        if "keywords" in article:
                            self.result_text.insert(tk.END, f"  Keywords: {', '.join(article['keywords'])}\n")
                        self.result_text.insert(tk.END, f"  Content: {article['content'][:200]}...\n")
                        if "hierarchy" in article:
                            self.result_text.insert(tk.END, f"  Hierarchy: {article['hierarchy']}\n")
                        if "references" in article:
                            self.result_text.insert(tk.END, f"  References: {', '.join(article['references']) if article['references'] else 'None'}\n")
                        if "referenced_by" in article:
                            self.result_text.insert(tk.END, f"  Referenced By: {', '.join(article['referenced_by']) if article['referenced_by'] else 'None'}\n")
                        self.result_text.insert(tk.END, "\n")
            except json.JSONDecodeError:
                self.result_text.insert(tk.END, f"{response}\n")
        except Exception as e:
            logger.error(f"Search error: {e}")
            messagebox.showerror("Error", f"Search failed: {str(e)}")
        finally:
            self.loading_label.config(text="")
            self.search_button.config(state="normal")

    def exit(self):
        self.root.quit()
        self.root.destroy()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Legal Code MCP Client")
    parser.add_argument(
        "--server_url", type=str, default=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/sse"),
        help="URL of the MCP server"
    )
    parser.add_argument(
        "--code_type", type=str, default="Code des Assurances",
        choices=["Code des Assurances", "Code penal", "Code du travail"],
        help="Type of legal code to query"
    )
    parser.add_argument(
        "--model", type=str, default="ollama",
        choices=["ollama", "gpt"],
        help="Type of LLM to use"
    )
    args = parser.parse_args()

    root = tk.Tk()
    app = CodeHelperApp(root, args.server_url, args.code_type, args.model)
    root.mainloop()

if __name__ == "__main__":
    main()