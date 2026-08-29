"""Dependency providers for the documents domain."""

from app.domains.applications.dependencies import get_application_service
from app.domains.documents.repository import SqlDocumentRepository
from app.domains.documents.service import DocumentService


def get_document_service() -> DocumentService:
    """Build the service with its repository and the one foreign service (ARC-018)."""
    return DocumentService(SqlDocumentRepository(), get_application_service())
