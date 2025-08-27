import json
from collections import defaultdict
from tqdm import tqdm
from .pdf_text_extractor import PdfTextExtractor
from .text_cleaner import TextCleaner
from .hierarchy_parser import HierarchyParser
from .article_processor import ArticleProcessor

class CodeProcessor:
    def __init__(self, config):
        self.pdf_path = config["pdf_path"]
        self.txt_path = config["txt_path"]
        self.json_path = config["json_path"]
        self.extractor = PdfTextExtractor(self.pdf_path, self.txt_path)
        self.cleaner = TextCleaner(config["cleaning_patterns"])
        self.parser = HierarchyParser(
            config["hierarchy_patterns"],
            config["level_keys"],
            config["article_pattern"]
        )
        self.article_processor = ArticleProcessor(
            config["stop_words"],
            config["llm_config"]
        )
        # self.hierarchy_tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))))
        def tree():
            return defaultdict(tree)

        self.hierarchy_tree = tree()
        self.articles_list = []
        self.reference_graph = defaultdict(list)
        self.all_articles = set()
        self.content_patterns = config["content_patterns"]

    def process(self):
        text = self.extractor.extract_text()
        text = self.cleaner.clean_text(text)
        
        articles_id, articles_content, preceding_texts = self.parser.split_by_articles(text)
        print(f"Number of articles: {len(articles_id)}")

        prev_hierarchy = {lvl: "" for lvl in self.parser.level_keys}
        for i, article_id in tqdm(enumerate(articles_id), desc="Processing articles"):
            preceding_text = preceding_texts[i] if i < len(preceding_texts) else ""
            curr_hierarchy = self.parser.detect_hierarchy(preceding_text, prev_hierarchy)
            
            article = self.article_processor.process_article(
                article_id, articles_content[i], curr_hierarchy, 
                self.reference_graph, self.all_articles, self.content_patterns
            )
            self.articles_list.append(article)

            node = self.hierarchy_tree
            for lvl in self.parser.level_keys[:-1]:
                if curr_hierarchy[lvl]:
                    node = node[curr_hierarchy[lvl]]
            node["articles"] = node.get("articles", []) + [article_id]

            prev_hierarchy = curr_hierarchy.copy()

        for article in self.articles_list:
            article["referenced_by"] = self.reference_graph.get(article["article_id"], [])

        output = {
            "articles": self.articles_list,
            "hierarchy_tree": dict(self.hierarchy_tree)
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"Data saved to {self.json_path}")