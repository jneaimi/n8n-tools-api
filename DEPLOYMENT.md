# Production Deployment - Quick Start Guide

This directory contains all the necessary files and configurations for deploying the N8N Tools API in production environments.

## 📁 Directory Structure

```
├── docs/
│   └── production-deployment.md     # Comprehensive deployment guide
├── k8s/
│   ├── deployment.yaml             # Kubernetes manifests
│   └── autoscaling.yaml           # HPA and resource policies
├── monitoring/
│   ├── docker-compose.monitoring.yml  # Monitoring stack
│   ├── prometheus.yml              # Prometheus configuration
│   ├── alertmanager.yml           # Alert configuration
│   └── alert_rules.yml            # Custom alert rules
├── nginx/
│   └── n8n-tools-api.conf         # Nginx reverse proxy config
└── scripts/deployment/
    └── deploy.sh                  # Automated deployment script
```

## 🚀 Quick Deployment Options

### Option 1: Docker Compose (Recommended)

```bash
# Basic production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With monitoring stack
docker-compose -f docker-compose.yml -f docker-compose.prod.yml -f monitoring/docker-compose.monitoring.yml up -d
```

### Option 2: Automated Script

```bash
# Run the automated deployment script
./scripts/deployment/deploy.sh

# Available commands:
./scripts/deployment/deploy.sh deploy    # Deploy the application
./scripts/deployment/deploy.sh rollback  # Rollback to previous version
./scripts/deployment/deploy.sh health    # Check service health
./scripts/deployment/deploy.sh cleanup   # Clean up old images
```

### Option 3: Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n n8n-tools-production
kubectl get svc -n n8n-tools-production
```

## 🔧 Configuration

### Environment Variables

Copy and customize the environment file:

```bash
cp .env.example .env
# Edit .env with your production values
```

Key production settings:
- `DEBUG=false`
- `LOG_LEVEL=INFO`
- `CORS_ORIGINS=https://your-n8n-domain.com`
- `MAX_FILE_SIZE_MB=50`
- `SECRET_KEY=your-secure-secret-key`

### SSL/TLS Setup

For production with HTTPS:

1. Install Nginx configuration:
   ```bash
   sudo cp nginx/n8n-tools-api.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/n8n-tools-api.conf /etc/nginx/sites-enabled/
   ```

2. Get SSL certificate with Certbot:
   ```bash
   sudo certbot --nginx -d api.your-domain.com
   ```

## 📊 Monitoring Setup

Deploy the complete monitoring stack:

```bash
cd monitoring/
docker-compose -f docker-compose.monitoring.yml up -d
```

Access points:
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

## 🔒 Security Checklist

- [ ] Update all default passwords
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up proper logging
- [ ] Enable monitoring and alerting
- [ ] Test backup and recovery procedures

## 📋 Health Checks

Verify deployment:

```bash
# Basic health check
curl http://localhost:8000/health

# API documentation
curl http://localhost:8000/docs

# Test file upload (with a small PDF)
curl -X POST "http://localhost:8000/api/v1/split" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@test.pdf"
```

## 🚨 Troubleshooting

### Common Issues

1. **Container won't start**:
   ```bash
   docker-compose logs n8n-tools-api
   docker system df  # Check disk space
   ```

2. **High memory usage**:
   ```bash
   docker stats n8n-tools-api
   # Check for large file processing
   ```

3. **SSL certificate issues**:
   ```bash
   sudo certbot renew --dry-run
   sudo nginx -t  # Test configuration
   ```

### Emergency Commands

```bash
# Quick restart
docker-compose restart n8n-tools-api

# Full redeployment
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View recent logs
docker-compose logs --tail=50 -f n8n-tools-api
```

## 📞 Support

For detailed information, see [production-deployment.md](docs/production-deployment.md)

- **Health Endpoint**: http://your-api-url/health
- **API Documentation**: http://your-api-url/docs
- **Monitoring Dashboard**: http://your-grafana-url:3000

---

**Need Help?** Check the comprehensive [Production Deployment Guide](docs/production-deployment.md) for detailed instructions and troubleshooting.
