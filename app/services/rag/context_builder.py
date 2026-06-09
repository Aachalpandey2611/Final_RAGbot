from typing import List, Dict, Any, Tuple
from app.models.document import DocumentChunk

class ContextBuilder:
    """
    Formats the retrieved chunks into a context string for the LLM prompt 
    and generates citation metadata.
    """
    
    @staticmethod
    def build_context(chunks: List[DocumentChunk]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Builds the context string and returns citation list.
        """
        if not chunks:
            return "No relevant context found.", []
            
        # Group chunks by document_id
        grouped_chunks = {}
        for chunk in chunks:
            doc_id = getattr(chunk, 'document_id', -1)
            if doc_id not in grouped_chunks:
                grouped_chunks[doc_id] = []
            grouped_chunks[doc_id].append(chunk)
            
        context_parts = []
        citations = []
        source_index = 1
        
        for doc_id, doc_chunks in grouped_chunks.items():
            # Sort chunks by their index to maintain logical order
            doc_chunks.sort(key=lambda c: getattr(c, 'chunk_index', 0) or 0)
            
            # Extract metadata from the first chunk for the header
            first_chunk = doc_chunks[0]
            meta = first_chunk.meta_data or {}
            source_file = meta.get("original_filename", f"Document ID: {doc_id}")
            
            # Form unified context for this document
            header = f"[Source {source_index} - {source_file}]"
            
            merged_content = []
            for chunk in doc_chunks:
                merged_content.append(chunk.content.strip())
                
                # Keep track of citation for each chunk
                citations.append({
                    "source_index": source_index,
                    "chunk_id": chunk.id,
                    "document_id": doc_id,
                    "filename": source_file,
                    "page": (chunk.meta_data or {}).get("page", "Unknown"),
                    "distance_score": getattr(chunk, 'similarity_score', None)
                })
                
            # Combine all chunks from this document with a clean separator
            context_parts.append(f"{header}\n" + "\n\n...\n\n".join(merged_content))
            source_index += 1
            
        return "\n\n".join(context_parts), citations
