import argparse
import json
import logging
import os
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

class CodeServer:
    def __init__(self, json_path: str):
        self.mcp = FastMCP("Legal-Code-Server")
        self.code_data = self._load_code_data(json_path)
        
    def _load_code_data(self, json_path: str) -> Dict:
        """Load JSON data from the specified path."""
        try:
            if not os.path.exists(json_path):
                logger.error(f"JSON file not found: {json_path}")
                raise FileNotFoundError(f"JSON file not found: {json_path}")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Successfully loaded JSON data from {json_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading JSON data: {e}")
            raise

    def search_code(self, query: str, max_results: int = 10) -> str:
        """Search legal code articles for matches to the query.

        Args:
            query (str): The search query (article ID, keyword, or phrase).
            max_results (int): Maximum number of results to return.

        Returns:
            str: JSON string containing matching articles.
        """
        results = []
        query_lower = query.lower().strip()
        if not query_lower:
            logger.warning("Empty query received")
            return json.dumps({"articles": [], "error": "Empty query"})

        for article in self.code_data["articles"]:
            # Match article ID, content, keywords, or summary
            if (query_lower == article["article_id"].lower() or
                article["article_id"].lower() in query_lower or
                query_lower in article["article_id"].lower() or
                query_lower in article["content"].lower()):
                results.append({
                    "article_id": article["article_id"],
                    "content": article["content"],
                    "hierarchy": article["hierarchy"],
                    "references": article["references"],
                    "referenced_by": article["referenced_by"],
                })
                if len(results) >= max_results:
                    break
        
        logger.info(f"Found {len(results)} articles for query: {query}")
        return json.dumps({"articles": results})

    def register_tools(self):
        """Register tools with MCP."""
        @self.mcp.tool()
        def search_code(query: str, max_results: int = 10) -> str:
            return self.search_code(query, max_results)

    def run(self, server_type: str):
        """Run the MCP server."""
        logger.info(f"Starting server with type: {server_type}")
        self.register_tools()
        self.mcp.run(server_type)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Legal Code MCP Server")
    parser.add_argument(
        "--server_type", type=str, default="sse", choices=["sse", "stdio"],
        help="Server type (sse or stdio)"
    )
    parser.add_argument(
        "--json_path", type=str, default=os.getenv("JSON_PATH", "data/output/code_assurances.json"),
        help="Path to JSON data file"
    )
    args = parser.parse_args()

    server = CodeServer(args.json_path)
    server.run(args.server_type)