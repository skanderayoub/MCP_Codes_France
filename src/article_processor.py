import re
from collections import defaultdict
from math import log
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from llama_index.llms.ollama import Ollama

class ArticleProcessor:
    def __init__(self, stop_words, llm_config):
        self.stop_words = stop_words
        self.documents = []
        self.word_doc_freq = defaultdict(int)
        self.llm = Ollama(**llm_config)

    def extract_keywords(self, content, top_n=5):
        words = word_tokenize(content.lower())
        tagged_words = pos_tag(words, lang='eng')
        candidates = [word for word, pos in tagged_words if pos in ('NN', 'NNS', 'NNP', 'NNPS', 'JJ', 'JJR', 'JJS') and word not in self.stop_words and len(word) > 2]

        word_freq = defaultdict(int)
        for word in candidates:
            word_freq[word] += 1

        tfidf_scores = {}
        total_docs = len(self.documents) if self.documents else 1
        for word, freq in word_freq.items():
            tf = freq / max(len(candidates), 1)
            idf = log(total_docs / (self.word_doc_freq[word] + 1)) + 1
            tfidf_scores[word] = tf * idf

        sorted_keywords = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)
        return [word for word, score in sorted_keywords[:top_n]]

    def generate_summary(self, content):
        prompt = (
            "Provide a concise summary of the following French code article in about 100 characters in French. "
            "Focus on key legal obligations and procedures, using precise legal terminology:\n\n"
            f"{content}"
        )
        response = self.llm.complete(prompt)
        return str(response).strip()

    def process_article(self, article_id, content, curr_hierarchy, reference_graph, all_articles, content_patterns):
        content = re.sub(r"\n", " ", content.strip())
        words = set(word_tokenize(content.lower()))
        for word in words:
            self.word_doc_freq[word] += 1
        self.documents.append(content)

        references = re.findall(r"\b(?:[A-Z]\.\s*)?\d{3}-\d+(?:-\d+)*\b", content)
        for ref in references:
            reference_graph["Article " + re.sub(". ", "", ref)].append(article_id)

        for pattern in content_patterns:
            match = re.search(pattern, content)
            if match:
                content = content[:match.start()]
                break

        article = {
            "article_id": article_id,
            "content": content.strip(),
            "hierarchy": curr_hierarchy.copy(),
            "references": ["Article " + re.sub(". ", "", r) for r in references],
            "referenced_by": [],
            "summary": "", # self.generate_summary(content),
            "keywords": self.extract_keywords(content),
            "page_number": None
        }
        all_articles.add(article_id)
        return article