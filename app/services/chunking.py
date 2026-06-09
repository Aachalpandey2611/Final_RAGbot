import re
from typing import List

from app.services.ingestion.chunkers import RecursiveCharacterChunker


class AdaptiveChunkingEngine:
    """Dynamic chunking engine that selects specialized chunkers
    based on document type and falls back to a recursive chunker.
    Supported doc_type values: 'policy', 'manual', 'table', 'code', or 'auto'.
    """

    def __init__(self, default_chunk_size: int = 1200, default_overlap: int = 300):
        self.default_chunk_size = default_chunk_size
        self.default_overlap = default_overlap
        self._fallback = RecursiveCharacterChunker()

    def chunk(self, text: str, doc_type: str = "auto", chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        if chunk_overlap is None:
            chunk_overlap = self.default_overlap

        if not text or not text.strip():
            return []

        doc_type = (doc_type or "auto").lower()

        if doc_type == "policy":
            chunks = self._section_chunk(text)
        elif doc_type == "manual":
            chunks = self._heading_chunk(text)
        elif doc_type == "table":
            chunks = self._table_chunk(text)
        elif doc_type == "code":
            chunks = self._function_chunk(text)
        else:
            # Auto-detect by heuristics
            if self._looks_like_code(text):
                chunks = self._function_chunk(text)
            elif self._contains_table(text):
                chunks = self._table_chunk(text)
            elif self._has_marked_headings(text):
                chunks = self._heading_chunk(text)
            else:
                chunks = self._section_chunk(text)

        # Merge highly related logic chains to prevent splitting
        chunks = self._preserve_logic_chains(chunks)

        # Ensure chunks are not too large — further split by fallback
        final = []
        for c in chunks:
            if len(c) > chunk_size:
                # If a block is too large, we must split it, but we try to keep logic lines grouped
                sub_chunks = self._fallback.chunk(c, chunk_size, chunk_overlap)
                final.extend(self._preserve_logic_chains(sub_chunks))
            else:
                final.append(c.strip())

        return [c for c in final if c]

    def _preserve_logic_chains(self, chunks: List[str]) -> List[str]:
        """Merge adjacent chunks if they break a conditional logic flow."""
        if not chunks:
            return []
            
        merged = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = merged[-1]
            curr = chunks[i]
            
            # Detect if current chunk is a continuation of a logic branch
            is_continuation = bool(re.search(r"^\s*(->|=>|accountType|Route|Otherwise|Else|Then|Elif|Z\d+|Collection Agency)\b", curr, re.IGNORECASE))
            
            # Detect if prev chunk ends with an incomplete logic
            prev_incomplete = bool(re.search(r"(If|Else|->|=>|=|Agency|Type|route to|Z\d+)\s*$", prev, re.IGNORECASE))
            
            if is_continuation or prev_incomplete:
                merged[-1] = prev + "\n" + curr
            else:
                merged.append(curr)
                
        return merged

    # --- Heuristics / detectors ---
    def _looks_like_code(self, text: str) -> bool:
        return bool(re.search(r"^\s*(def |class |#include|package\s)", text, re.MULTILINE))

    def _contains_table(self, text: str) -> bool:
        if re.search(r"^\s*\|.+\|", text, re.MULTILINE):
            return True
        lines = [l for l in text.splitlines() if l.strip()]
        if len(lines) >= 3:
            commas = sum(1 for l in lines[:5] if "," in l)
            pipes = sum(1 for l in lines[:5] if "|" in l)
            if commas >= 2 or pipes >= 2:
                return True
        return False

    def _has_marked_headings(self, text: str) -> bool:
        return bool(re.search(r"^#{1,6}\s+|^Chapter\s+\d+", text, re.MULTILINE))

    # --- Chunkers ---
    def _section_chunk(self, text: str) -> List[str]:
        pattern = re.compile(r"(?m)^(?:Section\s+\d+|\d+(?:\.\d+)*\s+[-–:]?)\s*", re.IGNORECASE)
        indices = [m.start() for m in pattern.finditer(text)]
        if not indices:
            return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

        chunks = []
        indices.append(len(text))
        for i in range(len(indices) - 1):
            chunks.append(text[indices[i]:indices[i + 1]].strip())
        return chunks

    def _heading_chunk(self, text: str) -> List[str]:
        pattern = re.compile(r"(?m)^(#{1,6}\s+.+|Chapter\s+\d+[:.-]?\s*.+)$", re.IGNORECASE)
        matches = list(pattern.finditer(text))
        if not matches:
            return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

        chunks = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chunks.append(text[start:end].strip())
        return chunks

    def _table_chunk(self, text: str) -> List[str]:
        lines = text.splitlines()
        chunks = []
        buffer = []

        def flush():
            if buffer:
                chunks.append("\n".join(buffer).strip())
                buffer.clear()

        for line in lines:
            if "|" in line or re.search(r",\s*\w+", line):
                buffer.append(line)
            else:
                flush()
        flush()

        if not chunks:
            rows = [l for l in lines if l.strip()]
            if len(rows) >= 3:
                chunks.append("\n".join(rows))

        return chunks or [text]

    def _function_chunk(self, text: str) -> List[str]:
        pattern = re.compile(r"(?m)^(\s*(def|class)\s+\w+)\b")
        matches = list(pattern.finditer(text))
        if not matches:
            return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

        indices = [m.start() for m in matches]
        indices.append(len(text))
        chunks = []
        for i in range(len(indices) - 1):
            chunks.append(text[indices[i]:indices[i + 1]].strip())
        return chunks

__all__ = ["AdaptiveChunkingEngine"]
