# Quick Reference Guide

A fast reference for common operations. For detailed procedures, see [PRODUCTION.md](PRODUCTION.md).

---

## Emergency Procedures

### 🚨 System Down - Quick Recovery
```bash
# 1. Check service status
docker-compose ps

# 2. View recent errors
docker-compose logs --tail=50 app | grep ERROR

# 3. Restart all services
docker-compose restart

# 4. Verify health
curl -k https://your-domain.com/api/health

# 5. If still down, contact DevOps team with logs:
docker-compose logs > /tmp/logs.txt
```

### 🚨 Database Connection Failed
```bash
# 1. Check PostgreSQL status
docker-compose exec postgres pg_isready

# 2. Verify database exists
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT COUNT(*) FROM businesses;"

# 3. If failed, check environment
echo $DATABASE_URL

# 4. Restart database
docker-compose restart postgres && sleep 5 && docker-compose restart app
```

### 🚨 SSL Certificate Expired
```bash
# 1. Check expiration
openssl x509 -in ./ssl/cert.pem -noout -dates

# 2. Renew certificate
sudo certbot renew

# 3. Copy to ssl directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/key.pem
sudo chown $(whoami):$(whoami) ./ssl/*.pem

# 4. Restart Nginx
docker-compose restart nginx

# 5. Verify
curl -k https://your-domain.com/api/health
```

---

## Daily Operations

### Check System Health
```bash
# Overall status
docker-compose ps

# Quick health check
curl -s https://your-domain.com/api/health | jq .

# Resource usage
docker-compose stats --no-stream

# Error log check
docker-compose logs app | grep ERROR | tail -5
```

### Monitor Logs
```bash
# Real-time logs (all services)
docker-compose logs -f

# Real-time app logs only
docker-compose logs -f app

# Last 50 lines
docker-compose logs --tail=50 app

# Search for errors
docker-compose logs app | grep ERROR
```

### Database Operations
```bash
# Count businesses
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT COUNT(*) FROM businesses;"

# Check database size
docker-compose exec postgres psql -U business_finder -d business_finder -c "\l+"

# View recent reviews
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT * FROM reviews ORDER BY created_at DESC LIMIT 10;"
```

---

## Deployment Operations

### Deploy New Version
```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild images
docker-compose build

# 3. Start new services (zero-downtime)
docker-compose up -d

# 4. Verify
curl https://your-domain.com/api/health

# 5. Check logs for errors
docker-compose logs --tail=20 app
```

### Rollback to Previous Version
```bash
# 1. Check git history
git log --oneline | head -10

# 2. Checkout previous commit
git checkout <previous-commit-hash>

# 3. Rebuild and restart
docker-compose build && docker-compose up -d

# 4. Verify
curl https://your-domain.com/api/health
```

---

## Maintenance Tasks

### Weekly Tasks

**Monday backup check** (5 min)
```bash
# Verify daily backup exists
ls -lh ./backups/ | head -5

# Optional: Manual backup
docker-compose exec postgres pg_dump -U business_finder business_finder | gzip > ./backups/backup_manual_$(date +%Y%m%d).sql.gz
```

**Certificate check** (2 min)
```bash
# Check expiration
openssl x509 -in ./ssl/cert.pem -noout -dates

# Should show 30+ days remaining
```

**Logs cleanup** (1 min)
```bash
# View current log size
du -sh /var/log/business-finder/

# Old logs are auto-rotated (no action needed)
```

### Monthly Tasks

**Database optimization** (5 min)
```bash
# Run VACUUM
docker-compose exec postgres vacuumdb -U business_finder business_finder

# Run ANALYZE
docker-compose exec postgres psql -U business_finder -d business_finder -c "ANALYZE;"

# Check index usage
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT schemaname, tablename, indexname FROM pg_indexes LIMIT 20;"
```

**Performance review** (10 min)
```bash
# Check error rates
docker-compose logs app | grep ERROR | wc -l

# Check slow queries (if logging enabled)
docker-compose logs app | grep "slow\|Slow" | tail -10

# Database size trend
du -sh ./backups/
```

**Security review** (5 min)
```bash
# Check for exposed secrets in logs
docker-compose logs | grep -i "password\|secret\|key" | head -5

# Verify API key is still valid
curl -H "X-Admin-Key: $ADMIN_API_KEY" https://your-domain.com/api/health
```

---

## API Testing

### Health Check
```bash
curl -s https://your-domain.com/api/health | jq .
# Expected: {"status": "healthy", "database": "connected"}
```

### List Businesses
```bash
curl -s https://your-domain.com/api/businesses?limit=5 | jq .
```

### Admin Operations (Requires API Key)
```bash
# Seed demo labels
curl -X POST \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  "https://your-domain.com/api/admin/seed_labels?count=10"

# Retrain model
curl -X POST \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  https://your-domain.com/api/retrain | jq .
```

### Export Data
```bash
# CSV export
curl -s "https://your-domain.com/api/export/csv?status=approved" > businesses.csv

# JSON export
curl -s "https://your-domain.com/api/export/json" | jq . | head -20
```

---

## Debugging Commands

### Application Issues
```bash
# Check Python errors
docker-compose logs app | grep -i "traceback\|error\|exception"

# Test database connection
docker-compose exec app python -c "from database import engine; print('OK')" || echo "DB ERROR"

# Check environment variables
docker-compose config | grep -i "database\|admin"
```

### Nginx Issues
```bash
# Test Nginx config
docker-compose exec nginx nginx -t

# Check Nginx error log
docker-compose logs nginx | grep error

# View Nginx access log (recent requests)
docker-compose logs nginx | tail -20
```

### Database Issues
```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT 1;"

# Check active connections
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT count(*) FROM pg_stat_activity;"

# List all databases
docker-compose exec postgres psql -U business_finder -l
```

### SSL/Certificate Issues
```bash
# Check certificate info
openssl x509 -in ./ssl/cert.pem -text -noout

# Check certificate validity (detailed)
openssl s_client -connect your-domain.com:443 -showcerts

# Verify certificate matches key
openssl x509 -modulus -in ./ssl/cert.pem -noout | md5sum
openssl rsa -modulus -in ./ssl/key.pem -noout | md5sum
# These should match
```

---

## Performance Tuning

### Slow Endpoints
```bash
# Identify slow requests (if logging enabled)
docker-compose logs app | grep "duration\|took\|time:" | sort

# Check database query performance
docker-compose exec postgres psql -U business_finder -d business_finder << EOF
EXPLAIN ANALYZE SELECT * FROM businesses WHERE status = 'approved' LIMIT 10;
EOF
```

### High Memory Usage
```bash
# Check memory per service
docker-compose stats --no-stream

# Reduce app instances (if multiple)
# Edit docker-compose.yml, remove extra app services

# Optimize database
docker-compose exec postgres vacuumdb -U business_finder business_finder
```

### High CPU Usage
```bash
# Monitor CPU per service
docker stats --no-stream

# Check for long-running queries
docker-compose exec postgres psql -U business_finder -d business_finder -c "SELECT query, duration FROM pg_stat_statements ORDER BY duration DESC LIMIT 5;"

# Restart services if needed
docker-compose restart app
```

---

## Contact & Escalation

**On-call Contact**: [DevOps Team]  
**Escalation**: [Tech Lead]  
**Emergency**: [CTO]

### When to Escalate
- System down for >30 minutes
- Data loss or corruption
- Security incident
- Service degradation affecting users

---

## Checklists

### Daily Checklist (5 minutes)
- [ ] `docker-compose ps` - all services UP
- [ ] `curl https://domain/api/health` - returns 200
- [ ] Check logs: `docker-compose logs --tail=20` - no ERROR
- [ ] Business count stable: `SELECT COUNT(*) FROM businesses`

### Weekly Checklist (30 minutes)
- [ ] Backup exists: `ls ./backups/`
- [ ] Certificate expiring: `openssl x509 -dates -in ./ssl/cert.pem`
- [ ] Database size: `du -sh ./backups/`
- [ ] Update check: `git status` - no uncommitted changes

### Monthly Checklist (1 hour)
- [ ] Performance review (errors, slow queries)
- [ ] Security review (no exposed secrets)
- [ ] Database optimization (VACUUM, ANALYZE)
- [ ] Disk space check: `df -h`
- [ ] Update dependencies: `docker-compose build --pull`

---

## File Locations

```
/home/appuser/business-finder/
├── .env                        # Production config (DO NOT COMMIT)
├── docker-compose.yml          # Service definitions
├── Dockerfile                  # Container image spec
├── nginx.conf                  # Reverse proxy config
├── ssl/
│   ├── cert.pem               # SSL certificate
│   └── key.pem                # Private key
├── backups/                   # Database backups
└── logs/                      # Application logs
```

---

## Useful Aliases

Add to `~/.bashrc` for quick access:

```bash
# Business Finder shortcuts
alias bf-status='docker-compose ps'
alias bf-logs='docker-compose logs -f app'
alias bf-health='curl -s https://your-domain.com/api/health | jq .'
alias bf-db='docker-compose exec postgres psql -U business_finder business_finder'
alias bf-backup='docker-compose exec postgres pg_dump -U business_finder business_finder | gzip > ./backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz && echo "Backup complete"'
alias bf-restart='docker-compose restart'
alias bf-deploy='git pull && docker-compose build && docker-compose up -d && sleep 2 && bf-health'
```

---

**Last Updated**: January 28, 2026  
**Version**: 1.0.0
