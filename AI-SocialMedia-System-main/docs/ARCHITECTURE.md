# System Architecture & Operations Manual

## Overview

Business Finder is a production-ready AI system for identifying small businesses without web/social presence. This document provides a comprehensive technical overview, architecture diagrams, and operational procedures.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         End Users                               │
│                  (via https://yourdomain.com)                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │    Nginx (Reverse Proxy)   │
        │  • SSL/TLS Termination     │
        │  • Rate Limiting           │
        │  • Static Asset Serving    │
        │  • Request Routing         │
        └────────┬───────────────────┘
                 │
        ┌────────▼───────────────────┐
        │   FastAPI Backend          │
        │  • REST API Endpoints      │
        │  • Business Management     │
        │  • ML Pipeline Execution   │
        │  • Admin Operations        │
        └────────┬───────────────────┘
                 │
        ┌────────▼───────────────────┐
        │  PostgreSQL Database       │
        │  • Business Records        │
        │  • Review History          │
        │  • Model Metrics           │
        │  • User Preferences        │
        └────────────────────────────┘
```

### Request Flow Diagram

```
1. HTTPS Request (Client → Nginx)
   ├─ GET /              → Serve React app (index.html)
   ├─ GET /static/*      → Serve CSS/JS bundles (cached)
   ├─ GET /api/health    → Health check
   ├─ GET /api/...       → API requests
   └─ POST /api/...      → Data mutation requests
                    │
                    ▼
2. Nginx Processing
   ├─ SSL/TLS decryption
   ├─ Rate limit check
   ├─ Static asset cache check
   └─ Proxy to FastAPI (if needed)
                    │
                    ▼
3. FastAPI Processing
   ├─ Authentication (ADMIN_API_KEY for /api/admin/*)
   ├─ Input validation (Pydantic models)
   ├─ Database operations (SQLAlchemy ORM)
   ├─ ML inference (if needed)
   └─ Response formatting (JSON)
                    │
                    ▼
4. Database Operation
   ├─ Query planning
   ├─ Index usage
   ├─ Transaction handling
   └─ Result fetching
                    │
                    ▼
5. Response Flow (reverse)
   ├─ Database → FastAPI (parsed results)
   ├─ FastAPI → Nginx (JSON response)
   ├─ Nginx → Client (SSL/TLS encryption)
   └─ Client renders/processes
```

### Component Interaction

```
Client (Browser)
    ↑ HTTPS
    ↓
Nginx (Port 80/443)
    ├─ Static files → build/ directory
    └─ /api/* → FastAPI backend (Port 8000)
            │
            ├─ Database (SQLAlchemy ORM)
            │   ├─ GET /api/businesses
            │   ├─ POST /api/review
            │   └─ POST /api/retrain
            │
            ├─ ML Pipeline (classifier.py)
            │   ├─ Load trained model
            │   ├─ Inference (predict)
            │   └─ Confidence scoring
            │
            └─ Admin Operations
                ├─ POST /api/admin/seed_labels
                ├─ POST /api/admin/export
                └─ GET /api/health

PostgreSQL Database
    ├─ businesses (id, name, address, url, status, confidence)
    ├─ reviews (id, business_id, status, timestamp)
    ├─ model_metrics (id, model_name, metric_name, value, timestamp)
    └─ Indexes on (status, confidence, created_at)
```

---

## Technology Stack

### Frontend
- **Framework**: React 18.x
- **Styling**: TailwindCSS + CSS Modules
- **Icons**: lucide-react
- **Routing**: React Router v6
- **Code Splitting**: React.lazy() + Suspense
- **Build Tool**: Webpack (via Create React App)
- **Testing**: Jest + React Testing Library

### Backend
- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn (ASGI)
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL 15 (production), SQLite 3 (dev)
- **Validation**: Pydantic v2
- **Logging**: Loguru
- **Task Queue**: APScheduler (optional, for background jobs)
- **Testing**: FastAPI TestClient + pytest

### ML Stack
- **Classification**: scikit-learn (LogisticRegression, RandomForest)
- **Boosting**: LightGBM
- **Model Persistence**: joblib
- **Data Processing**: pandas, numpy
- **Feature Engineering**: scikit-learn (StandardScaler, OneHotEncoder)

### DevOps & Deployment
- **Containerization**: Docker (multi-stage build)
- **Orchestration**: Docker Compose
- **Reverse Proxy**: Nginx 1.24+
- **Process Management**: Supervisor (traditional) or systemd
- **Certificates**: Let's Encrypt (Certbot)
- **CI/CD**: GitHub Actions (lint, test, build)

---

## Database Schema

### Core Tables

#### businesses
```sql
CREATE TABLE businesses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(512),
    city VARCHAR(100),
    postal_code VARCHAR(20),
    phone VARCHAR(20),
    website VARCHAR(512),
    has_facebook BOOLEAN DEFAULT FALSE,
    has_instagram BOOLEAN DEFAULT FALSE,
    has_twitter BOOLEAN DEFAULT FALSE,
    status VARCHAR(20),  -- 'no_web', 'approved', 'rejected', 'pending'
    confidence FLOAT,    -- 0.0 to 1.0
    source VARCHAR(50),  -- 'google_places', 'csv', 'osm'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_status ON businesses(status);
CREATE INDEX idx_confidence ON businesses(confidence);
CREATE INDEX idx_created_at ON businesses(created_at);
```

#### reviews
```sql
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id),
    reviewer_id VARCHAR(100),
    status VARCHAR(20),  -- 'approved', 'rejected'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_business_id ON reviews(business_id);
CREATE INDEX idx_created_at ON reviews(created_at);
```

#### model_metrics
```sql
CREATE TABLE model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    metric_name VARCHAR(100),
    metric_value FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_metric ON model_metrics(model_name, metric_name);
```

---

## API Endpoints Reference

### Health & Status
```
GET /api/health
  Returns: {"status": "healthy", "database": "connected"}
  Purpose: Health check for monitoring
```

### Business Management
```
GET /api/businesses?status=&page=1&limit=20
  Returns: List of businesses with pagination
  
POST /api/business/{id}/review
  Body: {"status": "approved|rejected", "notes": "..."}
  Returns: Updated business record
  
GET /api/business/{id}
  Returns: Single business record with full details
```

### ML Operations
```
POST /api/retrain
  Headers: X-Admin-Key: <ADMIN_API_KEY>
  Returns: {
    "status": "success",
    "metrics": {
      "auc": 0.95,
      "accuracy": 0.92,
      "precision": 0.91,
      "recall": 0.93
    },
    "reclassified": 342
  }
  
POST /api/admin/seed_labels?count=10
  Headers: X-Admin-Key: <ADMIN_API_KEY>
  Returns: {"status": "seeded", "count": 10}
  Note: Requires ADMIN_API_KEY or DEMO_ALLOW_SEED=true
```

### Exports
```
GET /api/export/csv?status=approved
  Returns: CSV file download
  
GET /api/export/json
  Returns: JSON formatted data
```

### Admin Operations
```
POST /api/admin/seed_labels
GET /api/admin/stats
POST /api/admin/backup
```

---

## Operational Procedures

### Deployment

#### Initial Deployment (Docker Compose)
```bash
# 1. Prepare server
ssh user@server.com
git clone repo && cd repo
cp env.example .env
# Edit .env with production values

# 2. Setup SSL certificates
sudo certbot certonly --standalone -d yourdomain.com
mkdir ssl && cp /etc/letsencrypt/live/yourdomain.com/{fullchain,privkey}.pem ssl/

# 3. Deploy
docker-compose build
docker-compose up -d

# 4. Verify
curl https://yourdomain.com/api/health
```

#### Update Deployment
```bash
# 1. Pull changes
git pull origin main

# 2. Rebuild images
docker-compose build

# 3. Restart services (zero-downtime recommended)
docker-compose up -d --no-deps app

# 4. Verify
curl https://yourdomain.com/api/health
```

### Monitoring

#### Real-time Monitoring
```bash
# Watch logs
docker-compose logs -f app

# Monitor resources
docker-compose stats

# Check service health
curl -s https://yourdomain.com/api/health | jq
```

#### Metrics Collection
```bash
# Count labeled businesses
curl -s -H "X-Admin-Key: $KEY" https://yourdomain.com/api/admin/stats

# Database size
docker-compose exec postgres psql -U bf -d business_finder -c "\l+"

# Last API calls
docker-compose logs app | grep "POST /api" | tail -10
```

### Maintenance

#### Database Optimization
```bash
# Weekly VACUUM
docker-compose exec postgres vacuumdb -U business_finder business_finder

# Weekly ANALYZE
docker-compose exec postgres psql -U business_finder -d business_finder -c "ANALYZE;"

# Monthly REINDEX
docker-compose exec postgres psql -U business_finder -d business_finder -c "REINDEX DATABASE business_finder;"
```

#### Log Rotation
```bash
# Configure in Docker or supervisord to rotate logs
# Keep last 7 days of logs in /var/log/business-finder/
```

#### Certificate Renewal
```bash
# Automatic via certbot.timer
sudo systemctl status certbot.timer

# Manual renewal
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

### Backup & Recovery

#### Regular Backups
```bash
# Daily automated backup
0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1

# Manual backup
docker-compose exec postgres pg_dump -U business_finder business_finder | gzip > backup_$(date +%Y%m%d).sql.gz

# Store securely (cloud storage, backup service)
```

#### Recovery Procedure
```bash
# 1. Restore from backup
gunzip -c backup_20240128.sql.gz | \
  docker-compose exec -T postgres psql -U business_finder business_finder

# 2. Verify data
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT COUNT(*) FROM businesses;"

# 3. Restart services
docker-compose restart app
```

---

## Performance Optimization

### Database Performance
- **Indexing**: Indexes on status, confidence, created_at
- **Query Optimization**: Use EXPLAIN ANALYZE for slow queries
- **Connection Pooling**: SQLAlchemy session management
- **Caching**: Redis for frequently accessed data (optional)

### Application Performance
- **Lazy Loading**: React components loaded on demand
- **Code Splitting**: Separate chunks for dashboard/filters/exports
- **Minification**: Production builds use webpack minification
- **Compression**: Nginx gzip enabled (text, JSON, CSS, JS)

### Infrastructure Performance
- **Caching**: Nginx caches static assets (1 year TTL)
- **Rate Limiting**: 10 req/s for admin, 50 req/s for general
- **Load Balancing**: Nginx upstream for multiple app instances
- **Database Pooling**: Connection pool size = (workers * 2) + 1

---

## Security Measures

### Authentication
- **API Keys**: ADMIN_API_KEY required for /api/admin/* endpoints
- **SSL/TLS**: All connections encrypted with HTTPS
- **CORS**: Restricted to production domain only
- **Headers**: X-Frame-Options, X-Content-Type-Options, etc.

### Data Security
- **Database Encryption**: PostgreSQL connection encryption
- **Secret Management**: Environment variables (not in code)
- **SQL Injection Prevention**: SQLAlchemy ORM parameterized queries
- **CSRF Protection**: Handled by HTTPS + SameSite cookies

### Rate Limiting
```
API endpoints: 10 requests/second per IP
General endpoints: 50 requests/second per IP
Burst allowance: 5 for API, 20 for general
```

### Monitoring & Logging
- **Error Tracking**: Sentry integration (optional)
- **Access Logs**: Nginx logs for all requests
- **Application Logs**: Structured logging with loguru
- **Audit Trail**: Review actions logged with timestamp/user

---

## Troubleshooting Guide

### Common Issues

| Issue | Symptom | Root Cause | Solution |
|-------|---------|-----------|----------|
| Services won't start | `docker-compose up` fails | Env vars missing or invalid | Check .env file, validate API keys |
| Database connection error | `/api/health` returns error | PostgreSQL not running or wrong URL | `docker-compose exec postgres pg_isready` |
| Slow API response | API calls take >5s | Database query slow, missing index | Run `EXPLAIN ANALYZE`, add indexes |
| High memory usage | Server RAM exhausted | Memory leak, too many app instances | Reduce replicas, optimize queries |
| SSL certificate error | HTTPS requests fail | Certificate expired or invalid | `certbot renew`, check paths |

### Debug Commands

```bash
# Test database connection
docker-compose exec app python -c "from database import engine; print('OK')"

# Check environment variables
docker-compose config | grep -i "database\|admin"

# View application logs
docker-compose logs -f app --tail=100

# Test API endpoint
curl -v -H "X-Admin-Key: $KEY" https://yourdomain.com/api/health

# Monitor database connections
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT count(*) FROM pg_stat_activity;"

# Check Nginx configuration
docker-compose exec nginx nginx -t

# Test SSL certificate
openssl s_client -connect yourdomain.com:443 -showcerts
```

---

## Disaster Recovery

### RTO/RPO Targets
- **RTO** (Recovery Time Objective): 15 minutes
- **RPO** (Recovery Point Objective): 24 hours (daily backups)

### Disaster Scenarios

#### Scenario 1: Database Corruption
1. Stop application: `docker-compose stop app`
2. Restore from latest backup
3. Verify data integrity
4. Restart application

#### Scenario 2: Application Crash
1. Check logs: `docker-compose logs app`
2. Restart service: `docker-compose restart app`
3. Monitor health: `curl https://yourdomain.com/api/health`

#### Scenario 3: Server Failure
1. Deploy on new server following [PRODUCTION.md](PRODUCTION.md)
2. Restore database from backup
3. Update DNS to new server IP
4. Verify all services operational

---

## Team Runbooks

### On-Call Response
- **Alert**: Received from monitoring service
- **Response**: Check `/api/health` endpoint
- **If healthy**: Investigate logs with `docker-compose logs`
- **If unhealthy**: Follow scenario-specific runbook above
- **Escalation**: Contact dev lead if issue persists >30 min

### Weekly Maintenance Window
- **Time**: Sunday 02:00 UTC (maintenance window)
- **Tasks**:
  - Run `VACUUM` on database
  - Review and update SSL certificates
  - Check backup completion
  - Review error logs
- **Duration**: ~30 minutes (with fallback plan ready)

### Monthly Review
- **Performance**: CPU, memory, disk usage trends
- **Security**: Review access logs, dependency vulnerabilities
- **Data**: Business count, label quality, model performance
- **Costs**: Infrastructure, API usage, storage
- **Planning**: Capacity planning for next quarter

---

## Glossary

- **ASGI**: Asynchronous Server Gateway Interface
- **ORM**: Object Relational Mapping (SQLAlchemy)
- **AUC**: Area Under the Receiver Operating Characteristic Curve
- **RTO**: Recovery Time Objective
- **RPO**: Recovery Point Objective
- **TTL**: Time To Live (cache expiration)
- **CORS**: Cross-Origin Resource Sharing
- **SLA**: Service Level Agreement
- **Upstream**: Reverse proxy configuration pointing to backend servers

---

## Related Documentation

- [PRODUCTION.md](PRODUCTION.md) - Deployment procedures
- [DOCKER_COMPOSE.md](DOCKER_COMPOSE.md) - Docker Compose operations
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Pre-deployment verification
- [README.md](README.md) - Project overview
- [env.example](env.example) - Configuration template

---

**Last Updated**: January 28, 2026  
**Version**: 1.0.0  
**Maintainer**: DevOps Team
