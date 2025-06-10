#!/usr/bin/env python3
"""
Test the OCR response format to see if it now matches Mistral specification
"""

import requests
import json
import tempfile
import os

def test_ocr_response_format():
    """Test to see the actual response format"""
    url = "http://localhost:8000/api/v1/ocr/process-file"
    
    # Create a small test PDF
    test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(test_content)
        tmp_file_path = tmp_file.name
    
    try:
        headers = {
            'X-API-Key': 'test-api-key-for-response-format-check'
        }
        
        with open(tmp_file_path, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            data = {
                'options': json.dumps({
                    'include_image_base64': True
                })
            }
            
            response = requests.post(url, headers=headers, files=files, data=data)
            
        print(f"=== Response Analysis ===")
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        try:
            response_json = response.json()
            print(f"\n=== Response Structure ===")
            
            # Check for Mistral official format fields
            mistral_fields = ['pages', 'model', 'usage_info', 'document_annotation']
            found_fields = []
            missing_fields = []
            
            for field in mistral_fields:
                if field in response_json:
                    found_fields.append(field)
                else:
                    missing_fields.append(field)
            
            print(f"✅ Found Mistral fields: {found_fields}")
            if missing_fields:
                print(f"❓ Missing optional fields: {missing_fields}")
            
            # Check pages structure
            if 'pages' in response_json:
                pages = response_json['pages']
                if isinstance(pages, list) and len(pages) > 0:
                    first_page = pages[0]
                    page_fields = ['index', 'markdown', 'images', 'dimensions']
                    page_found = [f for f in page_fields if f in first_page]
                    page_missing = [f for f in page_fields if f not in first_page]
                    
                    print(f"✅ Page structure fields found: {page_found}")
                    if page_missing:
                        print(f"❓ Page structure fields missing: {page_missing}")
                    
                    # Check images structure
                    if 'images' in first_page:
                        images = first_page['images']
                        if isinstance(images, list) and len(images) > 0:
                            first_image = images[0]
                            image_fields = ['id', 'top_left_x', 'top_left_y', 'bottom_right_x', 'bottom_right_y', 'image_base64']
                            image_found = [f for f in image_fields if f in first_image]
                            image_missing = [f for f in image_fields if f not in first_image]
                            
                            print(f"✅ Image structure fields found: {image_found}")
                            if image_missing:
                                print(f"❓ Image structure fields missing: {image_missing}")
                        else:
                            print(f"📝 No images in response (expected for test PDF)")
            
            # Show full structure overview
            print(f"\n=== Full Response Structure ===")
            print(f"Top-level keys: {list(response_json.keys())}")
            
            # Pretty print a sample of the response (truncated)
            print(f"\n=== Sample Response (truncated) ===")
            sample_response = json.dumps(response_json, indent=2)[:1000]
            print(f"{sample_response}...")
            
            # Check if it looks like official Mistral format
            has_pages = 'pages' in response_json
            has_model = 'model' in response_json
            has_usage_info = 'usage_info' in response_json
            
            if has_pages and has_model:
                print(f"\n🎉 Response appears to follow official Mistral OCR format!")
                return True
            else:
                print(f"\n⚠️ Response does not match official Mistral OCR format")
                return False
                
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON")
            print(f"Raw response: {response.text[:500]}...")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    finally:
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

if __name__ == "__main__":
    print("=== Testing OCR Response Format ===")
    success = test_ocr_response_format()
    print(f"\n=== Final Result ===")
    print(f"Official Mistral Format: {'✅ YES' if success else '❌ NO'}")
