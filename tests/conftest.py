"""
Global test configuration and fixtures.

Provides shared fixtures for all test modules including test client,
sample PDF files, and common test utilities.
"""

import pytest
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app


# Test client fixtures
@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Sample PDF creation utilities
class PDFGenerator:
    """Utility class for generating test PDF files."""
    
    @staticmethod
    def create_valid_pdf(pages: int = 3) -> bytes:
        """Create a minimal valid PDF with specified number of pages."""
        pdf_content = b'%PDF-1.4\n'
        
        # PDF catalog
        pdf_content += b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        
        # Pages object
        pdf_content += f'2 0 obj\n<< /Type /Pages /Kids ['.encode()
        for i in range(pages):
            pdf_content += f' {i+3} 0 R'.encode()
        pdf_content += f'] /Count {pages} >>\nendobj\n'.encode()
        
        # Individual page objects
        for i in range(pages):
            page_num = i + 3
            pdf_content += (
                f'{page_num} 0 obj\n'
                f'<< /Type /Page /Parent 2 0 R '
                f'/MediaBox [0 0 612 792] '
                f'/Contents {page_num + pages} 0 R >>\n'
                f'endobj\n'
            ).encode()
        
        # Page content streams
        for i in range(pages):
            content_num = i + 3 + pages
            content = f'BT /F1 12 Tf 50 750 Td (Page {i+1}) Tj ET'
            pdf_content += (
                f'{content_num} 0 obj\n'
                f'<< /Length {len(content)} >>\n'
                f'stream\n{content}\nendstream\n'
                f'endobj\n'
            ).encode()
        
        # Cross-reference table
        xref_offset = len(pdf_content)
        pdf_content += b'xref\n'
        pdf_content += f'0 {3 + 2 * pages}\n'.encode()
        pdf_content += b'0000000000 65535 f \n'
        
        # Add xref entries (simplified)
        for i in range(2 + 2 * pages):
            pdf_content += f'{str(20 + i * 100).zfill(10)} 00000 n \n'.encode()
        
        # Trailer
        pdf_content += (
            f'trailer\n'
            f'<< /Size {3 + 2 * pages} /Root 1 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF'
        ).encode()
        
        return pdf_content
    
    @staticmethod
    def create_invalid_pdf() -> bytes:
        """Create invalid PDF content for testing error handling."""
        return b"This is not a valid PDF file content"
    
    @staticmethod
    def create_corrupted_pdf() -> bytes:
        """Create a corrupted PDF for testing error handling."""
        valid_pdf = PDFGenerator.create_valid_pdf(2)
        # Corrupt the PDF by truncating it
        return valid_pdf[:len(valid_pdf)//2] + b"CORRUPTED_DATA"
    
    @staticmethod
    def create_large_pdf(pages: int = 100) -> bytes:
        """Create a larger PDF for performance testing."""
        return PDFGenerator.create_valid_pdf(pages)


# PDF file fixtures
@pytest.fixture
def pdf_generator() -> PDFGenerator:
    """Provide access to PDF generation utilities."""
    return PDFGenerator()


@pytest.fixture
def valid_pdf_bytes(pdf_generator: PDFGenerator) -> bytes:
    """Generate valid PDF content as bytes."""
    return pdf_generator.create_valid_pdf(3)


@pytest.fixture
def valid_multipage_pdf_bytes(pdf_generator: PDFGenerator) -> bytes:
    """Generate valid multi-page PDF content as bytes."""
    return pdf_generator.create_valid_pdf(10)


@pytest.fixture
def invalid_pdf_bytes(pdf_generator: PDFGenerator) -> bytes:
    """Generate invalid PDF content as bytes."""
    return pdf_generator.create_invalid_pdf()


@pytest.fixture
def corrupted_pdf_bytes(pdf_generator: PDFGenerator) -> bytes:
    """Generate corrupted PDF content as bytes."""
    return pdf_generator.create_corrupted_pdf()


@pytest.fixture
def large_pdf_bytes(pdf_generator: PDFGenerator) -> bytes:
    """Generate large PDF content as bytes for performance testing."""
    return pdf_generator.create_large_pdf(50)


# File upload fixtures
@pytest.fixture
def valid_pdf_upload_file(valid_pdf_bytes: bytes):
    """Create a file-like object for PDF upload testing."""
    return ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")


@pytest.fixture
def invalid_pdf_upload_file(invalid_pdf_bytes: bytes):
    """Create a file-like object for invalid PDF testing."""
    return ("invalid.pdf", BytesIO(invalid_pdf_bytes), "application/pdf")


@pytest.fixture
def corrupted_pdf_upload_file(corrupted_pdf_bytes: bytes):
    """Create a file-like object for corrupted PDF testing."""
    return ("corrupted.pdf", BytesIO(corrupted_pdf_bytes), "application/pdf")


# Test data paths
@pytest.fixture
def test_data_dir() -> Path:
    """Return the path to test data directory."""
    return Path(__file__).parent / "fixtures" / "test_pdfs"


# Configuration for pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "docker: mark test as a docker test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_temp_files():
    """Automatically cleanup temporary files after each test."""
    yield
    # Add cleanup logic here if needed
    # For now, the PDFService handles its own cleanup
    pass
