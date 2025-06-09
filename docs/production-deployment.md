# Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the **N8N Tools API - PDF Manipulation Service** in a production environment. It covers deployment options, security considerations, monitoring, and maintenance procedures for optimal performance and reliability.

## Prerequisites

### System Requirements
- **Docker Engine**: 20.10+ or Docker Desktop
- **Docker Compose**: 2.0+ (for multi-container deployments)
- **Memory**: 1GB minimum, 2GB recommended
- **Storage**: 10GB minimum for container images and temporary files
- **CPU**: 2 cores recommended for optimal performance

### Network Requirements
- Outbound internet access for image pulls and dependency updates
- Inbound access on port 8000 (configurable)
- Optional: Load balancer for high-availability deployments

## Deployment Options

### Docker Deployment (Recommended)

The service is containerized using Docker for consistent deployments across environments.

#### Single Container Deployment

```bash
# Clone the repository
git clone <your-repository-url>
cd n8n-tools

# Build the production image
docker build -t n8n-tools-api:latest .

# Run the container
docker run -d \
  --name n8n-tools-api \
  -p 8000:8000 \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  -e MAX_FILE_SIZE_MB=50 \
  -e CORS_ORIGINS="https://your-n8n-domain.com" \
  --restart unless-stopped \
  n8n-tools-api:latest
```

#### Docker Compose Deployment (Recommended)

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f n8n-tools-api
```

### Kubernetes Deployment

For larger scale deployments, Kubernetes manifests can be created:

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: n8n-tools-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: n8n-tools-api
  template:
    metadata:
      labels:
        app: n8n-tools-api
    spec:
      containers:
      - name: api
        image: n8n-tools-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEBUG
          value: "false"
        - name: LOG_LEVEL
          value: "INFO"
        - name: MAX_FILE_SIZE_MB
          value: "50"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Environment Configuration

### Core Environment Variables

| Variable | Description | Default | Production Recommendation |
|----------|-------------|---------|--------------------------|
| `DEBUG` | Enable debug mode | `true` | `false` |
| `LOG_LEVEL` | Logging level | `INFO` | `INFO` or `WARNING` |
| `APP_HOST` | Host binding | `0.0.0.0` | `0.0.0.0` |
| `APP_PORT` | Service port | `8000` | `8000` |
| `MAX_FILE_SIZE_MB` | Max upload size | `50` | Set based on requirements |
| `TEMP_DIR` | Temporary files directory | `/tmp/n8n-tools` | Mount dedicated volume |
| `CLEANUP_AFTER_HOURS` | File cleanup interval | `1` | `1` (keep low for security) |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | Specific domain list |

### Security Environment Variables

| Variable | Description | Production Value |
|----------|-------------|-----------------|
| `SECRET_KEY` | Application secret | Generate secure 32+ char key |
| `CORS_ORIGINS` | CORS allowed origins | `"https://your-n8n.domain.com,https://app.n8n.io"` |

### AI Features Configuration (Optional)

If using AI PDF features, configure these variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `AI_PDF_MISTRAL_API_KEY` | Mistral AI API key | Yes |
| `AI_PDF_MISTRAL_MODEL` | AI model to use | No |
| `AI_PDF_MAX_PAGES_PER_REQUEST` | Max pages per AI request | No |

## Security Hardening

### Container Security

1. **Non-root User**: The container runs as non-root user `appuser` (already configured)

2. **Resource Limits**: Production compose file includes CPU and memory limits:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2.0'
         memory: 1G
       reservations:
         cpus: '1.0'
         memory: 512M
   ```

3. **Read-only Filesystem**: Consider mounting application directory as read-only:
   ```yaml
   volumes:
     - /app:/app:ro
     - temp_storage:/tmp/n8n-tools
   ```

### Network Security

1. **Reverse Proxy Setup** (Recommended):
   ```nginx
   # nginx.conf
   server {
       listen 443 ssl;
       server_name api.your-domain.com;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Rate limiting
           limit_req zone=api burst=10 nodelay;
       }
   }
   ```

2. **Firewall Configuration**:
   ```bash
   # Allow only necessary ports
   ufw allow 22/tcp      # SSH
   ufw allow 80/tcp      # HTTP
   ufw allow 443/tcp     # HTTPS
   ufw deny 8000/tcp     # Block direct API access
   ufw enable
   ```

### API Security

1. **API Key Authentication** (Optional Enhancement):
   Add to FastAPI middleware:
   ```python
   @app.middleware("http")
   async def api_key_middleware(request: Request, call_next):
       if request.url.path.startswith("/api/"):
           api_key = request.headers.get("X-API-Key")
           if not api_key or api_key != os.getenv("API_KEY"):
               return JSONResponse(
                   status_code=401,
                   content={"detail": "Invalid API key"}
               )
       return await call_next(request)
   ```

### File Security

1. **Temporary File Management**: 
   - Files are automatically cleaned up after processing
   - Set `CLEANUP_AFTER_HOURS=1` for frequent cleanup
   - Mount separate volume for temp files

2. **File Size Limits**: 
   - Default 50MB limit via `MAX_FILE_SIZE_MB`
   - Prevents resource exhaustion attacks

## Monitoring and Observability

### Health Checks

The service includes built-in health monitoring:

```bash
# Basic health check
curl -f http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2025-06-09T10:30:00Z",
  "version": "1.0.0"
}
```

### Logging Configuration

1. **Production Logging Setup**:
   ```yaml
   # docker-compose.prod.yml
   services:
     n8n-tools-api:
       environment:
         - LOG_LEVEL=INFO
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

2. **Log Aggregation** (Optional):
   ```yaml
   # Add Fluentd or similar for centralized logging
   logging:
     driver: fluentd
     options:
       fluentd-address: localhost:24224
       tag: n8n-tools-api
   ```

### Metrics and Monitoring

1. **Application Metrics**:
   Add Prometheus instrumentation (optional enhancement):
   ```python
   from prometheus_fastapi_instrumentator import Instrumentator
   
   instrumentator = Instrumentator()
   instrumentator.instrument(app).expose(app)
   ```

2. **Container Monitoring**:
   ```yaml
   # docker-compose.monitoring.yml
   version: '3.8'
   services:
     prometheus:
       image: prom/prometheus
       ports:
         - "9090:9090"
       volumes:
         - ./prometheus.yml:/etc/prometheus/prometheus.yml
   
     grafana:
       image: grafana/grafana
       ports:
         - "3000:3000"
       environment:
         - GF_SECURITY_ADMIN_PASSWORD=admin
   ```

### Alerting Setup

Recommended alerts to configure:

1. **Service Health**: Alert if health check fails
2. **High Error Rate**: Alert if 5xx responses > 5%
3. **Resource Usage**: Alert if CPU > 80% or Memory > 85%
4. **Disk Space**: Alert if temp directory > 90% full
5. **Response Time**: Alert if 95th percentile > 30s

## Performance Optimization

### Scaling Strategies

1. **Horizontal Scaling**:
   ```yaml
   # Increase replicas in docker-compose
   deploy:
     replicas: 3
   
   # Load balancer configuration
   nginx:
     upstream n8n-tools-api {
         server 127.0.0.1:8001;
         server 127.0.0.1:8002;
         server 127.0.0.1:8003;
     }
   ```

2. **Resource Optimization**:
   - Monitor memory usage during large file processing
   - Adjust worker count based on CPU cores
   - Use SSD storage for temporary files

### Performance Tuning

1. **Uvicorn Configuration**:
   ```bash
   # Production command with optimized workers
   uvicorn app.main:app \
     --host 0.0.0.0 \
     --port 8000 \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --access-log \
     --use-colors
   ```

2. **Memory Management**:
   - Monitor peak memory usage during PDF processing
   - Set appropriate container memory limits
   - Consider streaming for very large files

## Backup and Recovery

### What to Backup

1. **Application Configuration**:
   - Environment variables (`.env` files)
   - Docker compose configurations
   - Custom configuration files

2. **Deployment Artifacts**:
   - Docker images (tagged versions)
   - Kubernetes manifests
   - Nginx/proxy configurations

### Recovery Procedures

1. **Service Recovery**:
   ```bash
   # Check service status
   docker-compose ps
   
   # View recent logs
   docker-compose logs --tail=50 n8n-tools-api
   
   # Restart service
   docker-compose restart n8n-tools-api
   
   # Full redeployment
   docker-compose down
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

2. **Disaster Recovery**:
   ```bash
   # Pull latest stable image
   docker pull n8n-tools-api:stable
   
   # Deploy with stable version
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## Maintenance Procedures

### Regular Maintenance Tasks

1. **Weekly**:
   - Review application logs for errors
   - Check resource utilization metrics
   - Verify health check responses

2. **Monthly**:
   - Update base images for security patches
   - Review and rotate secrets/API keys
   - Test backup and recovery procedures

3. **Quarterly**:
   - Performance testing and optimization
   - Security audit and vulnerability assessment
   - Documentation updates

### Update Procedures

1. **Application Updates**:
   ```bash
   # Build new version
   docker build -t n8n-tools-api:v1.1.0 .
   
   # Test in staging
   docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
   
   # Deploy to production (rolling update)
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

2. **Dependency Updates**:
   ```bash
   # Update Python dependencies
   pip-compile requirements.in
   
   # Rebuild image with updates
   docker build --no-cache -t n8n-tools-api:latest .
   ```

## Troubleshooting

### Common Issues

1. **Service Won't Start**:
   ```bash
   # Check logs for errors
   docker-compose logs n8n-tools-api
   
   # Check resource availability
   docker system df
   docker stats
   
   # Verify environment variables
   docker-compose config
   ```

2. **High Memory Usage**:
   ```bash
   # Monitor container resource usage
   docker stats n8n-tools-api
   
   # Check for memory leaks in logs
   docker-compose logs | grep -i "memory\|oom"
   
   # Restart service to clear memory
   docker-compose restart n8n-tools-api
   ```

3. **File Processing Errors**:
   ```bash
   # Check temp directory space
   df -h /tmp
   
   # Verify file permissions
   docker exec n8n-tools-api ls -la /tmp/n8n-tools
   
   # Check for corrupted files
   docker-compose logs | grep -i "pdf\|error\|corrupt"
   ```

4. **Network Connectivity Issues**:
   ```bash
   # Test internal connectivity
   docker exec n8n-tools-api curl -f http://localhost:8000/health
   
   # Check exposed ports
   docker port n8n-tools-api
   
   # Verify firewall rules
   ufw status
   ```

### Performance Issues

1. **Slow Response Times**:
   - Check CPU and memory utilization
   - Review application logs for bottlenecks
   - Consider horizontal scaling
   - Optimize PDF processing for large files

2. **High Error Rates**:
   - Review error logs for patterns
   - Check resource limits
   - Verify file size limits
   - Monitor temporary disk space

### Emergency Procedures

1. **Service Outage**:
   ```bash
   # Quick restart
   docker-compose restart n8n-tools-api
   
   # Full service recovery
   docker-compose down
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   
   # Scale up for high load
   docker-compose up --scale n8n-tools-api=3 -d
   ```

## Support and Resources

### Documentation Links
- **API Documentation**: http://your-api-url/docs
- **Health Endpoint**: http://your-api-url/health
- **OpenAPI Schema**: http://your-api-url/openapi.json

### Monitoring Dashboards
- **Application Metrics**: http://your-grafana-url:3000
- **Infrastructure Monitoring**: http://your-prometheus-url:9090
- **Log Aggregation**: http://your-logs-url

### Emergency Contacts
- **DevOps Team**: devops@yourcompany.com
- **On-call Engineer**: +1-xxx-xxx-xxxx
- **Incident Management**: https://your-incident-management-url

### Useful Commands Reference

```bash
# Service Management
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker-compose restart n8n-tools-api
docker-compose logs -f --tail=100 n8n-tools-api

# Health Monitoring
curl -f http://localhost:8000/health
docker exec n8n-tools-api ps aux
docker stats n8n-tools-api

# Debugging
docker exec -it n8n-tools-api /bin/bash
docker-compose config
docker system prune -a
```

---

**Last Updated**: June 2025  
**Version**: 1.0.0  
**Maintainer**: DevOps Team
