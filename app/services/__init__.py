"""Services package - import submodules lazily to avoid heavy dependency failures during test runs."""
try:
	from app.services.auth import AuthService
except Exception:
	AuthService = None

try:
	from app.services.conversation import ConversationService
except Exception:
	ConversationService = None

try:
	from app.services.document import DocumentService
except Exception:
	DocumentService = None

try:
	from app.services.embedding import EmbeddingService
except Exception:
	EmbeddingService = None

__all__ = ["AuthService", "ConversationService", "DocumentService", "EmbeddingService"]
