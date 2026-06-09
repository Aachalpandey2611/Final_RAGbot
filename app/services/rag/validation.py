from typing import List, Tuple


class ValidationService:
    """Lightweight validation layer for retrieved context.

    Determines whether the retrieved chunks provide sufficient confidence
    to proceed to the LLM. Uses retrieval scores and number of chunks.
    """

    def __init__(self, min_confidence: float = 0.5, expected_chunks: int = 3):
        self.min_confidence = min_confidence
        self.expected_chunks = expected_chunks

    def compute_confidence(self, retrieval_scores: List[float], num_chunks: int) -> float:
        if num_chunks == 0:
            return 0.0
        avg_score = sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0.0
        chunk_factor = min(1.0, num_chunks / float(self.expected_chunks))
        confidence = avg_score * chunk_factor
        return float(confidence)

    def validate(self, retrieval_scores: List[float], num_chunks: int) -> Tuple[bool, float]:
        """Return (is_valid, confidence)."""
        confidence = self.compute_confidence(retrieval_scores, num_chunks)
        is_valid = num_chunks > 0 and confidence >= self.min_confidence
        return is_valid, confidence
