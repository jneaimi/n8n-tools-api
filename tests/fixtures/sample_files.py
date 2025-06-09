"""
Test fixtures for sample PDF files and test data.

Provides utilities to create various types of PDF files for testing,
including valid PDFs, corrupted PDFs, and PDFs with specific characteristics.
"""

import pytest
from pathlib import Path
from io import BytesIO
import tempfile
import os


class PDFTestFileGenerator:
    """Generator for various types of test PDF files."""
    
    @staticmethod
    def create_minimal_pdf(pages: int = 1, page_content: str = "Test Page") -> bytes:
        """Create a minimal valid PDF with specified content."""
        pdf_content = b'%PDF-1.4\n'
        
        # Catalog
        pdf_content += b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        
        # Pages
        pdf_content += f'2 0 obj\n<< /Type /Pages /Kids ['.encode()
        for i in range(pages):
            pdf_content += f' {i+3} 0 R'.encode()
        pdf_content += f'] /Count {pages} >>\nendobj\n'.encode()
        
        # Individual pages and content
        obj_num = 3
        for i in range(pages):
            # Page object
            pdf_content += (
                f'{obj_num} 0 obj\n'
                f'<< /Type /Page /Parent 2 0 R '
                f'/MediaBox [0 0 612 792] '
                f'/Resources << /Font << /F1 {obj_num + pages} 0 R >> >> '
                f'/Contents {obj_num + pages + 1} 0 R >>\n'
                f'endobj\n'
            ).encode()
            obj_num += 1
        
        # Font objects
        for i in range(pages):
            pdf_content += (
                f'{obj_num} 0 obj\n'
                f'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n'
                f'endobj\n'
            ).encode()
            obj_num += 1
        
        # Content streams
        for i in range(pages):
            content = f'BT /F1 12 Tf 50 750 Td ({page_content} {i+1}) Tj ET'
            pdf_content += (
                f'{obj_num} 0 obj\n'
                f'<< /Length {len(content)} >>\n'
                f'stream\n{content}\nendstream\n'
                f'endobj\n'
            ).encode()
            obj_num += 1
        
        # Cross-reference table
        xref_offset = len(pdf_content)
        pdf_content += b'xref\n'
        pdf_content += f'0 {obj_num}\n'.encode()
        pdf_content += b'0000000000 65535 f \n'
        
        # Simplified xref entries
        for i in range(1, obj_num):
            pdf_content += f'{str(20 + i * 50).zfill(10)} 00000 n \n'.encode()
        
        # Trailer
        pdf_content += (
            f'trailer\n'
            f'<< /Size {obj_num} /Root 1 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF'
        ).encode()
        
        return pdf_content
    
    @staticmethod
    def create_pdf_with_metadata(title: str = "Test Document", 
                                author: str = "Test Author",
                                subject: str = "Test Subject") -> bytes:
        """Create a PDF with document metadata."""
        pdf_content = b'%PDF-1.4\n'
        
        # Info object with metadata
        pdf_content += (
            f'1 0 obj\n'
            f'<< /Title ({title}) /Author ({author}) /Subject ({subject}) '
            f'/Creator (PDFTestGenerator) /Producer (N8N Tools Test) >>\n'
            f'endobj\n'
        ).encode()
        
        # Catalog
        pdf_content += b'2 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n'
        
        # Pages
        pdf_content += b'3 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n'
        
        # Page
        pdf_content += (
            b'4 0 obj\n'
            b'<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] '
            b'/Resources << /Font << /F1 5 0 R >> >> '
            b'/Contents 6 0 R >>\n'
            b'endobj\n'
        )
        
        # Font
        pdf_content += (
            b'5 0 obj\n'
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n'
            b'endobj\n'
        )
        
        # Content
        content = f'BT /F1 12 Tf 50 750 Td (Document: {title}) Tj ET'
        pdf_content += (
            f'6 0 obj\n'
            f'<< /Length {len(content)} >>\n'
            f'stream\n{content}\nendstream\n'
            f'endobj\n'
        ).encode()
        
        # Cross-reference table
        xref_offset = len(pdf_content)
        pdf_content += b'xref\n0 7\n'
        pdf_content += b'0000000000 65535 f \n'
        for i in range(1, 7):
            pdf_content += f'{str(20 + i * 80).zfill(10)} 00000 n \n'.encode()
        
        # Trailer with Info reference
        pdf_content += (
            f'trailer\n'
            f'<< /Size 7 /Root 2 0 R /Info 1 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF'
        ).encode()
        
        return pdf_content
    
    @staticmethod
    def create_password_protected_pdf() -> bytes:
        """Create a password-protected PDF (simulated structure)."""
        # Note: This creates a PDF with encryption dictionary but may not be fully functional
        # For real password protection, you'd need a proper PDF library
        pdf_content = b'%PDF-1.4\n'
        
        # Catalog
        pdf_content += b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        
        # Pages
        pdf_content += b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
        
        # Page
        pdf_content += (
            b'3 0 obj\n'
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n'
            b'endobj\n'
        )
        
        # Encryption dictionary (simplified)
        pdf_content += (
            b'4 0 obj\n'
            b'<< /Filter /Standard /V 1 /R 2 /O <28BF4E5E4E758A41> /U <28BF4E5E4E758A41> /P -4 >>\n'
            b'endobj\n'
        )
        
        # Cross-reference
        xref_offset = len(pdf_content)
        pdf_content += b'xref\n0 5\n'
        pdf_content += b'0000000000 65535 f \n'
        for i in range(1, 5):
            pdf_content += f'{str(20 + i * 60).zfill(10)} 00000 n \n'.encode()
        
        # Trailer with Encrypt reference
        pdf_content += (
            f'trailer\n'
            f'<< /Size 5 /Root 1 0 R /Encrypt 4 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF'
        ).encode()
        
        return pdf_content
    
    @staticmethod
    def create_corrupted_pdf() -> bytes:
        """Create a corrupted PDF file."""
        valid_pdf = PDFTestFileGenerator.create_minimal_pdf()
        # Corrupt by truncating and adding garbage
        corrupted = valid_pdf[:len(valid_pdf)//2] + b"CORRUPTED_GARBAGE_DATA_123456789"
        return corrupted
    
    @staticmethod
    def create_invalid_pdf_content() -> bytes:
        """Create content that looks like a PDF but isn't valid."""
        return b"%PDF-1.4\nThis is not actually a valid PDF file structure\n%%EOF"
    
    @staticmethod
    def create_large_pdf(pages: int = 100) -> bytes:
        """Create a large PDF with many pages."""
        return PDFTestFileGenerator.create_minimal_pdf(pages, "Large Document Page")
    
    @staticmethod
    def create_pdf_with_images_placeholder() -> bytes:
        """Create a PDF that simulates having images (placeholder structure)."""
        pdf_content = b'%PDF-1.4\n'
        
        # Catalog
        pdf_content += b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        
        # Pages
        pdf_content += b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
        
        # Page with image reference
        pdf_content += (
            b'3 0 obj\n'
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Resources << /XObject << /Im1 4 0 R >> >> '
            b'/Contents 5 0 R >>\n'
            b'endobj\n'
        )
        
        # Image object (placeholder)
        pdf_content += (
            b'4 0 obj\n'
            b'<< /Type /XObject /Subtype /Image /Width 100 /Height 100 '
            b'/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 5 >>\n'
            b'stream\nFAKE\nendstream\n'
            b'endobj\n'
        )
        
        # Content stream
        content = 'q 100 0 0 100 100 100 cm /Im1 Do Q'
        pdf_content += (
            f'5 0 obj\n'
            f'<< /Length {len(content)} >>\n'
            f'stream\n{content}\nendstream\n'
            f'endobj\n'
        ).encode()
        
        # Cross-reference
        xref_offset = len(pdf_content)
        pdf_content += b'xref\n0 6\n'
        pdf_content += b'0000000000 65535 f \n'
        for i in range(1, 6):
            pdf_content += f'{str(20 + i * 100).zfill(10)} 00000 n \n'.encode()
        
        # Trailer
        pdf_content += (
            f'trailer\n'
            f'<< /Size 6 /Root 1 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF'
        ).encode()
        
        return pdf_content


@pytest.fixture
def pdf_test_generator():
    """Provide access to PDF test file generator."""
    return PDFTestFileGenerator()


@pytest.fixture
def sample_valid_pdf():
    """Generate a simple valid PDF."""
    return PDFTestFileGenerator.create_minimal_pdf(3, "Sample Test Page")


@pytest.fixture
def sample_multipage_pdf():
    """Generate a multi-page PDF."""
    return PDFTestFileGenerator.create_minimal_pdf(10, "Multi-page Document")


@pytest.fixture
def sample_pdf_with_metadata():
    """Generate a PDF with metadata."""
    return PDFTestFileGenerator.create_pdf_with_metadata(
        title="Test Document Title",
        author="Test Author Name",
        subject="Testing PDF Processing"
    )


@pytest.fixture
def sample_corrupted_pdf():
    """Generate a corrupted PDF."""
    return PDFTestFileGenerator.create_corrupted_pdf()


@pytest.fixture
def sample_invalid_pdf():
    """Generate invalid PDF content."""
    return PDFTestFileGenerator.create_invalid_pdf_content()


@pytest.fixture
def sample_large_pdf():
    """Generate a large PDF for performance testing."""
    return PDFTestFileGenerator.create_large_pdf(50)


@pytest.fixture
def sample_password_protected_pdf():
    """Generate a password-protected PDF structure."""
    return PDFTestFileGenerator.create_password_protected_pdf()


@pytest.fixture
def sample_pdf_with_images():
    """Generate a PDF with image placeholders."""
    return PDFTestFileGenerator.create_pdf_with_images_placeholder()


@pytest.fixture
def create_temp_pdf_file():
    """Factory fixture to create temporary PDF files."""
    created_files = []
    
    def _create_temp_pdf(content: bytes, suffix: str = ".pdf") -> Path:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.close()
        
        temp_path = Path(temp_file.name)
        created_files.append(temp_path)
        return temp_path
    
    yield _create_temp_pdf
    
    # Cleanup
    for file_path in created_files:
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass


@pytest.fixture
def test_pdfs_directory():
    """Provide access to test PDFs directory."""
    test_dir = Path(__file__).parent / "test_pdfs"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture(scope="session", autouse=True)
def create_sample_pdf_files():
    """Create sample PDF files for testing if they don't exist."""
    test_dir = Path(__file__).parent / "test_pdfs"
    test_dir.mkdir(exist_ok=True)
    
    # Create sample files
    files_to_create = {
        "valid_simple.pdf": PDFTestFileGenerator.create_minimal_pdf(1, "Simple Valid PDF"),
        "valid_multipage.pdf": PDFTestFileGenerator.create_minimal_pdf(5, "Multi-page PDF"),
        "valid_with_metadata.pdf": PDFTestFileGenerator.create_pdf_with_metadata(),
        "corrupted.pdf": PDFTestFileGenerator.create_corrupted_pdf(),
        "invalid.pdf": PDFTestFileGenerator.create_invalid_pdf_content(),
        "large.pdf": PDFTestFileGenerator.create_large_pdf(20),
        "password_protected.pdf": PDFTestFileGenerator.create_password_protected_pdf(),
        "with_images.pdf": PDFTestFileGenerator.create_pdf_with_images_placeholder(),
    }
    
    for filename, content in files_to_create.items():
        file_path = test_dir / filename
        if not file_path.exists():
            file_path.write_bytes(content)
    
    yield test_dir
    
    # Optional cleanup - uncomment if you want files removed after session
    # for filename in files_to_create.keys():
    #     file_path = test_dir / filename
    #     if file_path.exists():
    #         file_path.unlink()


# Utility functions for test data
def get_test_pdf_path(filename: str) -> Path:
    """Get path to a test PDF file."""
    test_dir = Path(__file__).parent / "test_pdfs"
    return test_dir / filename


def load_test_pdf(filename: str) -> bytes:
    """Load a test PDF file as bytes."""
    file_path = get_test_pdf_path(filename)
    if not file_path.exists():
        raise FileNotFoundError(f"Test PDF file not found: {filename}")
    return file_path.read_bytes()


# Test data constants
TEST_PDF_FILES = {
    "valid_simple": "valid_simple.pdf",
    "valid_multipage": "valid_multipage.pdf",
    "valid_with_metadata": "valid_with_metadata.pdf",
    "corrupted": "corrupted.pdf",
    "invalid": "invalid.pdf",
    "large": "large.pdf",
    "password_protected": "password_protected.pdf",
    "with_images": "with_images.pdf",
}

# Export commonly used test data
__all__ = [
    "PDFTestFileGenerator",
    "pdf_test_generator",
    "sample_valid_pdf",
    "sample_multipage_pdf",
    "sample_pdf_with_metadata",
    "sample_corrupted_pdf",
    "sample_invalid_pdf",
    "sample_large_pdf",
    "sample_password_protected_pdf",
    "sample_pdf_with_images",
    "create_temp_pdf_file",
    "test_pdfs_directory",
    "create_sample_pdf_files",
    "get_test_pdf_path",
    "load_test_pdf",
    "TEST_PDF_FILES"
]
