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

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

SYSTEM_PROMPT = """\
You are an AI assistant specialized in analyzing and extracting information from French legal codes (e.g., Code des Assurances, Code pénal). Your primary task is to parse legal text, identify key concepts, and provide accurate, concise, and contextually relevant responses.

Follow these guidelines:
1. **Understand Legal Context**: Interpret the input in the context of French law, focusing on domain-specific terminology (e.g., 'assurance,' 'contrat,' 'sinistre,' 'indemnisation,' 'responsabilité').
2. **Extract Key Information**: Prioritize extracting relevant keywords, provisions, or concepts using tools to query the provided database.
3. **Handle French Language**: Account for French linguistic nuances, including proper nouns, legal jargon, and multi-word expressions (e.g., 'responsabilité civile').
4. **Provide Structured Responses**: Summarize findings clearly, citing specific articles or sections (e.g., 'Article L121-1'). If clarification is needed, ask the user for additional context.
5. **Use Tools Effectively**: Leverage available tools to query the legal code database, ensuring responses are grounded in the source text.

Respond in a professional and precise manner, avoiding irrelevant details. If the input is ambiguous, request clarification to ensure accuracy.
"""

class CodeHelperApp:
    def __init__(self, root, server_url: str, code_type: str, model: str):
        self.root = root
        self.root.title(f"{code_type} MCP Assistant")
        self.root.geometry("600x400")
        self.server_url = server_url
        self.code_type = code_type

        # Setup LLM
        if model == "ollama":
            llm = Ollama(model="llama3.2:1b")
        else:
            llm = OpenAI(model="gpt-4o-mini")
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
        try:
            handler = self.agent.run(message_content, ctx=self.agent_context)
            async for event in handler.stream_events():
                if verbose and isinstance(event, ToolCall):
                    logger.info(f"Calling tool {event.tool_name} with kwargs {event.tool_kwargs}")
                elif verbose and isinstance(event, ToolCallResult):
                    logger.info(f"Tool {event.tool_name} returned {event.tool_output}")
            response = await handler
            return str(response)
        except Exception as e:
            logger.error(f"Error handling user message: {e}")
            return json.dumps({"error": str(e)})

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
                        self.result_text.insert(tk.END, f"  Summary: {article['summary']}\n")
                        self.result_text.insert(tk.END, f"  Keywords: {', '.join(article['keywords'])}\n")
                        self.result_text.insert(tk.END, f"  Content: {article['content'][:200]}...\n\n")
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
        choices=["Code des Assurances", "Code penal", "Code de la route"],
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