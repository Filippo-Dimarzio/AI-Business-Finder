# Production Deployment Guide

## Pre-deployment Checklist

- [ ] Update `.env` with production values (database, API keys, admin key)
- [ ] Set `DEBUG=False` and `DEMO_ALLOW_SEED=false` in `.env`
- [ ] Generate a secure `ADMIN_API_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Run database migrations (if using PostgreSQL)
- [ ] Test the build: `npm run build`
- [ ] Run all tests: `CI=true npm test -- --watchAll=false`
- [ ] Review and configure CORS origins in `.env` (CORS_ORIGINS)

## Quick Start with Docker Compose

**Recommended for most deployments**

### 1. Prepare Server

```bash
# SSH to server
ssh user@your-server.com

# Clone repository
git clone https://github.com/yourusername/business-finder.git
cd business-finder

# Copy environment template
cp env.example .env

# Edit with production values
nano .env
# Set: ADMIN_API_KEY, GOOGLE_PLACES_API_KEY, CORS_ORIGINS, DB_PASSWORD, etc.
```

### 2. SSL Certificate (Let's Encrypt)

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
```

### 3. Deploy with Docker Compose

```bash
# Build and start services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f app

# Test health endpoint
curl -k https://127.0.0.1/api/health
```

### 4. Verify Deployment

```bash
# Test API with authentication
curl -k -H "X-Admin-Key: your_admin_key" https://127.0.0.1/api/health

# View database status
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT COUNT(*) FROM businesses;"

# Monitor resources
docker-compose stats
```

---

## Traditional Server Deployment

**For servers without Docker**

### 1. System Setup

```bash
# Install dependencies
sudo apt-get update && sudo apt-get install -y \
  python3.11 python3.11-venv python3-pip \
  nodejs npm \
  postgresql postgresql-contrib \
  nginx supervisor

# Create app user
sudo useradd -m -s /bin/bash appuser

# Clone and setup
sudo -u appuser git clone https://github.com/yourusername/business-finder.git /home/appuser/business-finder
cd /home/appuser/business-finder
```

### 2. Create `.env` for Production

```bash
cp env.example .env
# Edit .env with production values:
# - DATABASE_URL: use PostgreSQL (not SQLite)
# - GOOGLE_PLACES_API_KEY: your actual API key
# - DEBUG: false
# - DEMO_ALLOW_SEED: false
# - ADMIN_API_KEY: generate secure random key
# - CORS_ORIGINS: your production domain
# - ENVIRONMENT: production
```

### 3. Install Production Python Dependencies

```bash
# Create production venv
python3.11 -m venv .venv_prod

# Activate and install
source .venv_prod/bin/activate
pip install -r requirements.txt
```

### 4. Build Frontend

```bash
# Install Node dependencies
npm install

# Build for production
npm run build

# Verify build output
ls -lah build/
```

### 5. Database Setup (PostgreSQL)

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE business_finder;
CREATE USER business_finder WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE business_finder TO business_finder;
\c business_finder
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO business_finder;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO business_finder;
EOF

# Initialize database tables
python database.py
```

## Deployment Options

### Option A: Docker (Recommended)

#### 1. Build Docker Image

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Frontend build
RUN npm install && npm run build

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Build and Run

```bash
docker build -t business-finder:latest .
docker run -p 8000:8000 --env-file .env business-finder:latest
```

### Option B: Traditional Server Deployment

#### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv postgresql nginx supervisor

# macOS
brew install python@3.11 postgresql nginx
```

#### 2. Setup Application

```bash
# Clone repository
git clone <repo-url> /opt/business-finder
cd /opt/business-finder

# Create venv
python3.11 -m venv .venv_prod
source .venv_prod/bin/activate
pip install -r requirements.txt

# Build frontend
npm install
npm run build
```

#### 3. Configure Nginx (Reverse Proxy)

Create `/etc/nginx/sites-available/business-finder`:

```nginx
upstream business_finder {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend (static files from build/)
    location / {
        root /opt/business-finder/build;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://business_finder;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/business-finder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 4. Configure Supervisor (Process Manager)

Create `/etc/supervisor/conf.d/business-finder.conf`:

```ini
[program:business-finder]
command=/opt/business-finder/.venv_prod/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
directory=/opt/business-finder
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/business-finder/app.log
environment=PATH="/opt/business-finder/.venv_prod/bin"
```

Start the service:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start business-finder
```

## Security Checklist

- [ ] **HTTPS**: Use SSL/TLS certificates (Let's Encrypt)
- [ ] **Database**: Use strong PostgreSQL credentials, restrict network access
- [ ] **Admin API**: Secure ADMIN_API_KEY in environment, rotate regularly
- [ ] **CORS**: Restrict to your domain only (CORS_ORIGINS)
- [ ] **Logs**: Store in secure location, rotate daily
- [ ] **Dependencies**: Keep `requirements.txt` packages updated (`pip list --outdated`)
- [ ] **Secrets**: Never commit `.env`, use environment variables only
- [ ] **Backups**: Automate daily database backups to secure storage

## Monitoring & Maintenance

### Health Check

```bash
curl https://yourdomain.com/api/health
# Expected: {"status": "healthy"}
```

### Logs

```bash
# Supervisor logs
tail -f /var/log/business-finder/app.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Database Backup

```bash
# Daily backup script (/usr/local/bin/backup-db.sh)
#!/bin/bash
pg_dump business_finder | gzip > /backups/business_finder_$(date +%Y%m%d).sql.gz
```

Add to crontab: `0 2 * * * /usr/local/bin/backup-db.sh`

## Troubleshooting

### Port already in use
```bash
lsof -i :8000  # Find process
kill -9 <PID>
```

### Database connection error
```bash
# Test PostgreSQL connection
psql -h localhost -U username -d business_finder -c "SELECT 1;"
```

### API not responding
```bash
# Check supervisor status
sudo supervisorctl status business-finder

# Restart
sudo supervisorctl restart business-finder
```

## Rollback Procedure

If deployment fails:

```bash
# Revert to previous code
git checkout <previous-commit-hash>
npm run build
sudo supervisorctl restart business-finder

# Verify
curl https://yourdomain.com/api/health
```

## Performance Optimization (Optional)

- **Database indexing**: Ensure all frequently-queried columns are indexed
- **Caching**: Add Redis for session/response caching
- **CDN**: Serve static assets (JS, CSS) from CloudFront or similar
- **Monitoring**: Use Sentry for error tracking, DataDog for metrics

---

For questions or issues, refer to [README.md](README.md) or check logs.
