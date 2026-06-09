import math
import re
from typing import List, Dict, Tuple
from app.models.document import DocumentChunk

class BM25:
    """
    Standard BM25 implementation for ranking document chunks based on a text query.
    """
    def __init__(self, corpus: List[DocumentChunk], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)
        
        self.doc_lengths = []
        self.doc_term_freqs = []  # List[Dict[str, int]]
        self.nd = {}  # Dict[str, int] (DF of terms)
        
        self._initialize()

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize the input text by converting it to lowercase and extracting alphanumeric tokens.
        """
        if not text:
            return []
        return re.findall(r'\w+', text.lower())

    def _initialize(self):
        total_len = 0
        for chunk in self.corpus:
            tokens = self._tokenize(chunk.content)
            self.doc_lengths.append(len(tokens))
            total_len += len(tokens)
            
            freqs = {}
            for token in tokens:
                freqs[token] = freqs.get(token, 0) + 1
            self.doc_term_freqs.append(freqs)
            
            for token in freqs.keys():
                self.nd[token] = self.nd.get(token, 0) + 1
                
        self.avg_doc_len = total_len / self.corpus_size if self.corpus_size > 0 else 0.0

    def score(self, query: str) -> List[Tuple[DocumentChunk, float]]:
        """
        Scores all chunks in the corpus against the query.
        Returns a list of tuples containing (chunk, score).
        """
        if not self.corpus or not query:
            return [(chunk, 0.0) for chunk in self.corpus]

        query_tokens = self._tokenize(query)
        results = []
        
        for idx, chunk in enumerate(self.corpus):
            score = 0.0
            doc_len = self.doc_lengths[idx]
            freqs = self.doc_term_freqs[idx]
            
            for token in query_tokens:
                if token not in freqs:
                    continue
                
                # Compute IDF with BM25 smoothing
                n_t = self.nd.get(token, 0)
                idf = math.log((self.corpus_size - n_t + 0.5) / (n_t + 0.5) + 1.0)
                
                # Avoid negative IDF
                idf = max(idf, 0.0001)
                
                # Compute term frequency component
                f_t = freqs[token]
                numerator = f_t * (self.k1 + 1.0)
                
                denom_len_ratio = doc_len / self.avg_doc_len if self.avg_doc_len > 0 else 1.0
                denominator = f_t + self.k1 * (1.0 - self.b + self.b * denom_len_ratio)
                
                score += idf * (numerator / denominator)
                
            results.append((chunk, score))
            
        return results
