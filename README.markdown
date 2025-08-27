# Legal Code Processor

## Overview
This project is designed to process French legal code documents, such as the *Code des Assurances* and *Code pénal*, extracted from PDF files. The system extracts, cleans, and structures legal articles into a JSON format, capturing their hierarchy, summaries, keywords, and cross-references. It includes a modular processing pipeline and a client-server architecture using MCP (message-passing client/server) for querying processed data interactively via a Tkinter-based UI. The project is built to be extensible, allowing easy adaptation for additional legal codes by modifying configuration files.

## Features
- **PDF Processing**: Extracts text from legal code PDFs and saves it for further processing.
- **Text Cleaning**: Removes irrelevant headers, footers, and metadata using regex-based patterns.
- **Hierarchy Parsing**: Identifies structural elements (e.g., Partie, Livre, Titre, Chapitre) to organize articles hierarchically.
- **Article Processing**: Generates summaries and extracts keywords using TF-IDF and an LLM (Ollama with llama3.2:1b).
- **Cross-Reference Tracking**: Captures references between articles and builds a reference graph.
- **Client-Server Architecture**: Provides a server (`FastMCP`) for querying processed data and a client with a Tkinter UI for user interaction.
- **Configurable**: Supports multiple legal codes via JSON configuration files specifying file paths and regex patterns.
- **Extensible**: Easily adaptable for new legal codes by adding new configuration files.

## Project Structure
```
project/
├── src/                    # Core processing logic
│   ├── pdf_text_extractor.py  # Extracts text from PDFs
│   ├── text_cleaner.py        # Cleans text using regex patterns
│   ├── hierarchy_parser.py    # Parses document hierarchy
│   ├── article_processor.py   # Processes articles (summaries, keywords)
│   ├── code_processor.py      # Orchestrates the processing pipeline
├── services/               # MCP client and server implementation
│   ├── client.py           # Tkinter-based UI for querying legal codes
│   ├── server.py           # MCP server for handling search queries
├── configs/                # Configuration files for different legal codes
│   ├── code_assurances.json  # Config for Code des Assurances
│   ├── code_penal.json       # Config for Code pénal
│   ├── code_de_la_route.json # Config for Code de la route
├── data/                   # Input and output files
│   ├── input/              # Input PDF files
│   │   ├── code_assurances.pdf  
│   │   ├── code_penal.pdf  
│   ├── output/             # Processed text and JSON files
├── tests/                   # TO COMPLETE
├── .env                    # Environment variables (e.g., LLM endpoint, server URL)
├── main.py                 # Entry point for processing PDFs
├── README.md               # Project documentation
├── requirements.txt        # MISSING
```

## Prerequisites
- Python 3.8 or higher
- pip for installing dependencies
- Input PDFs (e.g., `code_assurances.pdf`, `code_penal.pdf`) placed in `data/input/`
- Optional: Access to an LLM server (e.g., Ollama running locally)

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/skanderayoub/MCP_Codes_France
   cd MCP_Codes_France
   ```
2. **Install Dependencies MISSING**:
   ```bash
   pip install -r requirements.txt
   ```
   Dependencies include `pypdf`, `nltk`, `llama-index`, `tqdm`, `python-dotenv`, and `mcp[cli]`.
3. **Configure Environment Variables**:
   Edit `.env` to set:
   - `MCP_SERVER_URL`: MCP server URL (e.g., `http://127.0.0.1:8000/sse`)
   - `JSON_PATH`: Default JSON file path (e.g., `data/output/code_assurances.json`)
   - `LOG_LEVEL`: Logging level (e.g., `INFO`)
   - `OPENAI_API_KEY`: Your OPENAI Api Key if you want to use OpenAi models
4. **Place Input PDFs**:
   Copy legal code PDFs to `data/input/` (e.g., `code_assurances.pdf`, `code_penal.pdf`).

## Usage
### Processing a Legal Code
Run the processing pipeline to convert a PDF into structured JSON:
```bash
python main.py --config configs/code_assurances.json
```
- The `--config` argument specifies the configuration file for the legal code.
- Outputs are saved to `data/output/` (e.g., `code_assurances_raw.txt`, `code_assurances.json`).

### Running the MCP Server
Start the server to handle queries for a specific legal code:
```bash
python services/server.py --json_path data/output/code_assurances.json --server_type sse
```
- `--json_path`: Path to the processed JSON file.
- `--server_type`: Either `sse` (Server-Sent Events) or `stdio` (standard input/output).

### Running the Client UI
Launch the Tkinter-based client to query the legal code:
```bash
python services/client.py --code_type "Code des Assurances" --server_url http://127.0.0.1:8000/sse --model ollama
```
- `--code_type`: Specifies the legal code (e.g., "Code des Assurances", "Code pénal"), defaults to **"Code pénal"**.
- `--server_url`: URL of the running MCP server, defaults to **http://127.0.0.1:8000/sse**.
- `--model`: ["ollama" or "gpt"] Specifies the model to use, default to **ollama**.
- The UI allows entering queries (e.g., "Article L432-1" or "state guarantees") and displays results with article IDs, summaries, keywords, and content excerpts.


### Example Workflow
1. Process the *Code des Assurances*:
   ```bash
   python main.py --config configs/code_assurances.json
   ```
2. Start the server with the processed data:
   ```bash
   python services/server.py --json_path data/output/code_assurances.json
   ```
3. Open the client UI:
   ```bash
   python services/client.py --code_type "Code des Assurances"
   ```
4. Enter a query in the UI (e.g., "Article L121-1" or "contrat") to retrieve matching articles.

## Configuration
- **Configuration Files**: Located in `configs/`, each file (e.g., `code_assurances.json`) specifies:
  - File paths (`pdf_path`, `txt_path`, `json_path`)
  - Regex patterns for cleaning, hierarchy parsing, and article splitting
  - Stop words for keyword extraction
  - LLM configuration (e.g., model, temperature)
- **Adding a New Legal Code**:
  1. Create a new JSON config file in `configs/` (e.g., `code_new.json`).
  2. Update regex patterns and file paths as needed.
  3. Place the corresponding PDF in `data/input/`.
  4. Run `main.py` with the new config and update the server `--json_path`.