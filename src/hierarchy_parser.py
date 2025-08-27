import re
from collections import defaultdict

class HierarchyParser:
    def __init__(self, hierarchy_patterns, level_keys, article_pattern):
        self.patterns = hierarchy_patterns
        self.level_keys = level_keys
        self.article_pattern = article_pattern

    def split_by_articles(self, text):
        articles_splits = re.split(self.article_pattern, text, flags=re.M)
        return articles_splits[1::2], articles_splits[2::2], articles_splits[0::2]

    def detect_hierarchy(self, preceding_text, prev_hierarchy):
        curr_hierarchy = prev_hierarchy.copy()
        for idx, pattern in enumerate(reversed(self.patterns)):
            splt = re.split(pattern, preceding_text, flags=re.M)
            if len(splt) > 1:
                new_val = f"{splt[-2].strip()} {splt[-1].strip()}".strip()
                preceding_text = "".join(s for s in splt[:-2])
                # print(new_val)
                curr_idx = len(self.level_keys) - idx - 1
                if curr_hierarchy[self.level_keys[curr_idx]] != new_val:
                    curr_hierarchy[self.level_keys[curr_idx]] = new_val
                    for lower_idx in range(curr_idx + 1, len(self.level_keys)):
                        if (curr_hierarchy[self.level_keys[lower_idx]]) == prev_hierarchy[self.level_keys[lower_idx]]:
                            curr_hierarchy[self.level_keys[lower_idx]] = ""
        return curr_hierarchy