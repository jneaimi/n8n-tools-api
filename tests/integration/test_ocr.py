#!/usr/bin/env python3
"""
Test script for OCR endpoint to verify the logging fix
"""

import requests
import json

# Test the OCR endpoint with a simple request
def test_ocr_endpoint():
    url = "http://localhost:8000/api/v1/ocr/process-file"
    
    # Create a test request (this will likely fail due to missing API key, but should not cause the NameError)
    test_data = {
        "api_key": "test-key-that-will-fail",
        "options": {
            "include_image_base64": True
        }
    }
    
    try:
        response = requests.post(url, json=test_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Check if we get a proper error response instead of NameError
        if response.status_code == 500:
            response_data = response.json()
            if "name 'app_logger' is not defined" in response.text:
                print("❌ STILL HAS NameError - logging fix failed")
                return False
            else:
                print("✅ NameError fixed - getting proper error handling")
                return True
        else:
            print("✅ Request processed without NameError")
            return True
            
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing OCR endpoint for logging fix...")
    success = test_ocr_endpoint()
    print(f"Test {'PASSED' if success else 'FAILED'}")
