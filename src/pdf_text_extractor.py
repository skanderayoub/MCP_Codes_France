import os
from pypdf import PdfReader

class PdfTextExtractor:
    def __init__(self, pdf_path, output_txt_path):
        self.pdf_path = pdf_path
        self.output_txt_path = output_txt_path

    def extract_text(self):
        if not os.path.exists(self.output_txt_path):
            reader = PdfReader(self.pdf_path)
            text = ""
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
            with open(self.output_txt_path, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            with open(self.output_txt_path, "r", encoding="utf-8") as f:
                text = f.read()
        return text