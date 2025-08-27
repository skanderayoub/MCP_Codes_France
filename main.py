import json
import nltk
import os
from src.code_processor import CodeProcessor
import argparse

try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('averaged_perceptron_tagger')

def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    # Validate required config keys
    required_keys = [
        "pdf_path", "txt_path", "json_path", "cleaning_patterns", 
        "hierarchy_patterns", "level_keys", "article_pattern", 
        "content_patterns", "stop_words", "llm_config"
    ]
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required config key: {key}")
    return config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process French legal code PDFs")
    parser.add_argument("--config", default="configs/code_assurances.json", 
                        help="Path to configuration file")
    args = parser.parse_args()

    config = load_config(args.config)
    processor = CodeProcessor(config)
    processor.process()