# OCR API Documentation

This directory contains comprehensive documentation for the AI-powered OCR API using Mistral AI, specifically designed for n8n workflow automation.

## 📁 Documentation Structure

```
docs/api/
├── README.md                           # This file - documentation overview
├── ocr-api-specification.md           # Complete API specification
├── n8n-integration-guide.md           # n8n workflow examples and patterns
├── test_openapi_documentation.py      # Test suite for documentation accuracy
└── examples/                          # Additional examples (if needed)
```

## 📚 Available Documentation

### 1. [OCR API Specification](./ocr-api-specification.md)
**Complete technical reference for the OCR API**

- **Authentication**: API key methods and security requirements
- **Endpoints**: Detailed documentation for all 6 OCR endpoints
- **Request/Response Schemas**: Complete data models with examples
- **Error Handling**: 27 standardized error codes with descriptions
- **Rate Limiting**: Request limits and best practices
- **File Constraints**: Supported formats and size limitations
- **Performance Guidelines**: Processing times and optimization tips

**Key Features Documented:**
- ✅ File upload processing (PDF, PNG, JPG, JPEG, TIFF)
- ✅ URL-based document processing
- ✅ Text extraction with Markdown formatting
- ✅ Image extraction with coordinate mapping
- ✅ Metadata extraction and analysis
- ✅ Comprehensive error system
- ✅ Health monitoring and metrics

### 2. [N8N Integration Guide](./n8n-integration-guide.md)
**Practical examples for n8n workflow automation**

- **Quick Start**: Basic HTTP Request node configuration
- **Example Workflows**: Complete n8n workflow JSON examples
- **Error Handling Patterns**: Robust error handling strategies
- **Performance Optimization**: Batch processing and caching
- **Monitoring**: Health checks and alerting workflows
- **Best Practices**: Production deployment guidelines

**Example Workflows Included:**
- ✅ Simple PDF OCR processing
- ✅ URL-based document processing with email notifications
- ✅ Batch processing with comprehensive error handling
- ✅ Rate limit handling and retry logic
- ✅ Health monitoring and alerting

### 3. [Documentation Test Suite](./test_openapi_documentation.py)
**Automated tests to ensure documentation accuracy**

- **OpenAPI Schema Validation**: Verifies schema completeness and structure
- **Example Validation**: Tests that all examples are valid and realistic
- **Endpoint Coverage**: Ensures all implemented endpoints are documented
- **Security Documentation**: Validates authentication and authorization docs
- **Integration Testing**: Verifies examples work with actual API

**Test Categories:**
- ✅ OpenAPI schema structure and completeness
- ✅ Security scheme definitions
- ✅ Error response examples and structure
- ✅ Request/response model validation
- ✅ Documentation file completeness
- ✅ Example data realism and accuracy

## 🚀 Quick Start

### For API Consumers

1. **Start with the [API Specification](./ocr-api-specification.md)**
2. **Review authentication requirements**
3. **Test with the `/auth/test` endpoint**
4. **Validate files using `/validate` endpoint**
5. **Process documents with `/process-file` or `/process-url`**

### For n8n Users

1. **Follow the [N8N Integration Guide](./n8n-integration-guide.md)**
2. **Copy the HTTP Request node configuration**
3. **Set up your workflow parameters**
4. **Implement error handling patterns**
5. **Test with sample documents**

### For Developers

1. **Review the [OpenAPI Specification](../../../openapi.json)**
2. **Run the documentation tests**
3. **Generate client SDKs using OpenAPI tools**
4. **Implement based on the documented schemas**

## 🔧 API Overview

### Base URL
```
Production: https://your-production-domain.com/api/v1/ocr
Development: http://localhost:8000/api/v1/ocr
```

### Authentication
```http
X-API-Key: your_mistral_api_key
# OR
Authorization: Bearer your_mistral_api_key
```

### Key Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/` | GET | Service status and capabilities | No |
| `/health` | GET | Detailed health metrics | No |
| `/auth/test` | POST | Test API key authentication | Yes |
| `/validate` | POST | Validate file before processing | No |
| `/process-file` | POST | Process uploaded files | Yes |
| `/process-url` | POST | Process documents from URLs | Yes |

### Supported File Types
- **PDF**: Adobe PDF documents (.pdf)
- **Images**: PNG (.png), JPEG (.jpg, .jpeg), TIFF (.tiff)
- **Size Limit**: 50MB maximum per file
- **Processing**: AI-powered OCR using Mistral AI

### Rate Limits
- **Per Minute**: 60 requests
- **Per Hour**: 1000 requests
- **Concurrent**: 10 maximum active requests

## 📊 Documentation Features

### ✅ Comprehensive Coverage
- **All Endpoints**: Complete documentation for every API endpoint
- **All Error Codes**: 27 standardized error codes with examples
- **All Data Models**: Request/response schemas with validation rules
- **All Authentication Methods**: X-API-Key and Bearer token examples

### ✅ n8n Optimization
- **Workflow Examples**: Complete n8n workflow JSON configurations
- **Error Handling**: Robust patterns for production workflows
- **Performance Tips**: Optimization strategies for large-scale processing
- **Monitoring**: Health check and alerting workflow examples

### ✅ Developer Experience
- **Interactive Examples**: Copy-paste ready code samples
- **Realistic Data**: All examples use realistic, working data
- **Error Scenarios**: Comprehensive error handling documentation
- **Test Suite**: Automated validation of documentation accuracy

### ✅ Production Ready
- **Security Guidelines**: Authentication and authorization best practices
- **Performance Metrics**: Processing times and optimization recommendations
- **Troubleshooting**: Common issues and solutions
- **Monitoring**: Health checking and alerting strategies

## 🧪 Testing Documentation

### Run Documentation Tests
```bash
# Install test dependencies
pip install pytest requests pillow reportlab

# Run all documentation tests
pytest docs/api/test_openapi_documentation.py -v

# Run specific test categories
pytest docs/api/test_openapi_documentation.py::TestOCRAPIDocumentation -v
pytest docs/api/test_openapi_documentation.py::TestOCRDocumentationFiles -v
```

### Test Categories

1. **OpenAPI Schema Tests**
   - Schema structure validation
   - Component completeness
   - Security scheme definitions
   - Example validation

2. **Documentation File Tests**
   - File existence and readability
   - Section completeness
   - Example accuracy
   - Error code coverage

3. **Integration Tests** (require valid API key)
   - Authentication testing
   - Endpoint accessibility
   - Example functionality

### Continuous Integration

The documentation tests can be integrated into CI/CD pipelines to ensure:
- Documentation stays synchronized with implementation
- Examples remain valid and functional
- OpenAPI schema is complete and accurate
- Security requirements are properly documented

## 🔄 Documentation Maintenance

### Updating Documentation

When making API changes:

1. **Update Implementation First**
2. **Run Documentation Tests** to identify outdated docs
3. **Update API Specification** with new endpoints/models
4. **Update n8n Examples** if workflow patterns change
5. **Add New Test Cases** for new functionality
6. **Verify All Tests Pass**

### Adding New Examples

When adding new examples:

1. **Test Examples Work** with actual API
2. **Follow Existing Patterns** for consistency
3. **Include Error Handling** where appropriate
4. **Add Test Cases** to verify example accuracy
5. **Update This README** if new sections are added

### Version Management

Documentation versioning follows the API version:
- **Major Changes**: New sections, restructured content
- **Minor Changes**: New examples, additional details
- **Patch Changes**: Corrections, clarifications, updated examples

## 📖 External Resources

### OpenAPI/Swagger Tools
- **Swagger UI**: Interactive API documentation at `/docs`
- **ReDoc**: Alternative documentation view at `/redoc`
- **OpenAPI Schema**: Machine-readable schema at `/openapi.json`

### n8n Resources
- **n8n Documentation**: [https://docs.n8n.io](https://docs.n8n.io)
- **HTTP Request Node**: [n8n HTTP Request Documentation](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
- **Workflow Examples**: Available at `/n8n` endpoint

### Mistral AI Resources
- **Mistral AI Documentation**: [https://docs.mistral.ai](https://docs.mistral.ai)
- **OCR Model Documentation**: Mistral OCR API reference
- **API Key Management**: Mistral AI console

## 🆘 Support

### Documentation Issues
- **Bug Reports**: Use the issue tracker for documentation errors
- **Feature Requests**: Suggest improvements to documentation
- **Questions**: Use discussions for documentation questions

### API Support
- **Technical Issues**: Check `/health` endpoint first
- **Authentication Problems**: Verify API key with `/auth/test`
- **Rate Limiting**: Monitor response headers and implement backoff
- **Processing Errors**: Check file validation and error codes

### n8n Integration Support
- **Workflow Issues**: Review error handling patterns
- **Performance Problems**: Check optimization guidelines
- **Authentication Setup**: Follow step-by-step setup guide
- **Example Problems**: Run documentation tests to verify

---

**Last Updated**: June 2025  
**API Version**: 1.0.0  
**Documentation Version**: 1.0.0
