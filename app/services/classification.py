"""
AI Document Classification Service

Classifies documents into predefined categories using embeddings and similarity matching.
Supports: Policies, Technical Documents, Manuals, Procedures, Meeting Notes, Contracts, Emails, Source Code
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import hashlib
from datetime import datetime


class DocumentClass(str, Enum):
    """Supported document classifications"""
    POLICIES = "Policies"
    TECHNICAL_DOCUMENTS = "Technical Documents"
    MANUALS = "Manuals"
    PROCEDURES = "Procedures"
    MEETING_NOTES = "Meeting Notes"
    CONTRACTS = "Contracts"
    EMAILS = "Emails"
    SOURCE_CODE = "Source Code"


@dataclass
class ClassificationResult:
    """Result of document classification"""
    document_id: str
    primary_class: DocumentClass
    confidence: float  # 0.0 to 1.0
    class_scores: Dict[DocumentClass, float]  # All class confidences
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class DocumentClassifier:
    """
    AI-based document classifier using embeddings and semantic similarity.
    """

    # Class keywords and characteristics for pattern matching
    CLASS_PATTERNS = {
        DocumentClass.POLICIES: {
            "keywords": ["policy", "policies", "guidelines", "standards", "compliance", "regulation", "approved", "effective date", "shall"],
            "characteristics": ["formal", "regulatory", "organizational standards"],
            "sample_phrases": ["policy is", "guidelines are", "is required to", "in accordance with"]
        },
        DocumentClass.TECHNICAL_DOCUMENTS: {
            "keywords": ["technical", "specification", "architecture", "system design", "api", "protocol", "interface", "algorithm", "implementation"],
            "characteristics": ["detailed technical", "system documentation", "design details"],
            "sample_phrases": ["specification", "design", "component", "module", "interface"]
        },
        DocumentClass.MANUALS: {
            "keywords": ["manual", "guide", "tutorial", "how to", "instructions", "step-by-step", "user guide", "handbook", "reference"],
            "characteristics": ["instructional", "procedural", "user-facing"],
            "sample_phrases": ["to use", "follow these steps", "the following procedure", "see chapter"]
        },
        DocumentClass.PROCEDURES: {
            "keywords": ["procedure", "process", "workflow", "steps", "process flow", "sequence", "activity", "task", "checklist"],
            "characteristics": ["step-by-step", "sequential", "operational"],
            "sample_phrases": ["step 1", "first", "then", "finally", "next step"]
        },
        DocumentClass.MEETING_NOTES: {
            "keywords": ["meeting", "notes", "discussion", "attendance", "action items", "minutes", "participants", "agenda", "decided"],
            "characteristics": ["conversational", "informal documentation", "decisions"],
            "sample_phrases": ["discussed", "agreed", "action item", "next meeting", "attendees"]
        },
        DocumentClass.CONTRACTS: {
            "keywords": ["agreement", "contract", "terms", "parties", "legal", "liability", "obligations", "consideration", "effective", "signatures"],
            "characteristics": ["legal language", "formal structure", "binding terms"],
            "sample_phrases": ["hereby agree", "shall not", "notwithstanding", "in consideration of"]
        },
        DocumentClass.EMAILS: {
            "keywords": ["dear", "regards", "sincerely", "subject", "cc", "bcc", "forwarded", "reply", "urgent", "fyi"],
            "characteristics": ["informal", "conversational", "time-sensitive"],
            "sample_phrases": ["please see", "let me know", "asap", "thanks", "hi"]
        },
        DocumentClass.SOURCE_CODE: {
            "keywords": ["def ", "class ", "function", "import", "return", "if ", "for ", "while", "try", "except", "license"],
            "characteristics": ["code syntax", "programming language", "executable"],
            "sample_phrases": ["def ", "class ", "=>", "function(", "async"]
        },
    }

    def __init__(self, use_embeddings: bool = True):
        """
        Initialize classifier.
        
        Args:
            use_embeddings: If True, try to use sentence-transformers for embeddings
        """
        self.use_embeddings = use_embeddings
        self.embeddings_model = None
        
        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                self.embeddings_model = None
    
    def _extract_text_features(self, text: str) -> Dict[str, Any]:
        """Extract text features for classification"""
        text_lower = text.lower()
        lines = text.split('\n')
        
        return {
            "text_length": len(text),
            "line_count": len(lines),
            "word_count": len(text.split()),
            "has_code_markers": "def " in text_lower or "class " in text_lower or "function" in text_lower,
            "has_legal_terms": any(term in text_lower for term in ["hereby", "notwithstanding", "consideration", "obligation"]),
            "has_meeting_indicators": any(term in text_lower for term in ["attendance", "action items", "participants", "agenda"]),
            "has_email_indicators": any(term in text_lower for term in ["dear", "regards", "sincerely", "subject:", "cc:"]),
            "text": text_lower
        }
    
    def _keyword_match_score(self, text: str, doc_class: DocumentClass) -> float:
        """Calculate keyword matching score for a document class"""
        patterns = self.CLASS_PATTERNS[doc_class]
        text_lower = text.lower()
        
        # Count keyword matches (with boosting)
        keyword_matches = 0
        for kw in patterns["keywords"]:
            if kw.lower() in text_lower:
                keyword_matches += 1
        
        max_possible = len(patterns["keywords"])
        
        # Keyword score (0.0-1.0) with boost for multiple matches
        keyword_score = keyword_matches / max_possible if max_possible > 0 else 0.0
        keyword_boost = min(0.3, keyword_matches * 0.05)  # Up to 0.3 boost
        
        # Phrase matching
        phrase_matches = sum(1 for phrase in patterns["sample_phrases"] if phrase.lower() in text_lower)
        max_phrases = len(patterns["sample_phrases"])
        phrase_score = phrase_matches / max_phrases if max_phrases > 0 else 0.0
        phrase_boost = min(0.2, phrase_matches * 0.05)  # Up to 0.2 boost
        
        # Combine scores with boosts
        combined = (keyword_score * 0.6 + phrase_score * 0.4 + keyword_boost + phrase_boost)
        return min(1.0, combined)
    
    def _embedding_similarity_score(self, text: str, doc_class: DocumentClass) -> float:
        """Calculate embedding-based similarity score"""
        if self.embeddings_model is None:
            return 0.0
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            # Create a representative text for the document class
            patterns = self.CLASS_PATTERNS[doc_class]
            class_text = " ".join(patterns["keywords"] + patterns["sample_phrases"])
            
            # Get embeddings
            doc_embedding = self.embeddings_model.encode(text[:512], convert_to_tensor=False)
            class_embedding = self.embeddings_model.encode(class_text, convert_to_tensor=False)
            
            # Calculate cosine similarity
            similarity = cosine_similarity([doc_embedding], [class_embedding])[0][0]
            return float(similarity)
        except Exception:
            return 0.0
    
    def _feature_based_score(self, features: Dict[str, Any], doc_class: DocumentClass) -> float:
        """Calculate score based on extracted features"""
        score = 0.0
        
        if doc_class == DocumentClass.SOURCE_CODE and features["has_code_markers"]:
            score += 0.9
        
        if doc_class == DocumentClass.CONTRACTS and features["has_legal_terms"]:
            score += 0.9
        
        if doc_class == DocumentClass.MEETING_NOTES and features["has_meeting_indicators"]:
            score += 0.85
        
        if doc_class == DocumentClass.EMAILS and features["has_email_indicators"]:
            score += 0.8
        
        # Length-based scoring for better differentiation
        word_count = features["word_count"]
        if doc_class == DocumentClass.EMAILS and word_count < 1000:
            score += 0.15
        elif doc_class == DocumentClass.SOURCE_CODE and word_count < 15000:
            score += 0.1
        elif doc_class == DocumentClass.MANUALS and 500 < word_count < 50000:
            score += 0.25
        elif doc_class == DocumentClass.POLICIES and word_count > 300:
            score += 0.15
        elif doc_class == DocumentClass.PROCEDURES and word_count > 200:
            score += 0.1
        
        return min(1.0, score)
    
    def classify(self, text: str, document_id: str = None) -> ClassificationResult:
        """
        Classify a document.
        
        Args:
            text: Document text to classify
            document_id: Optional document identifier
        
        Returns:
            ClassificationResult with class, confidence, and metadata
        """
        if document_id is None:
            document_id = hashlib.md5(text[:100].encode()).hexdigest()[:8]
        
        # Extract features
        features = self._extract_text_features(text)
        
        # Calculate scores for each class
        class_scores = {}
        for doc_class in DocumentClass:
            # Combine multiple scoring methods
            keyword_score = self._keyword_match_score(text, doc_class)
            embedding_score = self._embedding_similarity_score(text, doc_class) if self.use_embeddings else 0.0
            feature_score = self._feature_based_score(features, doc_class)
            
            # Weighted combination - boost feature scores as they're more reliable
            if self.embeddings_model:
                combined_score = (keyword_score * 0.35 + embedding_score * 0.35 + feature_score * 0.3)
            else:
                combined_score = (keyword_score * 0.50 + feature_score * 0.50)
            
            class_scores[doc_class] = min(1.0, combined_score)
        
        # Find best match
        primary_class = max(class_scores, key=class_scores.get)
        confidence = class_scores[primary_class]
        
        # Generate tags
        tags = self._generate_tags(text, features, primary_class, class_scores)
        
        # Generate metadata
        metadata = self._generate_metadata(text, features, primary_class)
        
        return ClassificationResult(
            document_id=document_id,
            primary_class=primary_class,
            confidence=confidence,
            class_scores=class_scores,
            metadata=metadata,
            tags=tags
        )
    
    def _generate_tags(self, text: str, features: Dict[str, Any], primary_class: DocumentClass, 
                       class_scores: Dict[DocumentClass, float]) -> List[str]:
        """Generate semantic tags for the document"""
        tags = [primary_class.value]
        
        # Add secondary classifications if they have reasonable scores
        sorted_classes = sorted(class_scores.items(), key=lambda x: x[1], reverse=True)
        for doc_class, score in sorted_classes[1:4]:  # Top 3 alternatives
            if score > 0.3:
                tags.append(f"{doc_class.value} ({score:.0%})")
        
        # Add feature-based tags
        if features["has_code_markers"]:
            tags.append("code_content")
        
        if features["text_length"] > 10000:
            tags.append("lengthy")
        elif features["text_length"] < 500:
            tags.append("brief")
        
        if features["line_count"] > 200:
            tags.append("multi_section")
        
        return tags
    
    def _generate_metadata(self, text: str, features: Dict[str, Any], primary_class: DocumentClass) -> Dict[str, Any]:
        """Generate metadata for the classified document"""
        return {
            "classification": primary_class.value,
            "text_statistics": {
                "total_characters": features["text_length"],
                "total_words": features["word_count"],
                "total_lines": features["line_count"],
                "avg_line_length": features["text_length"] / features["line_count"] if features["line_count"] > 0 else 0
            },
            "language": "en",  # Could be enhanced with language detection
            "extraction_date": datetime.utcnow().isoformat(),
            "extracted_from": None,  # Could be populated from document metadata
        }
    
    def classify_batch(self, documents: List[Tuple[str, str]]) -> List[ClassificationResult]:
        """
        Classify multiple documents efficiently.
        
        Args:
            documents: List of (text, document_id) tuples
        
        Returns:
            List of ClassificationResult objects
        """
        return [self.classify(text, doc_id) for text, doc_id in documents]
    
    def get_class_info(self, doc_class: DocumentClass) -> Dict[str, Any]:
        """Get information about a document class"""
        patterns = self.CLASS_PATTERNS[doc_class]
        return {
            "class": doc_class.value,
            "keywords": patterns["keywords"],
            "characteristics": patterns["characteristics"],
            "sample_phrases": patterns["sample_phrases"]
        }
