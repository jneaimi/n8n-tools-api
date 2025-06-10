# N8N Integration Examples for OCR API

## Quick Start Guide

This guide provides practical examples for integrating the OCR API with n8n workflows.

## Basic Setup

### HTTP Request Node Configuration

1. **Method**: POST
2. **URL**: `{{$parameter['api_base_url']}}/api/v1/ocr/process-file`
3. **Authentication**: None (use headers)
4. **Headers**:
   ```json
   {
     "X-API-Key": "={{$parameter['mistral_api_key']}}"
   }
   ```
5. **Body Type**: Form-Data (Multipart)

### Required Parameters

```javascript
// Workflow Parameters (Set node)
{
  "api_base_url": "https://your-api-domain.com",
  "mistral_api_key": "your_mistral_api_key_here",
  "extract_images": true,
  "include_metadata": true,
  "language_hint": "en"
}
```

## Example Workflows

### 1. Simple PDF OCR Processing

**Workflow: Manual Trigger → OCR Processing → Save Results**

```json
{
  "nodes": [
    {
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "parameters": {},
      "position": [250, 300]
    },
    {
      "name": "OCR Processing",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "={{$parameter['api_base_url']}}/api/v1/ocr/process-file",
        "sendHeaders": true,
        "headerParameters": {
          "X-API-Key": "={{$parameter['mistral_api_key']}}"
        },
        "sendBody": true,
        "bodyContentType": "multipart-form-data",
        "bodyParameters": {
          "file": "={{$binary.data}}",
          "extract_images": "={{$parameter['extract_images']}}",
          "include_metadata": "={{$parameter['include_metadata']}}",
          "language_hint": "={{$parameter['language_hint']}}"
        }
      },
      "position": [450, 300]
    },
    {
      "name": "Process Results",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "code": "// Extract OCR results\nconst ocrData = $input.first().json;\n\n// Get extracted text\nconst extractedText = ocrData.extracted_text;\n\n// Get metadata\nconst metadata = ocrData.metadata || {};\nconst pageCount = metadata.page_count;\nconst language = metadata.language;\n\n// Get processing info\nconst processingTime = ocrData.processing_info.processing_time_ms;\nconst confidence = ocrData.processing_info.confidence_score;\n\n// Format results\nreturn [{\n  json: {\n    text: extractedText,\n    pageCount: pageCount,\n    language: language,\n    processingTimeMs: processingTime,\n    confidence: confidence,\n    timestamp: new Date().toISOString()\n  }\n}];"
      },
      "position": [650, 300]
    }
  ],
  "connections": {
    "Manual Trigger": {
      "main": [["OCR Processing"]]
    },
    "OCR Processing": {
      "main": [["Process Results"]]
    }
  }
}
```

### 2. URL-Based Document Processing

**Workflow: Webhook → Download URL → OCR Processing → Email Results**

```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "process-document-url",
        "httpMethod": "POST"
      },
      "position": [250, 300]
    },
    {
      "name": "OCR from URL",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "={{$parameter['api_base_url']}}/api/v1/ocr/process-url",
        "sendHeaders": true,
        "headerParameters": {
          "X-API-Key": "={{$parameter['mistral_api_key']}}",
          "Content-Type": "application/json"
        },
        "sendBody": true,
        "bodyContentType": "json",
        "jsonParameters": {
          "url": "={{$json['document_url']}}"
        }
      },
      "position": [450, 300]
    },
    {
      "name": "Format Results",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "code": "const ocrData = $input.first().json;\n\n// Create formatted report\nconst report = `\n# OCR Processing Report\n\n**Document URL**: ${$('Webhook').first().json.document_url}\n**Processing Time**: ${ocrData.processing_info.processing_time_ms}ms\n**Confidence Score**: ${(ocrData.processing_info.confidence_score * 100).toFixed(1)}%\n**Pages Processed**: ${ocrData.processing_info.pages_processed}\n**Language**: ${ocrData.metadata?.language || 'Unknown'}\n\n## Extracted Text\n\n${ocrData.extracted_text}\n\n## Metadata\n\n- **Title**: ${ocrData.metadata?.title || 'N/A'}\n- **Author**: ${ocrData.metadata?.author || 'N/A'}\n- **Creation Date**: ${ocrData.metadata?.creation_date || 'N/A'}\n- **Page Count**: ${ocrData.metadata?.page_count || 'N/A'}\n`;\n\nreturn [{\n  json: {\n    report: report,\n    raw_data: ocrData,\n    summary: {\n      text_length: ocrData.extracted_text.length,\n      word_count: ocrData.extracted_text.split(/\\s+/).length,\n      image_count: (ocrData.images || []).length\n    }\n  }\n}];"
      },
      "position": [650, 300]
    },
    {
      "name": "Send Email",
      "type": "n8n-nodes-base.emailSend",
      "parameters": {
        "fromEmail": "ocr-service@your-domain.com",
        "toEmail": "={{$('Webhook').first().json.notify_email}}",
        "subject": "OCR Processing Complete",
        "message": "={{$json['report']}}",
        "attachments": "={{$json['raw_data']}}"
      },
      "position": [850, 300]
    }
  ]
}
```

### 3. Batch Processing with Error Handling

**Workflow: Google Drive → Validate → OCR → Handle Errors → Save Results**

```json
{
  "nodes": [
    {
      "name": "Google Drive Trigger",
      "type": "n8n-nodes-base.googleDriveTrigger",
      "parameters": {
        "folderId": "your_folder_id",
        "event": "fileCreated"
      },
      "position": [250, 300]
    },
    {
      "name": "Download File",
      "type": "n8n-nodes-base.googleDrive",
      "parameters": {
        "operation": "download",
        "fileId": "={{$json['id']}}"
      },
      "position": [450, 300]
    },
    {
      "name": "Validate File",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "={{$parameter['api_base_url']}}/api/v1/ocr/validate",
        "sendBody": true,
        "bodyContentType": "multipart-form-data",
        "bodyParameters": {
          "file": "={{$binary.data}}"
        }
      },
      "position": [650, 300]
    },
    {
      "name": "Check Validation",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json['status']}}",
              "operation": "equal",
              "value2": "valid"
            }
          ]
        }
      },
      "position": [850, 300]
    },
    {
      "name": "Process OCR",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "={{$parameter['api_base_url']}}/api/v1/ocr/process-file",
        "sendHeaders": true,
        "headerParameters": {
          "X-API-Key": "={{$parameter['mistral_api_key']}}"
        },
        "sendBody": true,
        "bodyContentType": "multipart-form-data",
        "bodyParameters": {
          "file": "={{$binary.data}}",
          "extract_images": true,
          "include_metadata": true
        },
        "options": {
          "timeout": 300000,
          "retry": {
            "enabled": true,
            "maxAttempts": 3,
            "waitBetweenAttempts": 5000
          }
        }
      },
      "position": [1050, 250]
    },
    {
      "name": "Handle OCR Error",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json['status']}}",
              "operation": "equal",
              "value2": "error"
            }
          ]
        }
      },
      "position": [1250, 250]
    },
    {
      "name": "Log Validation Error",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "code": "console.log('File validation failed:', $input.first().json);\nreturn $input.all();"
      },
      "position": [1050, 350]
    },
    {
      "name": "Retry or Log Error",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "code": "const errorData = $input.first().json;\nconst errorCode = errorData.error_code;\n\n// Handle rate limiting\nif (errorCode === 'OCR_API_RATE_LIMIT') {\n  const retryAfter = errorData.details?.retry_after_seconds || 60;\n  console.log(`Rate limited. Retry after ${retryAfter} seconds`);\n  \n  // Could implement wait logic here\n  return [{\n    json: {\n      action: 'retry',\n      wait_seconds: retryAfter,\n      original_error: errorData\n    }\n  }];\n}\n\n// Handle authentication errors\nif (errorCode === 'OCR_API_AUTH_FAILED') {\n  console.error('Authentication failed. Check API key.');\n  return [{\n    json: {\n      action: 'auth_error',\n      error: 'Check Mistral API key configuration'\n    }\n  }];\n}\n\n// Log other errors\nconsole.error('OCR processing failed:', errorData);\nreturn [{\n  json: {\n    action: 'log_error',\n    error_code: errorCode,\n    error_message: errorData.message\n  }\n}];"
      },
      "position": [1450, 200]
    },
    {
      "name": "Save Success Results",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "append",
        "sheetId": "your_sheet_id",
        "range": "OCR_Results",
        "valueInputOption": "USER_ENTERED",
        "values": {
          "Filename": "={{$('Google Drive Trigger').first().json.name}}",
          "Processing_Time_Ms": "={{$json.processing_info.processing_time_ms}}",
          "Confidence_Score": "={{$json.processing_info.confidence_score}}",
          "Pages_Processed": "={{$json.processing_info.pages_processed}}",
          "Text_Length": "={{$json.extracted_text.length}}",
          "Language": "={{$json.metadata?.language}}",
          "Timestamp": "={{new Date().toISOString()}}"
        }
      },
      "position": [1450, 300]
    }
  ]
}
```

## Error Handling Patterns

### 1. Rate Limit Handling

```javascript
// In Code node - Handle rate limiting
const response = $input.first().json;

if (response.status === 'error' && response.error_code === 'OCR_API_RATE_LIMIT') {
  const retryAfter = response.details?.retry_after_seconds || 60;
  
  // Wait and retry
  await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
  
  // Return data to retry the OCR request
  return [{
    json: {
      retry: true,
      wait_time: retryAfter,
      original_input: $('Previous Node').first().json
    }
  }];
}

// Continue with normal processing
return $input.all();
```

### 2. File Validation Before Processing

```javascript
// Validation check before OCR
const validationResponse = $input.first().json;

if (validationResponse.status !== 'valid') {
  // Handle validation errors
  const errorCode = validationResponse.error_code;
  
  switch (errorCode) {
    case 'OCR_FILE_TOO_LARGE':
      console.log('File too large, consider splitting');
      break;
    case 'OCR_INVALID_FILE_FORMAT':
      console.log('Unsupported format, convert file first');
      break;
    default:
      console.log('Validation failed:', validationResponse.message);
  }
  
  // Skip OCR processing
  return [];
}

// Proceed with OCR
return $input.all();
```

### 3. Authentication Error Recovery

```javascript
// Check for auth errors and provide guidance
const response = $input.first().json;

if (response.error_code === 'OCR_API_AUTH_FAILED') {
  // Log authentication failure
  console.error('OCR API authentication failed');
  
  // Could trigger notification workflow
  return [{
    json: {
      error: 'authentication_failed',
      action_required: 'Check Mistral API key configuration',
      troubleshooting: [
        'Verify API key is valid',
        'Check key has sufficient quota', 
        'Ensure key is correctly set in workflow parameters'
      ]
    }
  }];
}
```

## Performance Optimization

### 1. Parallel Processing

```javascript
// For multiple files, process in batches
const files = $input.all();
const batchSize = 3; // Process 3 files at a time

const batches = [];
for (let i = 0; i < files.length; i += batchSize) {
  batches.push(files.slice(i, i + batchSize));
}

// Process each batch
const results = [];
for (const batch of batches) {
  const batchResults = await Promise.all(
    batch.map(file => processOCR(file))
  );
  results.push(...batchResults);
  
  // Wait between batches to respect rate limits
  await new Promise(resolve => setTimeout(resolve, 2000));
}

return results;
```

### 2. Caching Results

```javascript
// Cache OCR results to avoid reprocessing
const fileHash = $json.file_hash || $json.filename;
const cacheKey = `ocr_${fileHash}`;

// Check cache first (using Redis/database)
const cachedResult = await checkCache(cacheKey);
if (cachedResult) {
  return [{
    json: {
      ...cachedResult,
      from_cache: true
    }
  }];
}

// Process with OCR and cache result
const ocrResult = await processOCR($json);
await saveToCache(cacheKey, ocrResult, 3600); // Cache for 1 hour

return [{
  json: {
    ...ocrResult,
    from_cache: false
  }
}];
```

## Monitoring and Alerting

### 1. Health Check Workflow

```javascript
// Regular health check
const healthResponse = await fetch('{{$parameter.api_base_url}}/api/v1/ocr/health');
const healthData = await healthResponse.json();

if (healthData.health_score < 0.8) {
  // Send alert
  console.warn('OCR service health degraded:', healthData);
  
  // Could trigger notification
  return [{
    json: {
      alert: 'health_degraded',
      health_score: healthData.health_score,
      status: healthData.status,
      recommendations: healthData.recommendations
    }
  }];
}

return [{
  json: {
    status: 'healthy',
    health_score: healthData.health_score
  }
}];
```

### 2. Error Rate Monitoring

```javascript
// Track error rates over time
const errors = $input.all().filter(item => 
  item.json.status === 'error'
);

const total = $input.all().length;
const errorRate = errors.length / total;

if (errorRate > 0.1) { // 10% error rate threshold
  return [{
    json: {
      alert: 'high_error_rate',
      error_rate: errorRate,
      total_requests: total,
      error_count: errors.length,
      timestamp: new Date().toISOString()
    }
  }];
}
```

## Best Practices

1. **Always validate files** before OCR processing
2. **Implement retry logic** for rate limits and transient errors
3. **Cache results** for frequently processed documents
4. **Monitor health** and error rates regularly
5. **Use appropriate timeouts** (2-5 minutes for large files)
6. **Handle authentication errors** gracefully
7. **Process files in batches** to respect rate limits
8. **Log processing metrics** for optimization

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Authentication failures | Verify Mistral API key is valid and has quota |
| Rate limit exceeded | Implement retry with exponential backoff |
| File too large | Split documents or compress images |
| Timeout errors | Increase timeout or process smaller files |
| Invalid file format | Convert to supported format (PDF, PNG, JPG, TIFF) |
| Network errors | Implement retry logic and check connectivity |

### Debug Workflow

```javascript
// Debug node to inspect data
console.log('Input data:', JSON.stringify($input.first().json, null, 2));
console.log('Binary data info:', $binary);
console.log('Node parameters:', $parameter);
console.log('Previous node data:', $('Previous Node').first());

// Return debug info
return [{
  json: {
    debug: true,
    input_summary: $input.first().json,
    timestamp: new Date().toISOString()
  }
}];
```
