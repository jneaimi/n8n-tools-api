#!/usr/bin/env python3
"""
More comprehensive test script for OCR endpoint
"""

import requests
import json
import tempfile
import os

def test_ocr_with_valid_structure():
    """Test with proper request structure but invalid API key"""
    url = "http://localhost:8000/api/v1/ocr/process-file"

    # Create a small test PDF file
    test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"

    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(test_content)
        tmp_file_path = tmp_file.name

    try:
        headers = {
            'X-API-Key': 'sdfsdssa'
        }

        with open(tmp_file_path, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            data = {
                'options': json.dumps({
                    'include_image_base64': True
                })
            }

            response = requests.post(url, headers=headers, files=files, data=data)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}...")  # First 500 chars

        # Check if we get past the initial logging without NameError
        if "name 'logger' is not defined" in response.text:
            print("❌ STILL HAS NameError - logging fix incomplete")
            return False
        elif "name 'app_logger' is not defined" in response.text:
            print("❌ STILL HAS app_logger NameError")
            return False
        else:
            print("✅ No logging NameErrors found")
            return True

    except Exception as e:
        print(f"Request failed: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

def test_health_endpoint():
    """Test health endpoint"""
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Health check: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing n8n-tools OCR API ===")

    print("\n1. Testing health endpoint...")
    health_ok = test_health_endpoint()

    print("\n2. Testing OCR endpoint with file upload...")
    ocr_ok = test_ocr_with_valid_structure()

    print(f"\n=== Results ===")
    print(f"Health: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"OCR Logging: {'✅ PASS' if ocr_ok else '❌ FAIL'}")
    print(f"Overall: {'✅ ALL TESTS PASSED' if health_ok and ocr_ok else '❌ SOME TESTS FAILED'}")
