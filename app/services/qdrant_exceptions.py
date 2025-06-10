"""
Qdrant-related exception classes for RAG operations.

Custom exceptions for Qdrant operations that don't depend on the qdrant-client library.
"""


class QdrantConnectionError(Exception):
    """Raised when unable to connect to Qdrant server."""
    pass


class QdrantAuthenticationError(Exception):
    """Raised when Qdrant authentication fails."""
    pass


class QdrantValidationError(Exception):
    """Raised when Qdrant request validation fails."""
    pass


class QdrantCollectionExistsError(Exception):
    """Raised when trying to create a collection that already exists."""
    pass


class QdrantCollectionCreationError(Exception):
    """Raised when collection creation fails."""
    pass
