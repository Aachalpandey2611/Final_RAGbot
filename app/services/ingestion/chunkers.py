from typing import List, Optional

class TextChunker:
    """Interface for text chunking algorithms."""
    def chunk(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        raise NotImplementedError()

class RecursiveCharacterChunker(TextChunker):
    """Splits text recursively using paragraphs, sentences, words, and characters."""
    def __init__(self, separators: Optional[List[str]] = None):
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def chunk(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        if not text:
            return []
            
        chunks = []
        # Find best separator
        separator = self.separators[-1]
        for s in self.separators:
            if s == "":
                separator = s
                break
            if s in text:
                separator = s
                break

        # Split text
        if separator != "":
            splits = text.split(separator)
        else:
            splits = list(text)

        current_doc = []
        current_len = 0

        for part in splits:
            part_len = len(part)
            if current_len + part_len + (len(separator) if current_doc else 0) > chunk_size:
                if current_doc:
                    chunks.append(separator.join(current_doc))
                    # Retain overlap
                    overlap_doc = []
                    overlap_len = 0
                    for p in reversed(current_doc):
                        p_len = len(p)
                        if overlap_len + p_len + (len(separator) if overlap_doc else 0) <= chunk_overlap:
                            overlap_doc.insert(0, p)
                            overlap_len += p_len + len(separator)
                        else:
                            break
                    current_doc = overlap_doc
                    current_len = overlap_len
                
                # If a single part exceeds chunk size, split it recursively or append
                if part_len > chunk_size:
                    sub_splits = self.chunk(part, chunk_size, chunk_overlap)
                    chunks.extend(sub_splits)
                else:
                    current_doc.append(part)
                    current_len += part_len + len(separator)
            else:
                current_doc.append(part)
                current_len += part_len + (len(separator) if len(current_doc) > 1 else 0)

        if current_doc:
            chunks.append(separator.join(current_doc))

        return [c.strip() for c in chunks if c.strip()]
