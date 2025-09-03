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
            query (str): The search query (article ID).
            max_results (int): Maximum number of results to return.

        Returns:
            str: JSON string containing matching articles.
        """
        results = []
        query_lower = query.lower().strip()
        if not query_lower:
            logger.warning("Empty query received")
            return json.dumps({"articles": [], "error": "Empty query"})
        found_ids = []
        for article in self.code_data["articles"]:
            # Match article ID, content, keywords, or summary
            if (query_lower == article["article_id"].lower() or
                article["article_id"].lower() in query_lower or
                query_lower in article["article_id"].lower() or
                query_lower in article["content"].lower()):
                if article["article_id"] not in found_ids:
                    results.append({
                        "article_id": article["article_id"],
                        "content": article["content"],
                        "hierarchy": article["hierarchy"],
                        "references": article["references"],
                        "referenced_by": article["referenced_by"],
                    })
                    found_ids.append(article["article_id"])
                if len(results) >= max_results:
                    break
        
        logger.info(f"Found {len(results)} articles for query: {query}")
        return json.dumps({"articles": results})

    def get_article_by_id(self, article_id: str) -> str:
        """Retrieve a specific article by its exact ID.

        Args:
            article_id (str): The exact article ID to retrieve.

        Returns:
            str: JSON string with the full article details or error if not found.
        """
        if not article_id.startswith("Article"):
            article_id = "Article " + article_id
        try:
            article_id_lower = article_id.lower().strip()
            for article in self.code_data["articles"]:
                if article["article_id"].lower() == article_id_lower:
                    return json.dumps({"article": article})
            logger.warning(f"Article not found: {article_id}")
            return json.dumps({"article": None, "error": "Article not found"})
        except Exception as e:
            logger.error(f"Error in get_article_by_id: {e}")
            return json.dumps({"error": str(e)})

    def search_by_keywords(self, keywords: List[str], match_type: str = "any", max_results: int = 10) -> str:
        """Search articles by matching one or more keywords.

        Args:
            keywords (List[str]): List of keywords to match.
            match_type (str): "any" or "all" for matching logic (default "any").
            max_results (int): Maximum number of results to return (default 10).

        Returns:
            str: JSON string with matching articles.
        """
        try:
            if not keywords:
                logger.warning("Empty keywords list received")
                return json.dumps({"articles": [], "error": "Empty keywords"})
            keywords_lower = [kw.lower().strip() for kw in keywords]
            results = []
            for article in self.code_data["articles"]:
                article_keywords_lower = [kw.lower() for kw in article.get("keywords", [])]
                content_lower = article["content"].lower()
                if match_type == "all":
                    if all(kw in article_keywords_lower or kw in content_lower for kw in keywords_lower):
                        results.append(article)
                else:  # "any"
                    if any(kw in article_keywords_lower or kw in content_lower for kw in keywords_lower):
                        results.append(article)
                if len(results) >= max_results:
                    break
            logger.info(f"Found {len(results)} articles for keywords: {keywords}")
            return json.dumps({"articles": results})
        except Exception as e:
            logger.error(f"Error in search_by_keywords: {e}")
            return json.dumps({"error": str(e)})

    def get_hierarchy_articles(self, hierarchy_path: str, max_results: int = 20) -> str:
        """Retrieve all articles within a specific hierarchy level.

        Args:
            hierarchy_path (str): Path in the hierarchy (e.g., "Partie législative/Livre Ier : Le contrat").
            max_results (int): Maximum number of results to return (default 20).

        Returns:
            str: JSON string with articles in that section.
        """
        try:
            path_parts = hierarchy_path.split('/')
            current_level = self.code_data.get("hierarchy_tree", {})
            for part in path_parts:
                if part in current_level:
                    current_level = current_level[part]
                else:
                    logger.warning(f"Hierarchy path not found: {hierarchy_path}")
                    return json.dumps({"articles": [], "error": "Hierarchy path not found"})
            article_ids = current_level.get("articles", [])
            results = [art for art in self.code_data["articles"] if art["article_id"] in article_ids][:max_results]
            logger.info(f"Found {len(results)} articles in hierarchy: {hierarchy_path}")
            return json.dumps({"articles": results})
        except Exception as e:
            logger.error(f"Error in get_hierarchy_articles: {e}")
            return json.dumps({"error": str(e)})

    def get_related_articles(self, article_id: str, direction: str = "both") -> str:
        """Fetch articles that reference or are referenced by a given article ID.

        Args:
            article_id (str): The article ID to find relations for.
            direction (str): "references", "referenced_by", or "both" (default "both").

        Returns:
            str: JSON string with related articles.
        """
        try:
            if not article_id.startswith("Article"):
                article_id = "Article " + article_id
            article_id_lower = article_id.lower().strip()
            target_article = next((art for art in self.code_data["articles"] if art["article_id"].lower() == article_id_lower), None)
            if not target_article:
                logger.warning(f"Article not found: {article_id}")
                return json.dumps({"related_articles": [], "error": "Article not found"})
            related_ids = set()
            if direction in ["references", "both"]:
                related_ids.update(target_article.get("references", []))
            if direction in ["referenced_by", "both"]:
                related_ids.update(target_article.get("referenced_by", []))
            related_articles = [art for art in self.code_data["articles"] if art["article_id"] in related_ids]
            logger.info(f"Found {len(related_articles)} related articles for {article_id}")
            return json.dumps({"related_articles": related_articles})
        except Exception as e:
            logger.error(f"Error in get_related_articles: {e}")
            return json.dumps({"error": str(e)})

    def get_summary_or_keywords(self, query: str, max_results: int = 5) -> str:
        """Extract summary and/or keywords for matching articles.

        Args:
            query (str): Article ID or search term.
            max_results (int): Maximum number of results to return (default 5).

        Returns:
            str: JSON string with summaries/keywords per article.
        """
        try:
            query_lower = query.lower().strip()
            if not query_lower:
                logger.warning("Empty query received")
                return json.dumps({"summaries": [], "error": "Empty query"})
            results = []
            for article in self.code_data["articles"]:
                if query_lower in article["article_id"].lower() or query_lower in article["content"].lower():
                    summary = article.get("summary") or article["content"][:200] + "..."
                    keywords = article.get("keywords", [])
                    results.append({
                        "article_id": article["article_id"],
                        "summary": summary,
                        "keywords": keywords
                    })
                    if len(results) >= max_results:
                        break
            logger.info(f"Extracted summaries/keywords for {len(results)} articles matching: {query}")
            return json.dumps({"summaries": results})
        except Exception as e:
            logger.error(f"Error in get_summary_or_keywords: {e}")
            return json.dumps({"error": str(e)})

    def traverse_hierarchy_tree(self, start_path: str = "", depth: int = 3) -> str:
        """Retrieve a subtree or full hierarchy_tree.

        Args:
            start_path (str): Starting path in the hierarchy (default "" for full tree).
            depth (int): Maximum depth to traverse (default 3).

        Returns:
            str: JSON string of the (sub)tree.
        """
        try:
            import copy
            tree = copy.deepcopy(self.code_data.get("hierarchy_tree", {}))
            if start_path:
                path_parts = start_path.split('/')
                for part in path_parts:
                    if part in tree:
                        tree = tree[part]
                    else:
                        logger.warning(f"Path not found: {start_path}")
                        return json.dumps({"tree": {}, "error": "Path not found"})
            def limit_depth(node, current_depth):
                if current_depth >= depth:
                    return {k: {} if isinstance(v, dict) else v for k, v in node.items() if not isinstance(v, dict)}
                return {k: limit_depth(v, current_depth + 1) if isinstance(v, dict) else v for k, v in node.items()}
            limited_tree = limit_depth(tree, 0)
            logger.info(f"Traversed hierarchy tree from: {start_path}")
            return json.dumps({"tree": limited_tree})
        except Exception as e:
            logger.error(f"Error in traverse_hierarchy_tree: {e}")
            return json.dumps({"error": str(e)})

    def register_tools(self):
        """Register tools with MCP."""
        @self.mcp.tool()
        def search_code(query: str, max_results: int = 10) -> str:
            return self.search_code(query, max_results)
        
        @self.mcp.tool()
        def get_article_by_id(article_id: str) -> str:
            return self.get_article_by_id(article_id)
        
        @self.mcp.tool()
        def search_by_keywords(keywords: List[str], match_type: str = "any", max_results: int = 10) -> str:
            return self.search_by_keywords(keywords, match_type, max_results)
        
        @self.mcp.tool()
        def get_hierarchy_articles(hierarchy_path: str, max_results: int = 20) -> str:
            return self.get_hierarchy_articles(hierarchy_path, max_results)
        
        @self.mcp.tool()
        def get_related_articles(article_id: str, direction: str = "both") -> str:
            return self.get_related_articles(article_id, direction)
        
        @self.mcp.tool()
        def get_summary_or_keywords(query: str, max_results: int = 5) -> str:
            return self.get_summary_or_keywords(query, max_results)
        
        @self.mcp.tool()
        def traverse_hierarchy_tree(start_path: str = "", depth: int = 3) -> str:
            return self.traverse_hierarchy_tree(start_path, depth)

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