        )
        
        assert validation_response.status_code == 200
        validation_data = validation_response.json()
        assert validation_data["status"] == "valid"

    def test_documentation_completeness(self):
        """Test that documentation covers all implemented endpoints."""
        # Get actual API routes
        response = requests.get(f"{self.BASE_URL}/openapi.json")
        schema = response.json()
        
        # Get all documented paths
        documented_paths = set(schema["paths"].keys())
        
        # Check that critical OCR endpoints are documented
        critical_endpoints = {
            "/api/v1/ocr/",
            "/api/v1/ocr/auth/test",
            "/api/v1/ocr/validate", 
            "/api/v1/ocr/health",
            "/api/v1/ocr/process-file",
            "/api/v1/ocr/process-url"
        }
        
        missing_endpoints = critical_endpoints - documented_paths
        assert not missing_endpoints, f"Missing documented endpoints: {missing_endpoints}"

    def test_examples_have_realistic_data(self):
        """Test that examples contain realistic data values."""
        response = requests.get(f"{self.BASE_URL}/openapi.json")
        schema = response.json()
        
        # Check file processing examples
        process_file_path = "/api/v1/ocr/process-file"
        if process_file_path in schema["paths"]:
            endpoint = schema["paths"][process_file_path]["post"]
            
            if "responses" in endpoint and "200" in endpoint["responses"]:
                success_response = endpoint["responses"]["200"]
                if "content" in success_response:
                    json_content = success_response["content"].get("application/json", {})
                    if "examples" in json_content:
                        for example_name, example in json_content["examples"].items():
                            example_value = example["value"]
                            
                            # Check that examples have realistic values
                            if "processing_info" in example_value:
                                processing_info = example_value["processing_info"]
                                
                                # Processing time should be reasonable (0.1s to 5 minutes)
                                if "processing_time_ms" in processing_info:
                                    time_ms = processing_info["processing_time_ms"]
                                    assert 100 <= time_ms <= 300000, f"Unrealistic processing time: {time_ms}ms"
                                
                                # Confidence score should be between 0 and 1
                                if "confidence_score" in processing_info:
                                    confidence = processing_info["confidence_score"]
                                    assert 0 <= confidence <= 1, f"Invalid confidence score: {confidence}"
                                
                                # Pages processed should be positive
                                if "pages_processed" in processing_info:
                                    pages = processing_info["pages_processed"]
                                    assert pages > 0, f"Invalid pages processed: {pages}"

    def test_error_messages_are_helpful(self):
        """Test that error examples provide helpful messages."""
        response = requests.get(f"{self.BASE_URL}/openapi.json")
        schema = response.json()
        
        # Check error examples in process-file endpoint
        process_file_path = "/api/v1/ocr/process-file"
        if process_file_path in schema["paths"]:
            endpoint = schema["paths"][process_file_path]["post"]
            
            error_codes = ["400", "401", "413", "422", "429", "500"]
            
            for error_code in error_codes:
                if error_code in endpoint.get("responses", {}):
                    error_response = endpoint["responses"][error_code]
                    if "content" in error_response:
                        json_content = error_response["content"].get("application/json", {})
                        if "examples" in json_content:
                            for example_name, example in json_content["examples"].items():
                                example_value = example["value"]
                                
                                # Check message is helpful
                                message = example_value.get("message", "")
                                assert len(message) > 10, f"Error message too short: {message}"
                                assert not message.lower().startswith("error"), "Generic error message"
                                
                                # Check details provide context
                                if "details" in example_value:
                                    details = example_value["details"]
                                    assert isinstance(details, dict), "Details should be an object"
                                    assert len(details) > 0, "Details should not be empty"

    def test_security_documentation(self):
        """Test that security requirements are properly documented."""
        response = requests.get(f"{self.BASE_URL}/openapi.json")
        schema = response.json()
        
        # Check that OCR endpoints have security requirements
        ocr_endpoints = [
            "/api/v1/ocr/auth/test",
            "/api/v1/ocr/process-file", 
            "/api/v1/ocr/process-url"
        ]
        
        for endpoint_path in ocr_endpoints:
            if endpoint_path in schema["paths"]:
                for method in schema["paths"][endpoint_path]:
                    endpoint = schema["paths"][endpoint_path][method]
                    
                    # Should have security requirements
                    assert "security" in endpoint, f"Missing security for {endpoint_path} {method}"
                    
                    # Should reference our auth schemes
                    security_schemes = endpoint["security"]
                    auth_methods = []
                    for scheme in security_schemes:
                        auth_methods.extend(scheme.keys())
                    
                    assert "ApiKeyAuth" in auth_methods or "BearerAuth" in auth_methods


class TestOCRDocumentationFiles:
    """Test that documentation files are comprehensive and accurate."""
    
    def test_api_specification_file_exists(self):
        """Test that API specification file exists and is readable."""
        spec_file = "/Users/jneaimimacmini/dev/python/n8n-tools/docs/api/ocr-api-specification.md"
        
        try:
            with open(spec_file, 'r') as f:
                content = f.read()
                
            # Check key sections are present
            required_sections = [
                "# OCR API Specification",
                "## Authentication", 
                "## Rate Limiting",
                "## Supported File Types",
                "## Error Handling",
                "## API Endpoints",
                "## Data Models",
                "## n8n Integration Guidelines"
            ]
            
            for section in required_sections:
                assert section in content, f"Missing section: {section}"
                
        except FileNotFoundError:
            pytest.fail("OCR API specification file not found")

    def test_n8n_integration_guide_exists(self):
        """Test that n8n integration guide exists and is comprehensive."""
        guide_file = "/Users/jneaimimacmini/dev/python/n8n-tools/docs/api/n8n-integration-guide.md"
        
        try:
            with open(guide_file, 'r') as f:
                content = f.read()
                
            # Check key sections are present
            required_sections = [
                "# N8N Integration Examples",
                "## Quick Start Guide",
                "## Example Workflows", 
                "## Error Handling Patterns",
                "## Performance Optimization",
                "## Best Practices"
            ]
            
            for section in required_sections:
                assert section in content, f"Missing section: {section}"
                
            # Check for practical examples
            assert "HTTP Request Node Configuration" in content
            assert "Error Handling" in content
            assert "Rate Limit Handling" in content
                
        except FileNotFoundError:
            pytest.fail("n8n integration guide file not found")

    def test_documentation_has_examples(self):
        """Test that documentation includes working examples."""
        spec_file = "/Users/jneaimimacmini/dev/python/n8n-tools/docs/api/ocr-api-specification.md"
        
        with open(spec_file, 'r') as f:
            content = f.read()
            
        # Check for code examples
        assert "```http" in content or "```json" in content, "Missing HTTP/JSON examples"
        assert "```javascript" in content, "Missing JavaScript examples"
        
        # Check for realistic example data
        assert "mistral-ocr-latest" in content, "Missing AI model reference"
        assert "X-API-Key" in content, "Missing authentication examples"
        assert "application/json" in content, "Missing content type examples"

    def test_error_codes_documented(self):
        """Test that all error codes are properly documented."""
        spec_file = "/Users/jneaimimacmini/dev/python/n8n-tools/docs/api/ocr-api-specification.md"
        
        with open(spec_file, 'r') as f:
            content = f.read()
            
        # Check that major error codes are documented
        error_codes = [
            "OCR_INVALID_FILE_FORMAT",
            "OCR_FILE_TOO_LARGE", 
            "OCR_API_AUTH_FAILED",
            "OCR_API_RATE_LIMIT",
            "OCR_PROCESSING_FAILED",
            "OCR_TIMEOUT_ERROR"
        ]
        
        for error_code in error_codes:
            assert error_code in content, f"Error code not documented: {error_code}"

    def test_rate_limits_documented(self):
        """Test that rate limits are clearly documented."""
        spec_file = "/Users/jneaimimacmini/dev/python/n8n-tools/docs/api/ocr-api-specification.md"
        
        with open(spec_file, 'r') as f:
            content = f.read()
            
        # Check rate limit information
        assert "60 requests" in content, "Missing per-minute rate limit"
        assert "1000 requests" in content, "Missing per-hour rate limit"
        assert "Rate Limiting" in content, "Missing rate limiting section"

    def test_file_constraints_documented(self):
        """Test that file constraints are clearly documented."""
        spec_file = "/Users/jneaimimacmini/dev/python/n8n-tools/docs/api/ocr-api-specification.md"
        
        with open(spec_file, 'r') as f:
            content = f.read()
            
        # Check file constraints
        assert "50MB" in content, "Missing file size limit"
        assert "PDF" in content and "PNG" in content, "Missing supported formats"
        assert "JPEG" in content and "TIFF" in content, "Missing image formats"


class TestOpenAPIEnhancementsModule:
    """Test the OpenAPI enhancements module."""
    
    def test_enhancements_module_importable(self):
        """Test that enhancements module can be imported."""
        try:
            from app.core.openapi_enhancements import (
                get_enhanced_openapi_examples,
                get_enhanced_openapi_schemas,
                get_enhanced_security_schemes
            )
            
            # Test functions return valid data
            examples = get_enhanced_openapi_examples()
            schemas = get_enhanced_openapi_schemas() 
            security = get_enhanced_security_schemes()
            
            assert isinstance(examples, dict), "Examples should be a dictionary"
            assert isinstance(schemas, dict), "Schemas should be a dictionary"
            assert isinstance(security, dict), "Security schemes should be a dictionary"
            
        except ImportError:
            pytest.fail("Cannot import OpenAPI enhancements module")

    def test_examples_structure(self):
        """Test that examples have proper structure."""
        from app.core.openapi_enhancements import get_enhanced_openapi_examples
        
        examples = get_enhanced_openapi_examples()
        
        # Check major example categories
        expected_categories = [
            "ocr_file_processing_examples",
            "ocr_url_processing_examples", 
            "response_examples",
            "error_examples",
            "health_response_examples"
        ]
        
        for category in expected_categories:
            assert category in examples, f"Missing example category: {category}"
            assert isinstance(examples[category], dict), f"Category {category} should be dict"

    def test_schemas_completeness(self):
        """Test that schemas cover all OCR models."""
        from app.core.openapi_enhancements import get_enhanced_openapi_schemas
        
        schemas = get_enhanced_openapi_schemas()
        
        # Check major schemas
        expected_schemas = [
            "OCRUrlRequest",
            "OCRResponse",
            "OCRErrorResponse", 
            "OCRImage",
            "OCRMetadata",
            "OCRProcessingInfo"
        ]
        
        for schema_name in expected_schemas:
            assert schema_name in schemas, f"Missing schema: {schema_name}"
            schema = schemas[schema_name]
            assert "type" in schema, f"Schema {schema_name} missing type"
            assert "properties" in schema, f"Schema {schema_name} missing properties"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
