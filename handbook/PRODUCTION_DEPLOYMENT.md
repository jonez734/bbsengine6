# Production Deployment Guide - Flask + Apache2

## Key Principle

**Never use Flask's development server in production.**

Flask's built-in development server is designed for development only:
- Single-threaded (can only handle one request at a time)
- No process restarting on crashes
- Security vulnerabilities exposed
- No performance optimization
- No logging/monitoring
- Unstable under load

---

## Production-Ready WSGI Servers

Here are all the production-ready options:

### 1. **uWSGI** (Recommended for Your Setup)

**Best For:** Your bbsengine.org with mod_proxy_uwsgi

```
Flask app
   ↓
uWSGI (4+ worker processes)
   ↓
mod_proxy_uwsgi (native Apache module)
   ↓
Apache httpd
   ↓
Client
```

**Advantages:**
- ✓ Native Apache integration via mod_proxy_uwsgi (already installed)
- ✓ Direct protocol (no TCP overhead)
- ✓ Advanced features (app pre-loading, lazy apps, etc.)
- ✓ Multiple worker processes
- ✓ Excellent performance
- ✓ Professional deployments use this

**Disadvantages:**
- ✗ Complex configuration
- ✗ Steeper learning curve
- ✗ More documentation scattered

**Installation:**
```bash
pip install uwsgi
```

**Basic Configuration:**
```ini
[uwsgi]
chdir = /path/to/handbook
module = wsgi:application
master = true
processes = 4
threads = 2
socket = 127.0.0.1:5000
protocol = uwsgi
```

---

### 2. **Gunicorn** (Most Popular)

**Best For:** Easy production deployment, most documentation

```
Flask app
   ↓
Gunicorn (4+ worker processes)
   ↓
mod_proxy_http (Apache reverse proxy)
   ↓
Apache httpd
   ↓
Client
```

**Advantages:**
- ✓ Simple configuration
- ✓ Excellent documentation
- ✓ Most popular (huge community)
- ✓ Multiple worker processes
- ✓ Good performance
- ✓ Easy to debug

**Disadvantages:**
- ✗ TCP socket overhead (not native Apache)
- ✗ Extra service to manage
- ✗ Requires reverse proxy

**Installation:**
```bash
pip install gunicorn
```

**Basic Configuration:**
```bash
gunicorn --workers 4 --bind 127.0.0.1:8000 wsgi:application
```

---

### 3. **Waitress** (Simplest)

**Best For:** Maximum simplicity, minimal config

```
Flask app
   ↓
Waitress (thread pool)
   ↓
mod_proxy_http (Apache reverse proxy)
   ↓
Apache httpd
   ↓
Client
```

**Advantages:**
- ✓ Pure Python (no C dependencies)
- ✓ Minimal configuration
- ✓ Works out of the box
- ✓ Good documentation
- ✓ No process management needed

**Disadvantages:**
- ✗ Thread-based (not process-based)
- ✗ Less performance than Gunicorn/uWSGI
- ✗ TCP socket overhead

**Installation:**
```bash
pip install waitress
```

**Basic Configuration:**
```bash
waitress-serve --port=8000 --workers=4 wsgi:application
```

---

### 4. **mod_wsgi** (Native Apache)

**Best For:** In-process execution, no extra service

```
Flask app
   ↓
mod_wsgi (Apache embedded)
   ↓
Apache httpd
   ↓
Client
```

**Advantages:**
- ✓ Native Apache module
- ✓ No separate process
- ✓ Fast (in-process)
- ✓ Simple deployment

**Disadvantages:**
- ✗ Python crash affects Apache
- ✗ Must restart Apache for code changes
- ✗ Less isolation/security
- ✗ Harder to scale

**Installation:**
```bash
sudo apt-get install libapache2-mod-wsgi-py3
```

---

### 5. **Daphne** (For Async)

**Best For:** Async Python, WebSocket support

```
Flask app (or FastAPI/Starlette async)
   ↓
Daphne (async event loop)
   ↓
mod_proxy_http (Apache reverse proxy)
   ↓
Apache httpd
   ↓
Client
```

**Advantages:**
- ✓ Async-native
- ✓ WebSocket support
- ✓ Good performance
- ✓ Simple configuration

**Disadvantages:**
- ✗ Only for async frameworks
- ✗ TCP socket overhead
- ✗ Requires async code

**Installation:**
```bash
pip install daphne
```

---

### 6. **Hypercorn** (Advanced Async)

**Best For:** Advanced async deployments, HTTP/2

```
Flask app (or async framework)
   ↓
Hypercorn (advanced async)
   ↓
mod_proxy_http (Apache reverse proxy)
   ↓
Apache httpd
   ↓
Client
```

**Advantages:**
- ✓ Advanced async features
- ✓ HTTP/2 support
- ✓ WebSocket support
- ✓ Excellent performance

**Disadvantages:**
- ✗ More complex
- ✗ Requires async code
- ✗ Overkill for simple apps

**Installation:**
```bash
pip install hypercorn
```

---

## Comparison Table

| Feature | uWSGI | Gunicorn | Waitress | mod_wsgi | Daphne | Hypercorn |
|---------|-------|----------|----------|----------|--------|-----------|
| **Status** | Production | Production | Production | Production | Production | Production |
| **Setup Ease** | Medium | Easy | Very Easy | Easy | Easy | Medium |
| **Performance** | Excellent | Very Good | Good | Fast | Very Good | Excellent |
| **Apache Integration** | Native mod_proxy_uwsgi | mod_proxy_http | mod_proxy_http | Native module | mod_proxy_http | mod_proxy_http |
| **Worker Model** | Process | Process | Thread | In-process | Async | Async |
| **Your Infrastructure** | ✓ HAS IT | ✗ Need proxy | ✗ Need proxy | ✓ Available | ✗ Need proxy | ✗ Need proxy |
| **Documentation** | Good | Excellent | Good | Good | Good | Good |
| **Community Size** | Large | Largest | Medium | Medium | Medium | Small |
| **Isolation** | Excellent | Excellent | Good | Poor | Excellent | Excellent |
| **For Your App** | ✓ BEST | Good | Simple | Alternative | Not needed | Not needed |

---

## Production Recommendations

### For Your bbsengine.org Handbook

**Recommended:** **uWSGI**

```
Why:
  ✓ mod_proxy_uwsgi already installed
  ✓ Native Apache integration (no TCP overhead)
  ✓ Professional deployments use this
  ✓ Excellent performance
  ✓ Process isolation and reliability
  ✓ Your infrastructure supports it
```

**Configuration:**

```ini
[uwsgi]
# Application
chdir = /home/opencode/data/work/bbsengine6/handbook
module = wsgi:application
callable = application

# Master/workers
master = true
processes = 4              # Number of worker processes
threads = 2                # Threads per worker

# Sockets and protocol
socket = 127.0.0.1:5000
protocol = uwsgi           # Use uwsgi protocol for mod_proxy_uwsgi

# Lifecycle
max-requests = 5000        # Reload worker after N requests
max-requests-delta = 100   # Randomize to avoid thundering herd
reload-mercy = 8           # Grace period for reloads
worker-reload-mercy = 60   # Longer grace for worker reloads
worker-lifetime = 3600     # Recycle workers every hour

# Logging
logto = /var/log/uwsgi/handbook.log
log-4xx = true
log-5xx = true

# Performance
listen = 1024              # Socket backlog
buffer-size = 32768        # Buffer size

# Cleanup
vacuum = true              # Clean up socket on exit
auto-restart = true        # Restart on crash
```

---

### If You Want Simplicity: Gunicorn

**Alternative:** **Gunicorn** (if you prefer simpler setup)

```
Why:
  ✓ Easiest configuration
  ✓ Best documentation
  ✓ Largest community
  ✓ Very popular (team likely familiar)
  ✓ Good performance
```

**Installation:**
```bash
pip install gunicorn
```

**Run:**
```bash
gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/gunicorn/handbook-access.log \
    --error-logfile /var/log/gunicorn/handbook-error.log \
    wsgi:application
```

**Apache Config (reverse proxy):**
```apache
ProxyPass /handbook/ http://127.0.0.1:8000/handbook/
ProxyPassReverse /handbook/ http://127.0.0.1:8000/handbook/
```

---

### If You Want Absolute Simplicity: Waitress

**Alternative:** **Waitress** (minimal config)

```bash
pip install waitress
waitress-serve --port=8000 --workers=4 wsgi:application
```

---

### If You Have Async Code: Daphne or Hypercorn

For Flask alone, **don't use these** (overkill).

Only use if you're upgrading to FastAPI or async code later.

---

## What NOT to Use in Production

### ❌ Flask Development Server

```python
if __name__ == '__main__':
    app.run(debug=True)  # NEVER in production!
```

**Problems:**
- Single-threaded
- No process management
- Security issues
- Not designed for production

### ❌ Flask with Threaded Mode

```python
app.run(threaded=True)  # Still development-only!
```

**Problems:**
- Still development server
- Not suitable for production load
- GIL contention with threads

---

## Recommended Production Setup for bbsengine.org

### Option 1: uWSGI (Recommended)

```
Installation:
  $ pip install uwsgi

Configuration:
  Create /etc/uwsgi/apps-available/handbook.ini
  Create /etc/apache2/sites-available/handbook.conf
  Enable: a2enmod proxy proxy_uwsgi
  Start: systemctl start uwsgi-handbook

Apache Config:
  ProxyPass /handbook/ uwsgi://127.0.0.1:5000/handbook/

Benefits:
  ✓ Native Apache integration (mod_proxy_uwsgi)
  ✓ Excellent performance
  ✓ Professional standard
  ✓ Already have the module
  ✓ Process isolation
```

### Option 2: Gunicorn (If You Prefer Simplicity)

```
Installation:
  $ pip install gunicorn

Configuration:
  Create /etc/systemd/system/gunicorn-handbook.service
  Create /etc/apache2/sites-available/handbook.conf
  Enable: a2enmod proxy proxy_http
  Start: systemctl start gunicorn-handbook

Apache Config:
  ProxyPass /handbook/ http://127.0.0.1:8000/handbook/

Benefits:
  ✓ Simple configuration
  ✓ Excellent documentation
  ✓ Large community
  ✓ Good performance
```

---

## Performance Considerations

### Worker Count

For handbook app (I/O bound - markdown conversion):

```
CPU cores: 4
Recommendation: processes = 4 to 8

Formula: (2 × CPU cores) + 1
  = (2 × 4) + 1 = 9 workers (for I/O-bound)
```

### Memory Per Worker

Typical Flask app: 30-50 MB per worker

For 4 workers: ~150-200 MB
For 8 workers: ~300-400 MB

**Monitor:**
```bash
# Check memory usage
ps aux | grep uwsgi
top -p $(pgrep -f uwsgi)
```

### Request Handling

**Max Requests Per Worker:**
```ini
max-requests = 5000        # Reload after 5000 requests
max-requests-delta = 100   # Random 5000-5100 range
```

This prevents memory leaks from accumulating.

---

## Monitoring in Production

### Check Service Status

```bash
# For uWSGI
sudo systemctl status uwsgi-handbook
sudo journalctl -u uwsgi-handbook -f

# For Gunicorn
sudo systemctl status gunicorn-handbook
sudo journalctl -u gunicorn-handbook -f
```

### Monitor Performance

```bash
# Check processes
ps aux | grep -E 'uwsgi|gunicorn'

# Check listening ports
sudo netstat -tuln | grep 5000

# Check Apache proxy
curl -v http://localhost/handbook/
```

### Monitor Logs

```bash
# uWSGI logs
tail -f /var/log/uwsgi/handbook.log

# Gunicorn logs
tail -f /var/log/gunicorn/handbook-access.log
tail -f /var/log/gunicorn/handbook-error.log

# Apache logs
tail -f /var/log/apache2/handbook-error.log
tail -f /var/log/apache2/handbook-access.log
```

---

## Systemd Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start uwsgi-handbook

# Stop service
sudo systemctl stop uwsgi-handbook

# Restart service
sudo systemctl restart uwsgi-handbook

# Reload (graceful restart)
sudo systemctl reload uwsgi-handbook

# Enable on boot
sudo systemctl enable uwsgi-handbook

# Check status
sudo systemctl status uwsgi-handbook
```

### Auto-Restart on Failure

Systemd automatically restarts on failure:

```ini
[Service]
Restart=on-failure
RestartSec=5s
```

---

## Security Checklist

- [ ] Never use Flask dev server
- [ ] Use a production WSGI server
- [ ] Run as non-root user (www-data)
- [ ] Enable logging
- [ ] Monitor performance
- [ ] Set up log rotation
- [ ] Use systemd for process management
- [ ] Set up alerting for crashes
- [ ] Use HTTPS in production
- [ ] Set security headers in Apache

---

## Troubleshooting

### App Won't Start

```bash
# Test directly
cd /path/to/handbook
uwsgi --ini handbook.ini --show-config

# Check syntax
python3 -c "from wsgi import application; print(application)"
```

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :5000
sudo netstat -tuln | grep 5000

# Kill the process
sudo kill -9 <PID>
```

### Permission Denied

```bash
# Check permissions
ls -la /path/to/handbook

# Check socket permissions
ls -la /run/uwsgi-handbook.sock

# Fix if needed
sudo chown www-data:www-data /run/uwsgi-handbook.sock
sudo chmod 666 /run/uwsgi-handbook.sock
```

### Application Errors

```bash
# Check application logs
tail -f /var/log/uwsgi/handbook.log

# Check Apache proxy logs
tail -f /var/log/apache2/error.log

# Test Flask directly
cd /path/to/handbook
python3 -c "from app import app; app.run(debug=True)"
```

---

## Summary

| Aspect | Dev | Production |
|--------|-----|-----------|
| **Server** | Flask dev server | uWSGI / Gunicorn / etc |
| **Workers** | 1 (single-threaded) | 4+ (multi-process) |
| **Security** | Minimal | Full headers, SSL, etc |
| **Performance** | Low | High (multi-worker) |
| **Monitoring** | None | Logging, auto-restart |
| **Reliability** | Low (crashes stop app) | High (auto-restart) |
| **Scalability** | N/A | Can add workers/machines |

**For bbsengine.org:** Use **uWSGI** with **mod_proxy_uwsgi**

See: `APACHE_UWSGI_SETUP.md` for complete setup instructions.
