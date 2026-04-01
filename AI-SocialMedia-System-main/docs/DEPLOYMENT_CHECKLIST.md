# Production Deployment Checklist

Complete this checklist before deploying to production. Each section should be verified and signed off.

---

## Pre-Deployment Verification

### Code & Build
- [ ] All dependencies are updated: `npm audit`, `pip list --outdated`
- [ ] Production build compiles successfully: `npm run build`
- [ ] Zero ESLint warnings: `npm run lint`
- [ ] All tests pass: `npm test -- --watchAll=false`
- [ ] Backend tests pass: `pytest tests/`
- [ ] No secrets in codebase (`.env`, API keys, passwords)
- [ ] Git history is clean: `git log --oneline | head -20`

### Security Review
- [ ] `DEBUG=False` in `.env`
- [ ] `DEMO_ALLOW_SEED=false` in `.env`
- [ ] `ADMIN_API_KEY` is 32+ character random string
- [ ] Database password is strong (16+ chars, mixed case, numbers, symbols)
- [ ] CORS origins set to specific domain (not `*`)
- [ ] No hardcoded API keys in code
- [ ] SSL/TLS certificates obtained and placed in `./ssl/`
- [ ] HTTPS only (HTTP redirects to HTTPS)

### Configuration
- [ ] `.env` file created from `env.example`
- [ ] All required variables set:
  - [ ] `DATABASE_URL` (PostgreSQL for production)
  - [ ] `GOOGLE_PLACES_API_KEY`
  - [ ] `GOOGLE_SEARCH_API_KEY`
  - [ ] `ADMIN_API_KEY`
  - [ ] `CORS_ORIGINS`
  - [ ] `ENVIRONMENT=production`
- [ ] Optional variables configured (email, monitoring, etc.)
- [ ] PostgreSQL connection tested: `psql $DATABASE_URL`
- [ ] API keys tested and working

### Infrastructure
- [ ] Server meets minimum requirements (2GB RAM, 20GB storage)
- [ ] Docker and Docker Compose installed and working
- [ ] SSL certificates installed in `./ssl/` directory
- [ ] Firewall configured (allow 80, 443; restrict 22, 5432)
- [ ] DNS records pointing to server
- [ ] Domain resolves correctly: `nslookup your-domain.com`

---

## Deployment Steps

### Docker Compose Deployment
- [ ] Clone repository: `git clone https://github.com/yourusername/business-finder.git`
- [ ] Create `.env` file with production values
- [ ] Copy SSL certificates to `./ssl/`
- [ ] Build services: `docker-compose build`
- [ ] Start services: `docker-compose up -d`
- [ ] All services running: `docker-compose ps` shows all "Up"
- [ ] Database migrations completed (if using Alembic)
- [ ] Frontend build present: `docker-compose exec app ls -la build/`

### Verification
- [ ] Health check passing: `curl -k https://127.0.0.1/api/health`
- [ ] Frontend accessible: `curl -k https://127.0.0.1/`
- [ ] API endpoint working: `curl -k https://127.0.0.1/api/businesses`
- [ ] Admin API secured: `curl -k https://127.0.0.1/api/admin/seed_labels` returns 403 without key
- [ ] Database connected: Business count > 0
- [ ] Logs show no errors: `docker-compose logs --tail=50`

### DNS & Domain Setup
- [ ] Domain DNS records updated (A record pointing to server IP)
- [ ] Domain resolves: `curl https://your-domain.com/api/health`
- [ ] HTTPS working: `curl -v https://your-domain.com/`
- [ ] Certificate is valid: `openssl s_client -connect your-domain.com:443`
- [ ] Certificate auto-renewal configured

---

## Post-Deployment Tasks

### Monitoring Setup
- [ ] Health check monitored (uptime monitoring service)
- [ ] Error logging configured (Sentry, DataDog, or similar)
- [ ] Database backups automated
- [ ] Log rotation configured
- [ ] Resource alerts set up (memory, disk, CPU)
- [ ] Team notified of deployment

### Data Management
- [ ] Initial seed data loaded
- [ ] Backup of production database taken
- [ ] Database replication/failover configured (if applicable)
- [ ] Data retention policy set

### Documentation
- [ ] Deployment documented in team wiki/docs
- [ ] Rollback procedure documented
- [ ] Monitoring/alerting procedures documented
- [ ] On-call procedures updated
- [ ] Team trained on new system

---

## Operational Checklists

### Daily Operations
- [ ] Monitor application logs for errors
- [ ] Check resource usage (CPU, memory, disk)
- [ ] Verify API response times
- [ ] Check database size growth
- [ ] Monitor backup completion

### Weekly Operations
- [ ] Review application metrics and errors
- [ ] Check dependency updates available
- [ ] Verify automated backups are working
- [ ] Review SSL certificate expiration date
- [ ] Check API rate limits and abuse

### Monthly Operations
- [ ] Security audit (check for vulnerabilities)
- [ ] Performance analysis and optimization
- [ ] Database maintenance (VACUUM, ANALYZE)
- [ ] Update dependencies: `docker-compose build --pull`
- [ ] Review and rotate ADMIN_API_KEY
- [ ] Disaster recovery drill

---

## Troubleshooting Quick Reference

| Issue | Command | Solution |
|-------|---------|----------|
| Services won't start | `docker-compose logs` | Check environment variables, disk space |
| Database connection error | `docker-compose exec postgres pg_isready` | Verify DATABASE_URL, check PostgreSQL logs |
| SSL certificate error | `openssl x509 -in ssl/cert.pem -noout -dates` | Renew certificate with `certbot renew` |
| High memory usage | `docker-compose stats` | Increase memory limit or optimize queries |
| Slow API response | `curl -w "@curl-format.txt" https://your-domain.com/api/health` | Check database, add indexes, optimize queries |
| Disk space low | `df -h` | Remove old Docker images/containers, increase storage |

---

## Rollback Procedure

If deployment has critical issues:

```bash
# Option 1: Restart last working version
docker-compose down
git checkout <previous-working-commit>
docker-compose build
docker-compose up -d

# Option 2: Restore from database backup
docker-compose down
gunzip -c ./backups/backup_YYYYMMDD.sql.gz | \
  docker-compose exec -T postgres psql -U business_finder business_finder

# Option 3: Full system rollback
# Restore from infrastructure snapshot (if available)
```

Verify rollback:
```bash
curl -k https://your-domain.com/api/health
docker-compose ps
```

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| DevOps Engineer | ________________ | ________ | ________________ |
| Tech Lead | ________________ | ________ | ________________ |
| Product Manager | ________________ | ________ | ________________ |

---

## Deployment Summary

**Deployment Date**: ________________
**Deployed By**: ________________
**Deployment Method**: [ ] Docker Compose  [ ] Traditional Server
**Environment**: [ ] Staging  [ ] Production
**Incident Response Contact**: ________________
**Escalation Contact**: ________________

**Issues Encountered**: 
```
[Document any issues and resolutions]
```

**Notes**:
```
[Additional notes, configuration changes, etc.]
```

---

## Post-Deployment Review

**Date**: ________________
**Reviewed By**: ________________
**Status**: [ ] All Good  [ ] Issues Found  [ ] Needs Revision

**Metrics Summary**:
- API Response Time: __________ ms
- Error Rate: __________ %
- Database Size: __________ MB
- Memory Usage: __________ MB
- CPU Usage: __________ %

**Observations**:
```
[Notes on performance, issues, improvements needed]
```

---

For more information, see:
- [PRODUCTION.md](PRODUCTION.md) - Complete deployment guide
- [DOCKER_COMPOSE.md](DOCKER_COMPOSE.md) - Docker Compose guide
- [env.example](env.example) - Configuration options
- [README.md](README.md) - Project overview
