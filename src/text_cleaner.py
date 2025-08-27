import re

class TextCleaner:
    def __init__(self, cleaning_patterns):
        self.cleaning_patterns = cleaning_patterns

    def clean_text(self, text):
        for pattern in self.cleaning_patterns:
            text = re.sub(pattern, '', text)
        return text.strip()