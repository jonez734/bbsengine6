# Apache Python Integration - Quick Comparison

## The Bottom Line

**DON'T USE mod_python** - It's dead (2013) and incompatible with Apache 2.4.

**Use one of these instead:**

| Approach | Complexity | Best For | Setup Time |
|----------|-----------|----------|-----------|
| **mod_wsgi** | ⭐ Simple | Testing, small sites | 2 minutes |
| **mod_proxy + Gunicorn** | ⭐⭐ Medium | Production (recommended) | 10 minutes |
| **mod_proxy + uWSGI** | ⭐⭐⭐ Complex | Enterprise, scaling | 15 minutes |

---

## Why NOT mod_python?

```
mod_python 3.3.1 (last release: 2013)
    ↓ Only supports Apache 2.0/2.2
    ↓ Not compatible with Apache 2.4 (current standard)
    ↓ No security updates since 2013
    ↓ Abandoned/dead project
    ↓
CONCLUSION: DO NOT USE
```

---

## Quick Setup Guide

### Option 1: mod_wsgi (Simplest)

**Install:**
```bash
sudo apt-get install libapache2-mod-wsgi-py3
sudo a2enmod wsgi
```

**Configure:**
```bash
sudo cp handbook/handbook-wsgi.conf /etc/apache2/sites-available/
sudo a2ensite handbook-wsgi.conf
```

**Start:**
```bash
sudo systemctl restart apache2
```

**Restart Python (if code changes):**
```bash
sudo systemctl restart apache2  # Restarts entire Apache
```

**Pros:** One module, simple config
**Cons:** Python crash → Apache affected, must restart Apache for updates

---

### Option 2: mod_proxy + Gunicorn (Recommended for Production)

**Install:**
```bash
pip install gunicorn
sudo apt-get install libapache2-mod-proxy-http
sudo a2enmod proxy proxy_http
```

**Configure Gunicorn service:**
```bash
sudo cp handbook/handbook-gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable handbook-gunicorn.service
```

**Configure Apache:**
```bash
sudo cp handbook/handbook-gunicorn.conf /etc/apache2/sites-available/
sudo a2ensite handbook-gunicorn.conf
```

**Start:**
```bash
sudo systemctl start handbook-gunicorn.service
sudo systemctl restart apache2
```

**Restart Python (if code changes):**
```bash
sudo systemctl restart handbook-gunicorn.service  # Only restarts handbook
```

**Pros:** Separate processes, auto-restart, easy to debug
**Cons:** Slightly more setup, separate service to manage

---

## Architecture Diagrams

### mod_wsgi
```
Request
   ↓
Apache httpd
   ↓
mod_wsgi (in-process)
   ↓
Python process (same as Apache)
   ↓
Flask app
   ↓
HTML response
```

### mod_proxy + Gunicorn
```
Request
   ↓
Apache httpd (reverse proxy)
   ↓
TCP socket (127.0.0.1:8000)
   ↓
Gunicorn process (separate service)
   ↓
Flask app
   ↓
HTML response
```

---

## Failure Scenarios

### mod_wsgi Failure
```
Python crash
   ↓
mod_wsgi becomes unavailable
   ↓
/handbook/ returns 500 error
   ↓
Must restart Apache
   ↓
Entire site is restarting
```

### mod_proxy + Gunicorn Failure
```
Gunicorn crash
   ↓
systemd auto-restarts service (5 seconds)
   ↓
Service recovers automatically
   ↓
No Apache restart needed
   ↓
Other sites unaffected
```

---

## Monitoring

### mod_wsgi
```bash
# Check if module loaded
sudo apache2ctl -M | grep wsgi

# Restart if needed
sudo systemctl restart apache2

# View logs
sudo tail -f /var/log/apache2/error.log
```

### mod_proxy + Gunicorn
```bash
# Check service status
sudo systemctl status handbook-gunicorn.service

# View logs
sudo journalctl -u handbook-gunicorn.service -f

# Restart (without restarting Apache)
sudo systemctl restart handbook-gunicorn.service

# Check process
ps aux | grep gunicorn
```

---

## Performance

### Request Latency
- **mod_wsgi:** ~1-2ms overhead (in-process)
- **mod_proxy + Gunicorn:** ~2-4ms overhead (network)

**Reality:** Markdown conversion (~20-50ms) dominates, overhead is negligible

### Memory Usage
- **mod_wsgi:** ~50-80 MB per Apache process
- **mod_proxy + Gunicorn:** ~20-30 MB per worker, 4 workers = ~80-120 MB total

**Both reasonable for documentation serving**

---

## Production Recommendation

### For bbsengine.org

**Use mod_proxy + Gunicorn because:**

✓ Industry standard approach  
✓ Best documentation  
✓ Python process separate from Apache  
✓ Can restart without affecting other sites  
✓ Auto-restart on failure via systemd  
✓ Future-proof for scaling  
✓ Easier to debug  
✓ Not over-engineering  

**Setup cost:** 10 minutes  
**Long-term benefit:** Stability, scalability, maintainability  

---

## Files Provided

### For mod_wsgi
- `handbook-wsgi.conf` - Apache configuration
- `wsgi.py` - WSGI entry point
- `app.py` - Flask application (unchanged)

### For mod_proxy + Gunicorn
- `handbook-gunicorn.conf` - Apache reverse proxy configuration
- `handbook-gunicorn.service` - Systemd service file
- `app.py` - Flask application (unchanged)
- `wsgi.py` - WSGI entry point (unchanged)

### Documentation
- `APACHE_INTEGRATION.md` - Full comparison and setup guide
- `APACHE_QUICK_COMPARISON.md` - This file

---

## Testing Before Production

### Test Flask Directly
```bash
cd handbook
python3 app.py
# Visit http://localhost:5000/handbook/
```

### Test Gunicorn
```bash
cd handbook
gunicorn --workers 4 --bind 127.0.0.1:8000 wsgi:application
# Visit http://localhost:8000/handbook/
```

### Test Apache Proxy (after configuring)
```bash
curl -v http://localhost/handbook/
# Should proxy to Gunicorn
```

---

## Troubleshooting

### mod_wsgi Issues
```bash
# Test config
sudo apache2ctl configtest

# Check module loaded
sudo apache2ctl -M | grep wsgi

# View errors
sudo tail -f /var/log/apache2/error.log

# If module missing:
sudo apt-get install libapache2-mod-wsgi-py3
sudo a2enmod wsgi
```

### Gunicorn Issues
```bash
# Test Gunicorn directly
cd /path/to/handbook
gunicorn --workers 4 wsgi:application

# Check service status
sudo systemctl status handbook-gunicorn

# View service logs
sudo journalctl -u handbook-gunicorn -n 50 -f

# Verify listening
sudo netstat -tuln | grep 8000
sudo ss -tuln | grep 8000

# Check socket
ls -la /run/handbook.sock
```

### Apache Proxy Issues
```bash
# Test proxy config
sudo apache2ctl configtest

# Verify modules
sudo apache2ctl -M | grep proxy

# Test connectivity
curl -v http://127.0.0.1:8000/handbook/  # Direct to Gunicorn
curl -v http://localhost/handbook/       # Via Apache proxy

# View proxy logs
sudo tail -f /var/log/apache2/error.log
```

---

## Migration Path

### From Flask dev to Production

1. Keep `app.py` unchanged
2. Choose: mod_wsgi OR mod_proxy + Gunicorn
3. Follow setup for chosen approach
4. Test with `sudo systemctl restart apache2`
5. Deploy!

**Zero code changes needed** - Flask app is portable!

---

## Summary Table

| Aspect | mod_wsgi | Gunicorn |
|--------|----------|----------|
| **Ease** | ⭐⭐⭐ | ⭐⭐ |
| **Stability** | ⭐⭐ | ⭐⭐⭐ |
| **Scalability** | ⭐ | ⭐⭐⭐ |
| **Debug-ability** | ⭐ | ⭐⭐⭐ |
| **Auto-restart** | ✗ | ✓ |
| **Isolation** | ✗ | ✓ |
| **Industry std** | Declining | Growing |
| **Setup time** | 2 min | 10 min |
| **Recommendation** | Testing | Production |

---

## Final Decision

**For local testing:** Use `python3 app.py` (Flask dev server)

**For production:** Use **mod_proxy + Gunicorn**

**If you want simplicity:** Use mod_wsgi

**Never use:** mod_python (it's dead)

---

See `APACHE_INTEGRATION.md` for full details on each approach.
