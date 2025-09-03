Below are query examples for each MCP tool in the updated `CodeServer` class. These examples are designed to test the tools' functionality in the context of insurance workers, lawyers, or legal professionals using the Code des Assurances or Code Penal. Each query is a user input that could be entered in the `client.py` UI (e.g., in the `query_entry` field) to trigger the corresponding tool via the agent's logic. The examples reflect realistic use cases, such as legal research, case preparation, or compliance checks, and are tailored to the data structure provided (articles with fields like `article_id`, `content`, `hierarchy`, `references`, `referenced_by`, `summary`, and `keywords`, plus a `hierarchy_tree`).

### 1. **search_code**
   - **Purpose**: Searches articles by matching a query against article IDs or content.
   - **Query Example**:  
     `"Find articles about state guarantees in the Code des Assurances"`  
     - **Why**: Tests partial matching in content (e.g., searching for "state guarantees" might match articles mentioning terms like "garanties de l'État"). Useful for broad searches when the exact article ID is unknown.
   - **Expected Behavior**: Returns up to 10 articles (default `max_results`) where the query appears in the `article_id` or `content`, including fields like `hierarchy`, `references`, and `referenced_by`.

### 2. **get_article_by_id**
   - **Purpose**: Retrieves a specific article by its exact ID.
   - **Query Example**:  
     `"What is the content of Article L121-1 in the Code des Assurances?"`  
     - **Why**: Tests precise lookup of a known article, common when a lawyer needs the exact text of a cited article for a contract dispute.
   - **Expected Behavior**: Returns the full article details (e.g., `content`, `hierarchy`, etc.) for `Article L121-1` or an error if not found.

### 3. **search_by_keywords**
   - **Purpose**: Searches articles by matching one or more keywords in the `keywords` field or `content`, with "any" or "all" logic.
   - **Query Example**:  
     `"Search for articles with keywords 'responsabilité civile' and 'indemnisation' in the Code des Assurances"`  
     - **Why**: Tests keyword-based search for liability claim analysis, common in insurance cases. Using multiple keywords tests the `match_type` logic (e.g., "all" ensures both terms are present).
   - **Expected Behavior**: Returns articles where both keywords appear (if `match_type="all"`) or at least one appears (if `match_type="any"`), up to 10 results.

### 4. **get_hierarchy_articles**
   - **Purpose**: Retrieves all articles within a specific hierarchy level (e.g., livre, titre, chapitre).
   - **Query Example**:  
     `"List all articles under Livre Ier : Le contrat in the Code des Assurances"`  
     - **Why**: Tests navigation of the `hierarchy_tree` to explore a specific section, useful for reviewing all contract-related provisions in one go.
   - **Expected Behavior**: Returns up to 20 articles (default `max_results`) listed under the specified hierarchy path (e.g., "Partie législative/Livre Ier : Le contrat").

### 5. **get_related_articles**
   - **Purpose**: Fetches articles that reference or are referenced by a given article ID.
   - **Query Example**:  
     `"Which articles reference or are referenced by Article L432-1 in the Code Penal?"`  
     - **Why**: Tests relationship tracing, critical for building a defense strategy or understanding legal dependencies in a case.
   - **Expected Behavior**: Returns articles listed in the `references` and/or `referenced_by` fields of `Article L432-1`, depending on the `direction` parameter ("both" by default).

### 6. **get_summary_or_keywords**
   - **Purpose**: Extracts summaries and/or keywords for articles matching a query.
   - **Query Example**:  
     `"Provide summaries and keywords for articles about 'sinistre' in the Code des Assurances"`  
     - **Why**: Tests summary/keyword extraction for preparing reports (e.g., insurance payout analysis), especially when concise overviews are needed.
   - **Expected Behavior**: Returns up to 5 articles (default `max_results`) with their `summary` (or truncated `content` if no summary) and `keywords` where the query term "sinistre" appears.

### 7. **traverse_hierarchy_tree**
   - **Purpose**: Retrieves a subtree or full hierarchy_tree starting from a given path.
   - **Query Example**:  
     `"Show the hierarchy structure under Titre Ier : Règles communes in the Code des Assurances"`  
     - **Why**: Tests structural exploration, useful for understanding the organization of rules (e.g., for damage and personal insurance) before diving into specific articles.
   - **Expected Behavior**: Returns a JSON tree starting from "Partie législative/Livre Ier : Le contrat/Titre Ier : Règles communes", limited to a depth of 3 (default), showing sublevels and associated articles.

### Notes for Testing
- **How to Test**: Run the server (`server.py`) with `python server.py --json_path data/output/code_assurances.json`, then run the client (`client.py`) with `python client.py --code_type "Code des Assurances"`. Enter each query in the UI's text field and observe the output in the `result_text` widget.
- **Validation**: Check the JSON response in the UI or logs (`./logging/interaction_history.json`) to ensure the correct articles, fields, or tree structure are returned. Verify that error messages appear for invalid queries (e.g., non-existent article IDs).
- **Edge Cases**: Test empty queries, invalid article IDs, or deep hierarchy paths to ensure robust error handling (e.g., `{"error": "Article not found"}` or `{"error": "Hierarchy path not found"}`).
- **Realism**: These queries mimic real-world tasks, like looking up specific articles for a court case, analyzing liability terms, or mapping code structure for training purposes.