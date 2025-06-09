"""
AI PDF Operations Module

This module provides AI-powered PDF processing capabilities including:
- OCR (Optical Character Recognition)
- Vision analysis
- Embeddings generation
- Mistral API integration

Designed for n8n workflow automation with FastAPI integration.
"""

from .config import ai_pdf_config
from .base import AIOperation, OCROperation, VisionOperation, EmbeddingsOperation
from .mistral_integration import MistralAPI
from .ocr import OCRProcessor
from .vision import VisionProcessor
from .embeddings import EmbeddingsProcessor

__all__ = [
    "ai_pdf_config",
    "AIOperation",
    "OCROperation", 
    "VisionOperation",
    "EmbeddingsOperation",
    "MistralAPI",
    "OCRProcessor",
    "VisionProcessor",
    "EmbeddingsProcessor",
]
