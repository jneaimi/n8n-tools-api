# OCR S3 Integration Documentation

## Overview

The OCR S3 Integration extends the existing OCR API with the ability to upload extracted base64 images to S3-compatible storage and replace them with public URLs in the response. This feature is particularly useful for:

- Reducing response payload size by replacing large base64 images with URLs
- Storing extracted images persistently for future reference
- Enabling image access from web applications and mobile apps
- Supporting various S3-compatible storage providers (AWS S3, MinIO, DigitalOcean Spaces, etc.)

## New Endpoints

### POST /ocr/process-file-s3

Process uploaded files with OCR and upload extracted images to S3.

**Request Format:**
- **Method:** POST
- **Content-Type:** multipart/form-data with JSON body
- **Authentication:** Required (X-API-Key or Authorization: Bearer)

**Request Body (JSON):**
```json
{
  "s3_config": {
    "endpoint": "https://minio.example.com:9000",  // Optional for AWS S3
    "access_key": "AKIAIOSFODNN7EXAMPLE",          // Required
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", // Required
    "bucket_name": "my-ocr-images",                // Required
    "region": "us-west-2"                          // Optional, defaults to us-east-1
  },
  "extract_images": true,                          // Optional, defaults to true
  "include_metadata": true,                        // Optional, defaults to true
  "language_hint": "en",                           // Optional
  "image_upload_prefix": "ocr-images",             // Optional, defaults to "ocr-images"
  "fallback_to_base64": true,                      // Optional, defaults to true
  "upload_timeout_seconds": 30                     // Optional, defaults to 30
}
```

**File Upload:**
- **Parameter:** `file`
- **Supported formats:** PDF, PNG, JPG, JPEG, TIFF
- **Maximum size:** 50MB

### POST /ocr/process-url-s3

Process documents from URLs with OCR and upload extracted images to S3.

**Request Format:**
- **Method:** POST
- **Content-Type:** application/json
- **Authentication:** Required (X-API-Key or Authorization: Bearer)

**Request Body:**
```json
{
  "url": "https://example.com/document.pdf",       // Required
  "s3_config": {
    "endpoint": "https://s3.amazonaws.com",        // Optional for AWS S3
    "access_key": "AKIAIOSFODNN7EXAMPLE",          // Required
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", // Required
    "bucket_name": "my-ocr-images",                // Required
    "region": "us-east-1"                          // Optional
  },
  "extract_images": true,                          // Optional
  "include_metadata": true,                        // Optional
  "language_hint": "es",                           // Optional
  "image_upload_prefix": "url-ocr",                // Optional
  "fallback_to_base64": true,                      // Optional
  "upload_timeout_seconds": 60                     // Optional
}
```

## S3 Configuration

### Required Parameters

- **access_key**: S3 access key ID
- **secret_key**: S3 secret access key  
- **bucket_name**: S3 bucket name for storing images

### Optional Parameters

- **endpoint**: S3-compatible endpoint URL (omit for AWS S3)
- **region**: S3 region (defaults to "us-east-1")

### Bucket Name Requirements

Bucket names must follow AWS S3 naming conventions:
- 3-63 characters long
- Lowercase letters, numbers, hyphens, and periods only
- Must start and end with a letter or number
- Cannot contain consecutive periods or period-hyphen combinations
- Cannot be formatted as an IP address

### Supported S3 Providers

The OCR S3 integration supports any S3-compatible storage provider:

**AWS S3:**
```json
{
  "access_key": "AKIAIOSFODNN7EXAMPLE",
  "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "bucket_name": "my-ocr-bucket",
  "region": "us-west-2"
  // No endpoint needed for AWS S3
}
```

**MinIO:**
```json
{
  "endpoint": "https://minio.example.com:9000",
  "access_key": "minioadmin",
  "secret_key": "minioadmin",
  "bucket_name": "ocr-storage",
  "region": "us-east-1"
}
```

**DigitalOcean Spaces:**
```json
{
  "endpoint": "https://nyc3.digitaloceanspaces.com",
  "access_key": "YOUR_SPACES_KEY",
  "secret_key": "YOUR_SPACES_SECRET",
  "bucket_name": "my-space-name",
  "region": "nyc3"
}
```

## Response Format

### Successful Response

The response format is similar to the standard OCR endpoints, but with images containing S3 URLs instead of base64 data:

```json
{
  "status": "success",
  "message": "OCR processing completed successfully",
  "extracted_text": "Document text content...",
  "pages": [
    {
      "page_number": 1,
      "markdown": "# Page Content\n\nText here...",
      "images": [
        {
          "id": "page1_img1",
          "s3_url": "https://my-bucket.s3.us-west-2.amazonaws.com/ocr-images/20241201/abc123.png",
          "s3_object_key": "ocr-images/20241201/abc123.png", 
          "upload_timestamp": 1704067200.123,
          "format": "png",
          "file_size_bytes": 15420,
          "content_type": "image/png",
          "page_number": 1,
          "sequence_number": 1,
          "coordinates": {
            "x": 100,
            "y": 200, 
            "width": 300,
            "height": 150
          },
          "upload_metadata": {
            "source_location": "pages[0].images[0]",
            "upload_prefix": "ocr-images",
            "upload_success": true
          }
        }
      ]
    }
  ],
  "metadata": {
    "page_count": 1,
    "language": "en",
    "processing_time": 2.5
  },
  "processing_info": {
    "processing_time_ms": 2500.0,
    "source_type": "file_upload_s3",
    "ai_model_used": "mistral-large-latest",
    "pages_processed": 1
  },
  "s3_upload_info": {
    "images_detected": 1,
    "images_uploaded": 1,
    "images_failed": 0,
    "upload_success_rate": 1.0,
    "fallback_used": false,
    "processing_time_ms": 800.0,
    "s3_bucket": "my-bucket",
    "s3_prefix": "ocr-images"
  },
  "n8n_processing_info": {
    "source_type": "file_upload_s3",
    "source_identifier": "document.pdf",
    "processing_time_ms": 2500.0,
    "api_format": "mistral_with_s3",
    "s3_images_uploaded": 1,
    "s3_upload_success_rate": 1.0
  }
}
```

### Error Response

```json
{
  "status": "error",
  "error_code": "S3_CONFIGURATION_ERROR",
  "message": "S3 configuration or connection error",
  "details": {
    "error": "Bucket 'invalid-bucket' does not exist",
    "timestamp": 1704067200.123
  }
}
```

## Features

### Image Upload and URL Replacement

- **Automatic Detection**: Scans OCR responses for base64-encoded images
- **Concurrent Upload**: Uploads multiple images simultaneously for better performance
- **URL Generation**: Generates public URLs for uploaded images
- **Metadata Preservation**: Maintains image metadata (coordinates, format, etc.)

### Fallback Mechanism

When `fallback_to_base64` is enabled (default), the system will:

1. Attempt to upload images to S3
2. If upload fails, keep original base64 data in the response
3. Include error information in `s3_upload_info`

```json
{
  // ... standard response fields ...
  "s3_upload_info": {
    "upload_attempted": true,
    "s3_error": "Connection timeout",
    "fallback_used": true,
    "images_uploaded": 0
  },
  "fallback_images": [
    {
      "id": "img_001",
      "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA...",
      "format": "png"
    }
  ]
}
```

### Error Handling

The S3 integration includes comprehensive error handling:

- **S3 Connection Errors**: Invalid credentials, network issues
- **Configuration Errors**: Missing required fields, invalid bucket names
- **Upload Errors**: Insufficient permissions, storage quota exceeded
- **Timeout Handling**: Configurable timeouts for upload operations

## Usage Examples

### Basic Usage with AWS S3

```bash
curl -X POST "https://api.example.com/ocr/process-file-s3" \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf" \
  -F "json_data={
    \"s3_config\": {
      \"access_key\": \"AKIAIOSFODNN7EXAMPLE\",
      \"secret_key\": \"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\",
      \"bucket_name\": \"my-ocr-bucket\",
      \"region\": \"us-west-2\"
    },
    \"extract_images\": true,
    \"include_metadata\": true
  }"
```

### URL Processing with MinIO

```bash
curl -X POST "https://api.example.com/ocr/process-url-s3" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/document.pdf",
    "s3_config": {
      "endpoint": "https://minio.company.com:9000",
      "access_key": "minio-access-key",
      "secret_key": "minio-secret-key", 
      "bucket_name": "document-images",
      "region": "us-east-1"
    },
    "extract_images": true,
    "image_upload_prefix": "invoices",
    "upload_timeout_seconds": 60
  }'
```

### n8n Integration

For n8n workflows, use the HTTP Request node:

**Node Configuration:**
- **Method**: POST
- **URL**: `https://your-api.com/ocr/process-file-s3`
- **Authentication**: Generic Credential Type
  - **Header Name**: `X-API-Key`
  - **Header Value**: `{{$credentials.api_key}}`

**Request Body:**
```json
{
  "s3_config": {
    "access_key": "{{$credentials.s3_access_key}}",
    "secret_key": "{{$credentials.s3_secret_key}}",
    "bucket_name": "{{$node.parameter.bucket_name}}",
    "region": "us-east-1"
  },
  "extract_images": true,
  "fallback_to_base64": true
}
```

## Performance Considerations

### Upload Performance

- **Concurrent Uploads**: Multiple images are uploaded simultaneously
- **Configurable Timeouts**: Adjust timeouts based on image sizes and network conditions
- **Retry Logic**: Automatic retries for transient failures

### Memory Usage

- **Streaming Uploads**: Images are uploaded directly from memory without temporary files
- **Size Limits**: 10MB per image, configurable minimum size filtering
- **Garbage Collection**: Temporary data is cleaned up immediately after upload

### Network Optimization

- **Content Type Detection**: Proper MIME types for better caching
- **Compression**: Images are uploaded without additional compression
- **Metadata**: Minimal metadata to reduce overhead

## Security Considerations

### Credential Handling

- **SecretStr**: S3 secret keys are wrapped in Pydantic SecretStr for security
- **No Logging**: Credentials are never logged in plain text
- **Memory Protection**: Secrets are cleared from memory when possible

### Access Control

- **Bucket Permissions**: Ensure bucket has appropriate read/write permissions
- **Public URLs**: Uploaded images are accessible via public URLs
- **CORS Configuration**: May need CORS setup for web application access

### Best Practices

1. **Use IAM Roles**: Prefer IAM roles over long-term access keys when possible
2. **Bucket Policies**: Implement appropriate bucket policies for access control
3. **Encryption**: Enable server-side encryption on S3 buckets
4. **Monitoring**: Monitor S3 usage and access patterns
5. **Lifecycle Policies**: Implement lifecycle policies for automatic cleanup

## Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `S3_CONFIGURATION_ERROR` | Invalid S3 configuration | Check credentials and bucket name |
| `S3_CONNECTION_ERROR` | Cannot connect to S3 service | Verify endpoint and network connectivity |
| `S3_UPLOAD_ERROR` | Image upload failed | Check permissions and storage quota |
| `INVALID_REQUEST_BODY` | Malformed request body | Validate JSON format and required fields |
| `AUTHENTICATION_FAILED` | Invalid API key | Verify API key is correct |
| `FILE_TOO_LARGE` | File exceeds size limit | Reduce file size or contact support |

## Rate Limits

S3 endpoints are subject to the same rate limits as standard OCR endpoints:
- **API Key Tier**: Based on your API key tier
- **Concurrent Requests**: Limited per API key
- **S3 Operations**: Additional limits may apply from S3 provider

## Migration from Standard OCR

To migrate from standard OCR endpoints to S3 endpoints:

1. **Update Endpoint URLs**: Change from `/process-file` to `/process-file-s3`
2. **Add S3 Configuration**: Include `s3_config` in request body
3. **Update Response Parsing**: Handle S3 URLs instead of base64 data
4. **Test Fallback**: Verify fallback behavior with invalid S3 config
5. **Monitor Performance**: Check upload times and success rates

## Troubleshooting

### Common Issues

**"Bucket does not exist" error:**
- Verify bucket name spelling and region
- Ensure bucket exists in the specified region
- Check that credentials have access to the bucket

**"Access denied" error:**
- Verify S3 credentials are correct
- Check bucket permissions and IAM policies
- Ensure credentials have `s3:PutObject` permission

**Upload timeouts:**
- Increase `upload_timeout_seconds` parameter
- Check network connectivity to S3 endpoint
- Consider reducing image quality/size

**Images not replaced with URLs:**
- Verify images are detected in OCR response
- Check S3 upload success in `s3_upload_info`
- Enable fallback to see original base64 data

### Debug Mode

For debugging, set `fallback_to_base64: false` to see S3 errors directly instead of falling back to base64 data.

## API Reference

For complete API documentation with interactive examples, visit:
- **Swagger UI**: `https://your-api.com/docs`
- **ReDoc**: `https://your-api.com/redoc`
- **OpenAPI Spec**: `https://your-api.com/openapi.json`