# N8N Tools API - Integration Guide

## Overview

The N8N Tools API is specifically designed for seamless integration with n8n workflow automation. This guide provides step-by-step instructions for setting up and using the API in your n8n workflows.

## Quick Start

### 1. API Health Check
Before using the API in workflows, verify it's running:
```
GET http://your-api-domain:8000/health
```

### 2. Get n8n Integration Information
Access comprehensive integration details:
```
GET http://your-api-domain:8000/n8n
```

### 3. Access Interactive Documentation
View full API documentation:
```
http://your-api-domain:8000/docs
```

## n8n Setup Instructions

### Basic HTTP Request Node Configuration

1. **Add HTTP Request Node** to your workflow
2. **Configure base settings**:
   - **URL**: `http://your-api-domain:8000/api/v1/pdf/[endpoint]`
   - **Method**: `POST` (for most operations)
   - **Authentication**: None required

### File Upload Operations

For endpoints that require PDF file uploads:

1. **Set Request Format**: `Multipart/Form-Data`
2. **Add Form Data**:
   - **Key**: `file`
   - **Type**: `File`
   - **Value**: Connect from previous node or manual upload

3. **Additional Parameters** (as needed):
   - For split operations: `ranges`, `batch_size`
   - For merge operations: `merge_strategy`, `preserve_metadata`

### Response Handling

#### JSON Responses (validation, info, metadata)
- **Response Format**: `JSON`
- **Use for**: Validation, file information, metadata extraction

#### File Downloads (split, merge operations)
- **Response Format**: `File`
- **Content Types**: `application/pdf`, `application/zip`
- **Headers**: Check `X-*` headers for processing information

## Common Workflow Patterns

### Pattern 1: PDF Validation & Processing
```
[Start] → [HTTP: Validate PDF] → [If: Valid?] → [HTTP: Process PDF] → [Save Result]
                                     ↓ No
                                [Error Handler]
```

### Pattern 2: Batch PDF Processing
```
[Start] → [Split to Batches] → [Process Each Batch] → [Merge Results] → [Final Output]
```

### Pattern 3: Conditional Processing
```
[Start] → [Get PDF Info] → [If: >10 pages?] → [Split] → [Process Parts]
                              ↓ No
                           [Process Whole]
```

## API Endpoints Reference

### Core Operations

#### PDF Validation
- **Endpoint**: `/api/v1/pdf/validate`
- **Method**: `POST`
- **Use Case**: Validate PDF before processing
- **Response**: JSON with validation status

#### PDF Metadata
- **Endpoint**: `/api/v1/pdf/metadata`
- **Method**: `POST`
- **Use Case**: Extract document information
- **Response**: JSON with metadata

#### PDF Split by Ranges
- **Endpoint**: `/api/v1/pdf/split/ranges`
- **Method**: `POST`
- **Parameters**: `file`, `ranges` (e.g., "1-3,5,7-9")
- **Response**: ZIP file with split PDFs

#### PDF Merge
- **Endpoint**: `/api/v1/pdf/merge`
- **Method**: `POST`
- **Parameters**: `files[]`, `merge_strategy`, `preserve_metadata`
- **Response**: Single merged PDF file

### Advanced Operations

#### Batch Split
- **Endpoint**: `/api/v1/pdf/split/batch`
- **Parameters**: `file`, `batch_size`, `output_prefix`

#### Page Selection Merge
- **Endpoint**: `/api/v1/pdf/merge/pages`
- **Parameters**: `files[]`, `page_selections` (JSON array)

## Error Handling in n8n

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request (validation error)
- **413**: File too large (>50MB)
- **500**: Server error

### Recommended Error Handling
1. Add **If Node** after HTTP Request
2. **Condition**: `{{ $node["HTTP Request"].json.status === "success" }}`
3. **True**: Continue workflow
4. **False**: Handle error (log, notify, retry)

## Best Practices

### Performance Optimization
1. **Validate files first** before processing
2. **Use batch operations** for multiple files
3. **Implement error handling** for all HTTP requests
4. **Check response headers** for processing information

### Security Considerations
1. **Validate file types** before upload
2. **Set size limits** in n8n workflows
3. **Use HTTPS** in production
4. **Implement rate limiting** if needed

### Workflow Design
1. **Start with validation** for all PDF operations
2. **Use conditional logic** based on file properties
3. **Implement retries** for network errors
4. **Log processing results** for monitoring

## Troubleshooting

### Common Issues

#### File Upload Errors
- Ensure `multipart/form-data` format
- Check file size (max 50MB)
- Verify PDF format

#### Response Format Errors
- Use "File" format for PDF/ZIP responses
- Use "JSON" format for validation/info responses

#### Network Errors
- Check API health endpoint
- Verify URL and port configuration
- Implement retry logic

### Debug Steps
1. Test API endpoints directly with curl
2. Check n8n execution logs
3. Verify HTTP request configuration
4. Test with small PDF files first

## Example Workflows

### Simple PDF Split Workflow
```json
{
  "nodes": [
    {
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger"
    },
    {
      "name": "Validate PDF",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://api:8000/api/v1/pdf/validate",
        "method": "POST",
        "sendBody": true,
        "bodyFormat": "multipart-form-data",
        "bodyParameters": {
          "parameters": [
            {
              "name": "file",
              "value": "={{$binary.data}}"
            }
          ]
        }
      }
    },
    {
      "name": "Split PDF",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://api:8000/api/v1/pdf/split/ranges",
        "method": "POST",
        "sendBody": true,
        "bodyFormat": "multipart-form-data",
        "bodyParameters": {
          "parameters": [
            {
              "name": "file",
              "value": "={{$binary.data}}"
            },
            {
              "name": "ranges",
              "value": "1-5,10-15"
            }
          ]
        },
        "responseFormat": "file"
      }
    }
  ]
}
```

## Support

- **API Documentation**: `/docs`
- **n8n Integration Info**: `/n8n`
- **Health Check**: `/health`
- **OpenAPI Schema**: `/openapi.json`

For additional support, refer to the interactive documentation at `/docs` or check the n8n integration endpoint at `/n8n`.
