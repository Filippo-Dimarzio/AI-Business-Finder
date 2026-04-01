# Production Deployment with Docker Compose

This guide provides step-by-step instructions for deploying Business Finder to production using Docker Compose.

## Prerequisites

Before starting, ensure you have:

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- A domain name pointing to your server
- SSL/TLS certificate (from Let's Encrypt or other CA)
- Required API keys:
  - Google Places API key
  - Google Custom Search API key
  - Admin API key (generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

## Quick Start (5 minutes)

### 1. SSH to Server and Clone Repository

```bash
ssh user@your-server.com
cd /home/user
git clone https://github.com/yourusername/business-finder.git
cd business-finder
```

### 2. Create Environment File

```bash
# Copy template
cp env.example .env

# Edit with your production values
nano .env

# Required variables to set:
# GOOGLE_PLACES_API_KEY=your_key_here
# GOOGLE_SEARCH_API_KEY=your_key_here
# ADMIN_API_KEY=secure_random_string_here
# DB_PASSWORD=secure_database_password
# CORS_ORIGINS=https://your-domain.com
# ENVIRONMENT=production
```

### 3. Setup SSL Certificates

```bash
# Install certbot
sudo apt-get update && sudo apt-get install -y certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Create ssl directory and copy certificates
mkdir -p ./ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/key.pem
sudo chown $(whoami):$(whoami) ./ssl/*.pem
chmod 644 ./ssl/*.pem
```

### 4. Build and Start Services

```bash
# Build Docker images
docker-compose build

# Start all services in background
docker-compose up -d

# Verify services are running
docker-compose ps

# Check application logs
docker-compose logs -f app
```

### 5. Verify Deployment

```bash
# Test health endpoint
curl -k https://127.0.0.1/api/health

# Check database
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT COUNT(*) FROM businesses;"

# View Nginx logs
docker-compose logs nginx
```

## Architecture

The docker-compose setup includes:

- **App Service**: FastAPI backend (Python 3.11) running on port 8000
- **PostgreSQL Service**: Database on port 5432
- **Nginx Service**: Reverse proxy and SSL termination on ports 80/443
- **Health Checks**: Built-in health monitoring for all services

```
┌─────────────────────────────────────────────────────┐
│                   Internet (HTTPS)                   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │   Nginx (Reverse     │
          │   Proxy + SSL)       │
          │   Ports: 80, 443     │
          └─────────┬────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  FastAPI Backend     │
          │  Port: 8000 (internal)
          │  React Frontend      │
          └─────────┬────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  PostgreSQL Database │
          │  Port: 5432 (internal)
          └──────────────────────┘
```

## Environment Configuration

### Required Variables

```bash
# Database
DATABASE_URL=postgresql://business_finder:password@postgres:5432/business_finder
DB_PASSWORD=secure_password_here

# API Keys
GOOGLE_PLACES_API_KEY=your_google_places_api_key
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
ADMIN_API_KEY=secure_random_key_32_chars_min

# Security & Deployment
CORS_ORIGINS=https://your-domain.com
ENVIRONMENT=production
DEBUG=False
DEMO_ALLOW_SEED=false
```

### Optional Variables

```bash
# Email notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
NOTIFICATION_EMAIL=admin@your-domain.com

# Monitoring
SENTRY_DSN=https://your-sentry-key

# Features
ENABLE_RETRAINING=true
ENABLE_BATCH_OPERATIONS=true
```

## SSL/TLS Certificate Renewal

The setup includes automatic SSL certificate renewal:

```bash
# Test renewal (dry-run)
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew

# Check certificate expiration
sudo certbot certificates

# The certificates should be copied to ./ssl/ directory
# The docker-compose setup will pick up updated certificates automatically
```

## Common Operations

### View Logs

```bash
# All services
docker-compose logs --tail=100 -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f nginx
```

### Database Operations

```bash
# Backup database
docker-compose exec postgres pg_dump -U business_finder business_finder > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U business_finder business_finder

# Connect to database
docker-compose exec postgres psql -U business_finder -d business_finder

# Run migrations
docker-compose exec app alembic upgrade head
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild services
docker-compose build

# Restart services
docker-compose down
docker-compose up -d

# Verify
docker-compose ps
```

### Stop Services

```bash
# Stop without removing
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v
```

## Monitoring

### Health Checks

```bash
# Check service health
docker-compose ps

# Detailed health check
docker-compose exec app curl http://localhost:8000/api/health

# Nginx health
docker-compose exec nginx curl http://localhost/api/health
```

### Resource Usage

```bash
# Monitor resource usage
docker-compose stats

# Specific service
docker-compose stats app
docker-compose stats postgres
```

### Application Metrics

```bash
# Check application logs for errors
docker-compose logs app | grep ERROR

# Count API requests
docker-compose logs nginx | grep -c "POST /api"

# Monitor database size
docker-compose exec postgres psql -U business_finder -d business_finder -c "\l+"
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs app

# Verify environment variables
docker-compose config | grep DATABASE_URL

# Check disk space
df -h
```

### Database connection error

```bash
# Test database connectivity
docker-compose exec app python -c "from database import engine; print('OK')"

# Check database status
docker-compose exec postgres pg_isready

# Verify database exists
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT 1;"
```

### SSL certificate not working

```bash
# Check certificate
ls -la ./ssl/

# Verify certificate validity
openssl x509 -in ./ssl/cert.pem -noout -dates

# Check Nginx SSL configuration
docker-compose logs nginx | grep ssl

# Test SSL
curl -v https://127.0.0.1/api/health
```

### High memory usage

```bash
# Check memory usage
docker-compose stats

# Restart services
docker-compose restart

# Increase resources in docker-compose.yml
# Add to services:
#   app:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
```

## Security Best Practices

- ✅ Use strong, unique passwords for DATABASE password and ADMIN_API_KEY
- ✅ Keep Docker images updated: `docker-compose pull && docker-compose up -d`
- ✅ Review and rotate ADMIN_API_KEY regularly
- ✅ Use HTTPS only (redirect HTTP to HTTPS)
- ✅ Enable rate limiting in Nginx (already configured)
- ✅ Monitor logs for suspicious activity
- ✅ Keep DEMO_ALLOW_SEED=false in production
- ✅ Regular database backups
- ✅ Restrict SSH access to trusted IPs

## Backup & Disaster Recovery

### Automated Daily Backup

```bash
# Create backup script
mkdir -p ./backups
cat > ./backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U business_finder business_finder | gzip > ./backups/backup_$DATE.sql.gz
echo "Backup completed: ./backups/backup_$DATE.sql.gz"
EOF

chmod +x ./backup.sh

# Add to crontab for daily backups at 2 AM
# 0 2 * * * cd /path/to/business-finder && ./backup.sh >> /var/log/backup.log 2>&1
```

### Restore from Backup

```bash
# Extract and restore
gunzip -c ./backups/backup_20240101_020000.sql.gz | \
  docker-compose exec -T postgres psql -U business_finder business_finder
```

## Performance Optimization

### Database Optimization

```bash
# Run VACUUM
docker-compose exec postgres vacuumdb -U business_finder business_finder

# Analyze query plans
docker-compose exec postgres psql -U business_finder -d business_finder -c "ANALYZE;"

# Check slow queries
docker-compose logs app | grep "Slow query"
```

### Nginx Caching

Caching is already configured in nginx.conf for:
- Static assets: 1 year cache
- Frontend app: 1 hour cache
- API endpoints: No cache

### Scaling

To handle more traffic:

```yaml
# In docker-compose.yml, increase app replicas:
version: '3.8'
services:
  app:
    deploy:
      replicas: 3  # Run 3 instances

# Load balancing is handled by Nginx upstream directive
```

## Support & Documentation

- Health check: `curl https://your-domain.com/api/health`
- Admin API key: Set `X-Admin-Key` header with value from ADMIN_API_KEY env var
- Database: PostgreSQL running in container
- Frontend: React app served by Nginx
- API docs: Available at `https://your-domain.com/docs` (if configured)

For detailed information, see:
- [PRODUCTION.md](PRODUCTION.md) - Comprehensive deployment guide
- [README.md](README.md) - Project overview
- [env.example](env.example) - All configuration options
