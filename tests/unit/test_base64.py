#!/usr/bin/env python3
"""
Test base64 encoding directly
"""

import base64
import tempfile
import os

def test_base64_encoding():
    """Test the base64 encoding function directly"""
    try:
        from app.services.mistral_service import MistralOCRService
        
        # Create a small test PDF
        test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nxref\n0 2\n0000000000 65535 f \n0000000009 00000 n \ntrailer\n<<\n/Size 2\n/Root 1 0 R\n>>\nstartxref\n74\n%%EOF"
        
        # Initialize service
        service = MistralOCRService()
        
        # Test the base64 encoding function
        print("🔧 Testing base64 encoding...")
        data_url = service._prepare_file_data(test_content, "test.pdf")
        
        print(f"✅ Base64 encoding successful!")
        print(f"📊 Original file size: {len(test_content)} bytes")
        print(f"📊 Data URL length: {len(data_url)} characters")
        print(f"🔗 Data URL format: {data_url[:60]}...")
        
        # Verify it's proper base64
        if "data:application/pdf;base64," in data_url:
            base64_part = data_url.split("data:application/pdf;base64,")[1]
            try:
                decoded = base64.b64decode(base64_part)
                if decoded == test_content:
                    print("✅ Base64 encoding/decoding verification PASSED")
                    return True
                else:
                    print("❌ Base64 content doesn't match original")
                    return False
            except Exception as e:
                print(f"❌ Base64 decoding failed: {e}")
                return False
        else:
            print("❌ Data URL format incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_image_base64():
    """Test base64 encoding for an image"""
    try:
        from app.services.mistral_service import MistralOCRService
        
        # Create a minimal PNG (1x1 pixel)
        png_content = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a4944415478da6300010000050001d72db3540000000049454e44ae426082')
        
        service = MistralOCRService()
        
        print("\n🖼️ Testing image base64 encoding...")
        data_url = service._prepare_file_data(png_content, "test.png")
        
        print(f"✅ Image base64 encoding successful!")
        print(f"📊 Original image size: {len(png_content)} bytes")
        print(f"📊 Data URL length: {len(data_url)} characters")
        print(f"🔗 Data URL format: {data_url[:60]}...")
        
        # Verify format
        if "data:image/png;base64," in data_url:
            print("✅ Image data URL format correct")
            return True
        else:
            print("❌ Image data URL format incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Image test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Base64 Encoding Test ===")
    
    pdf_test = test_base64_encoding()
    image_test = test_image_base64()
    
    print(f"\n=== Results ===")
    print(f"PDF Base64: {'✅ PASS' if pdf_test else '❌ FAIL'}")
    print(f"Image Base64: {'✅ PASS' if image_test else '❌ FAIL'}")
    print(f"Overall: {'✅ ALL TESTS PASSED' if pdf_test and image_test else '❌ SOME TESTS FAILED'}")
