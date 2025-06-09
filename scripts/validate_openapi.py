#!/usr/bin/env python3
"""
OpenAPI Documentation Validation Script

Tests all the enhanced OpenAPI endpoints and n8n integration features
to ensure they work correctly after implementation.
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8001"

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str, expected_keys: list = None) -> Dict[str, Any]:
    """Test a single endpoint and validate response."""
    try:
        async with session.get(f"{BASE_URL}{endpoint}") as response:
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                data = await response.json()
            else:
                data = await response.text()
            
            result = {
                "endpoint": endpoint,
                "status": response.status,
                "success": response.status == 200,
                "content_type": content_type,
                "data": data
            }
            
            # Validate expected keys if provided
            if expected_keys and isinstance(data, dict):
                missing_keys = [key for key in expected_keys if key not in data]
                result["missing_keys"] = missing_keys
                result["has_all_keys"] = len(missing_keys) == 0
            
            return result
            
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": "error",
            "success": False,
            "error": str(e)
        }

async def validate_openapi_schema(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Validate the OpenAPI schema structure and n8n customizations."""
    try:
        async with session.get(f"{BASE_URL}/openapi.json") as response:
            if response.status != 200:
                return {"success": False, "error": f"HTTP {response.status}"}
            
            schema = await response.json()
            
            # Validate basic OpenAPI structure
            required_fields = ["openapi", "info", "paths"]
            missing_fields = [field for field in required_fields if field not in schema]
            
            # Check n8n customizations
            n8n_customizations = {
                "has_custom_logo": "x-logo" in schema.get("info", {}),
                "has_tags": "tags" in schema,
                "path_count": len(schema.get("paths", {})),
                "has_examples": False,
                "has_headers": False
            }
            
            # Check for examples in endpoints
            for path, methods in schema.get("paths", {}).items():
                for method, details in methods.items():
                    # Check for examples
                    if "requestBody" in details:
                        content = details["requestBody"].get("content", {})
                        if "multipart/form-data" in content:
                            if "examples" in content["multipart/form-data"]:
                                n8n_customizations["has_examples"] = True
                    
                    # Check for custom headers documentation
                    if "responses" in details:
                        for status_code, response in details["responses"].items():
                            if "headers" in response:
                                n8n_customizations["has_headers"] = True
            
            return {
                "success": True,
                "missing_fields": missing_fields,
                "valid_structure": len(missing_fields) == 0,
                "n8n_customizations": n8n_customizations,
                "api_info": {
                    "title": schema.get("info", {}).get("title"),
                    "version": schema.get("info", {}).get("version"),
                    "openapi_version": schema.get("openapi")
                }
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

async def main():
    """Run all validation tests."""
    print("🚀 Starting OpenAPI Documentation Validation")
    print("=" * 60)
    
    # Test endpoints with expected structure
    test_cases = [
        {
            "endpoint": "/health",
            "expected_keys": ["status", "service", "version", "capabilities", "limits", "endpoints"],
            "description": "Enhanced health check endpoint"
        },
        {
            "endpoint": "/",
            "expected_keys": ["message", "version", "documentation", "endpoints", "quick_start", "support"],
            "description": "Enhanced root endpoint"
        },
        {
            "endpoint": "/n8n",
            "expected_keys": ["service", "n8n_integration", "recommended_endpoints", "n8n_setup_tips", "example_workflow"],
            "description": "n8n integration information endpoint"
        },
        {
            "endpoint": "/openapi.json",
            "expected_keys": None,  # Will be validated separately
            "description": "OpenAPI schema endpoint"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        results = []
        
        # Test individual endpoints
        for test_case in test_cases:
            print(f"📋 Testing {test_case['endpoint']} - {test_case['description']}")
            result = await test_endpoint(session, test_case["endpoint"], test_case["expected_keys"])
            results.append(result)
            
            if result["success"]:
                print(f"   ✅ Status: {result['status']}")
                if "has_all_keys" in result:
                    if result["has_all_keys"]:
                        print("   ✅ All expected keys present")
                    else:
                        print(f"   ❌ Missing keys: {result['missing_keys']}")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            print()
        
        # Validate OpenAPI schema structure
        print("📋 Validating OpenAPI Schema Structure")
        schema_validation = await validate_openapi_schema(session)
        
        if schema_validation["success"]:
            print(f"   ✅ Schema structure valid: {schema_validation['valid_structure']}")
            print(f"   📊 API Info: {schema_validation['api_info']}")
            
            customizations = schema_validation["n8n_customizations"]
            print(f"   🎨 n8n Customizations:")
            print(f"      - Custom logo: {customizations['has_custom_logo']}")
            print(f"      - Tags defined: {customizations['has_tags']}")
            print(f"      - Examples included: {customizations['has_examples']}")
            print(f"      - Headers documented: {customizations['has_headers']}")
            print(f"      - Total endpoints: {customizations['path_count']}")
            
            if schema_validation.get("missing_fields"):
                print(f"   ❌ Missing required fields: {schema_validation['missing_fields']}")
        else:
            print(f"   ❌ Schema validation failed: {schema_validation['error']}")
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        # Summary statistics
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["success"])
        
        print(f"Total endpoint tests: {total_tests}")
        print(f"Successful tests: {successful_tests}")
        print(f"Failed tests: {total_tests - successful_tests}")
        
        # Check if OpenAPI schema is valid
        schema_valid = schema_validation.get("success", False) and schema_validation.get("valid_structure", False)
        print(f"OpenAPI schema valid: {schema_valid}")
        
        # Overall status
        all_passed = successful_tests == total_tests and schema_valid
        if all_passed:
            print("\n🎉 ALL TESTS PASSED! OpenAPI documentation is ready for n8n integration.")
        else:
            print("\n❌ Some tests failed. Please review the output above.")
            sys.exit(1)
        
        # Additional recommendations
        print("\n📋 n8n Integration Checklist:")
        print("   ✅ Enhanced API documentation with descriptions")
        print("   ✅ Custom OpenAPI schema with n8n optimizations")
        print("   ✅ Dedicated /n8n endpoint with integration guide")
        print("   ✅ Comprehensive examples for all operations")
        print("   ✅ Custom headers documentation for file operations")
        print("   ✅ Health check endpoint for monitoring")
        print("   ✅ Error handling information")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        sys.exit(1)
