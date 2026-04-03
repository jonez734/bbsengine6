# Apache2 Python Integration for Runtime Markdown Conversion

## TL;DR

**Do NOT use mod_python** - it's unmaintained since 2013 and incompatible with Apache 2.4.

**Use one of these instead:**
1. **mod_wsgi** (simplest, one-module setup)
2. **mod_proxy + uWSGI** (production standard, most flexible)
3. **mod_proxy + Gunicorn** (modern, easier to debug)

---

## Why NOT mod_python?

### Status
- **Last Release:** March 2013 (mod_python 3.3.1)
- **Maintenance:** Abandoned/Dead
- **Apache 2.4:** NOT COMPATIBLE (only supports Apache 2.0/2.2)
- **Security:** No security updates since 2013

### Problems
```
Apache 2.4 (current standard)
    ↓
mod_python (Apache 2.0/2.2 only)
    ↗ INCOMPATIBLE
```

**Conclusion:** Do not waste time trying to use mod_python.

---

## Best Options for Apache 2.4+

### Option 1: mod_wsgi (Simplest)

**Status:** ✓ ACTIVELY MAINTAINED, Apache 2.4 compatible

**How It Works:**
```
Request → Apache → mod_wsgi → Python process → Flask app → HTML
```

**Installation:**
```bash
sudo apt-get install libapache2-mod-wsgi-py3
sudo a2enmod wsgi
```

**Configuration (handbook-wsgi.conf):**
```apache
WSGIDaemonProcess handbook user=www-data group=www-data threads=5
WSGIScriptAlias /handbook /path/to/handbook/wsgi.py
```

**Pros:**
- ✓ Single module installation
- ✓ Integrated into Apache process
- ✓ Simple configuration
- ✓ Works out-of-the-box
- ✓ Actively maintained

**Cons:**
- ✗ Python process crashes take down the module
- ✗ Harder to restart without restarting Apache
- ✗ Less isolated from Apache core

**Best For:**
- Simple applications
- Development/small sites
- When you want maximum simplicity

---

### Option 2: mod_proxy + uWSGI (Production Standard)

**Status:** ✓ ACTIVELY MAINTAINED (both components)

**How It Works:**
```
Request → Apache → mod_proxy → TCP/Unix socket → uWSGI → Flask app → HTML
```

**Installation:**
```bash
sudo apt-get install libapache2-mod-proxy-http
sudo pip install uwsgi
sudo a2enmod proxy proxy_http
```

**Configuration:**
```apache
ProxyPreserveHost On
ProxyPass /handbook http://127.0.0.1:5000/handbook
ProxyPassReverse /handbook http://127.0.0.1:5000/handbook
```

**uWSGI service (systemd):**
```ini
[Unit]
Description=BBSEngine Handbook uWSGI
After=network.target

[Service]
Type=notify
ExecStart=/usr/local/bin/uwsgi --ini /path/to/uwsgi.ini
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**uwsgi.ini:**
```ini
[uwsgi]
socket = 127.0.0.1:5000
wsgi-file = /path/to/wsgi.py
callable = application
processes = 4
threads = 2
master = true
vacuum = true
die-on-term = true
```

**Pros:**
- ✓ Industry standard for Python web apps
- ✓ Python process completely separate from Apache
- ✓ Can restart Python without restarting Apache
- ✓ Multiple worker processes for concurrency
- ✓ Can run on different machine (load balancing)
- ✓ Easy to debug (separate processes visible)
- ✓ Better isolation and stability

**Cons:**
- ✗ Slightly more complex setup
- ✗ Extra TCP/socket overhead (minimal)
- ✗ Requires separate service management

**Best For:**
- Production deployments
- Scaling to multiple servers
- High-traffic sites
- When stability is critical

---

### Option 3: mod_proxy + Gunicorn (Modern Alternative)

**Status:** ✓ ACTIVELY MAINTAINED

**How It Works:**
```
Request → Apache → mod_proxy → TCP/Unix socket → Gunicorn → Flask app → HTML
```

**Installation:**
```bash
sudo apt-get install libapache2-mod-proxy-http
sudo pip install gunicorn
sudo a2enmod proxy proxy_http
```

**Configuration:**
```apache
ProxyPreserveHost On
ProxyPass /handbook http://127.0.0.1:8000/handbook
ProxyPassReverse /handbook http://127.0.0.1:8000/handbook
```

**Gunicorn service (systemd):**
```ini
[Unit]
Description=BBSEngine Handbook Gunicorn
After=network.target

[Service]
Type=notify
ExecStart=/usr/local/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --chdir /path/to/handbook \
    wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Pros:**
- ✓ Simpler than uWSGI (fewer config options)
- ✓ Very popular in modern deployments
- ✓ Great documentation
- ✓ Easy to understand and debug
- ✓ Same benefits as uWSGI

**Cons:**
- ✗ One more moving part than mod_wsgi
- ✗ Requires systemd service management

**Best For:**
- Modern Python deployments
- Developers familiar with Gunicorn
- Simple production setups

---

## Comparison Matrix

| Feature | mod_wsgi | uWSGI | Gunicorn |
|---------|----------|-------|----------|
| **Maintenance** | ✓ Active | ✓ Active | ✓ Active |
| **Apache 2.4** | ✓ Yes | ✓ Yes | ✓ Yes |
| **Setup Complexity** | Simple | Medium | Medium |
| **Process Isolation** | No | Yes | Yes |
| **Restartability** | Hard | Easy | Easy |
| **Multiple Workers** | Yes | Yes | Yes |
| **Load Balancing** | No | Yes | Yes |
| **Debugging** | Moderate | Easy | Very Easy |
| **Industry Standard** | Still used | Yes | Most popular |
| **Production Ready** | Yes | Yes | Yes |
| **Small Sites** | ✓ Best | Overkill | Overkill |
| **Large Sites** | ✗ Limited | ✓ Best | ✓ Good |

---

## Quick Decision Tree

```
Does your site need:

High availability / Auto-restart?
├─ YES → Use mod_proxy + uWSGI or Gunicorn
└─ NO  → Check next

Multiple machines / Load balancing?
├─ YES → Use mod_proxy + uWSGI
└─ NO  → Check next

Production deployment?
├─ YES → Use mod_proxy + Gunicorn or uWSGI
└─ NO  → Check next

Just testing locally?
├─ YES → Use: python3 app.py (Flask dev server)
└─ NO  → Check next

Want simplicity over everything?
├─ YES → Use mod_wsgi
└─ NO  → Use mod_proxy + Gunicorn
```

---

## Detailed Implementation Guides

### Using mod_wsgi (Already Provided)

See: `handbook-wsgi.conf`

```bash
# Install
sudo apt-get install libapache2-mod-wsgi-py3
sudo a2enmod wsgi

# Configure
sudo cp handbook/handbook-wsgi.conf /etc/apache2/sites-available/
sudo a2ensite handbook-wsgi.conf

# Start
sudo systemctl restart apache2
```

**Pros:** Single command to enable and restart
**Cons:** Python crashes affect Apache

---

### Using mod_proxy + Gunicorn (Recommended for Production)

**1. Install Gunicorn:**
```bash
pip install gunicorn
```

**2. Create Apache config (handbook-gunicorn.conf):**
```apache
<VirtualHost *:80>
    ServerName handbook.bbsengine.org
    
    # Reverse proxy to Gunicorn
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    
    # Enable modules
    <IfModule mod_proxy.c>
        ProxyRequests Off
    </IfModule>
    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/handbook-error.log
    CustomLog ${APACHE_LOG_DIR}/handbook-access.log combined
</VirtualHost>
```

**3. Create systemd service (handbook-gunicorn.service):**
```ini
[Unit]
Description=BBSEngine Handbook Gunicorn
After=network.target
Wants=handbook-gunicorn.socket

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/home/opencode/data/work/bbsengine6/handbook
ExecStart=/usr/local/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind unix:/run/handbook.sock \
    --access-logfile /var/log/handbook-access.log \
    --error-logfile /var/log/handbook-error.log \
    wsgi:application
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**4. Enable and start:**
```bash
# Copy service file
sudo cp handbook-gunicorn.service /etc/systemd/system/

# Enable Apache modules
sudo a2enmod proxy proxy_http
sudo cp handbook-gunicorn.conf /etc/apache2/sites-available/
sudo a2ensite handbook-gunicorn.conf

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable handbook-gunicorn.service
sudo systemctl start handbook-gunicorn.service

# Restart Apache
sudo systemctl restart apache2
```

**5. Monitor:**
```bash
# Check status
sudo systemctl status handbook-gunicorn.service

# View logs
sudo journalctl -u handbook-gunicorn.service -f

# Restart without restarting Apache
sudo systemctl restart handbook-gunicorn.service
```

---

## Performance Characteristics

### Request Flow Overhead

```
mod_wsgi:
  Request → Apache → Python process → Flask → HTML
  Overhead: ~1-2ms (in-process)

mod_proxy + Gunicorn:
  Request → Apache → TCP socket → Gunicorn → Flask → HTML
  Overhead: ~2-4ms (inter-process communication)
```

Both are negligible compared to markdown conversion time (~20-50ms for complex docs).

### Memory Usage

```
mod_wsgi:
  - Python embedded in Apache
  - ~50-80 MB per Apache process

mod_proxy + Gunicorn:
  - Separate Gunicorn processes
  - ~20-30 MB per worker process
  - Can scale: start with 4, add more as needed
```

---

## Resilience and Reliability

### Crash Handling

**mod_wsgi:**
```
Python crash → Module becomes unavailable → Apache still running but 
/handbook returns 500 → Must restart Apache
```

**mod_proxy + Gunicorn:**
```
Gunicorn worker crash → Systemd auto-restarts → Requests queue briefly → 
Service recovers automatically → No Apache restart needed
```

### Restart Scenario

**Development (no restart needed):**
```bash
cd handbook && python3 app.py  # Dev server auto-reloads
```

**mod_wsgi:**
```bash
sudo systemctl restart apache2  # ENTIRE Apache restarts, all sites down
```

**mod_proxy + Gunicorn:**
```bash
sudo systemctl restart handbook-gunicorn.service  # Only handbook service restarts
```

---

## Deployment Recommendations

### For Development
```bash
# Simplest: Flask dev server with hot-reload
python3 app.py
```

### For Small Production Site
```bash
# Simplest: mod_wsgi one-liner
sudo apt-get install libapache2-mod-wsgi-py3
# Done! Just add config and restart Apache
```

### For Medium Production Site
```bash
# Recommended: mod_proxy + Gunicorn
# Gives you service isolation and auto-restart without much complexity
```

### For Large/Enterprise Site
```bash
# Standard: mod_proxy + uWSGI with multiple workers
# Or: Kubernetes/Docker deployment (separate infrastructure)
```

---

## Security Considerations

### mod_wsgi
- Python code in same process as Apache
- Buffer overflows in Python → Apache crash
- Privilege escalation risk if Apache is compromised

### mod_proxy + Gunicorn
- Separate processes = process isolation
- Gunicorn runs as www-data user (can restrict further)
- Apache crash doesn't affect Gunicorn
- Easier to sandbox with AppArmor/SELinux

---

## Troubleshooting

### mod_wsgi Issues
```bash
# Check if loaded
sudo apache2ctl -M | grep wsgi

# Check Apache config
sudo apache2ctl configtest

# Check logs
sudo tail -f /var/log/apache2/error.log

# Reload module
sudo systemctl restart apache2
```

### mod_proxy + Gunicorn Issues
```bash
# Check service status
sudo systemctl status handbook-gunicorn.service

# Check service logs
sudo journalctl -u handbook-gunicorn.service -n 50 -f

# Test Gunicorn directly
cd /path/to/handbook
gunicorn --workers 4 --bind 127.0.0.1:8000 wsgi:application

# Check Apache proxy
sudo apache2ctl configtest
curl -v http://localhost/handbook/
```

---

## Migration Path

If you start with one approach and need to switch:

### From Flask dev server → mod_wsgi
```bash
# 1. Copy Flask app unchanged
# 2. Create wsgi.py wrapper
# 3. Enable mod_wsgi
# 4. Restart Apache
# Time: 5 minutes, zero code changes
```

### From mod_wsgi → mod_proxy + Gunicorn
```bash
# 1. Copy Flask app unchanged
# 2. Create systemd service
# 3. Update Apache config (reverse proxy)
# 4. Enable proxy modules
# 5. Restart both
# Time: 10 minutes, zero code changes
```

**Flask application is portable** - the same `app.py` works everywhere!

---

## Final Recommendation for bbsengine.org

**Use mod_proxy + Gunicorn** because:

1. ✓ Industry standard approach
2. ✓ Excellent documentation and community
3. ✓ Service isolation (separate from Apache)
4. ✓ Easy to restart without affecting other sites
5. ✓ Simple auto-restart via systemd
6. ✓ Trivial to scale to multiple servers later
7. ✓ Easy to debug (separate processes in top/ps)
8. ✓ Not over-engineering for current needs
9. ✓ Future-proof for growth

**If you want simplicity:** Use mod_wsgi (one module, done)

**Never use:** mod_python (it's dead)

---

## Side-by-Side Setup Comparison

### mod_wsgi Setup
```bash
# 3 commands
sudo apt-get install libapache2-mod-wsgi-py3
sudo a2enmod wsgi
# Add config to Apache, restart
```

### mod_proxy + Gunicorn Setup
```bash
# More commands, but clearer separation
pip install gunicorn
sudo a2enmod proxy proxy_http
# Create systemd service
# Add Apache config
# Start service and Apache
```

---

## Conclusion

| Approach | Status | Use When |
|----------|--------|----------|
| **Flask dev server** | Good | Local development only |
| **mod_python** | ✗ DEAD | NEVER - incompatible, unmaintained |
| **mod_wsgi** | ✓ Working | Want maximum simplicity |
| **mod_proxy + uWSGI** | ✓ Standard | Production, enterprise scale |
| **mod_proxy + Gunicorn** | ✓ Recommended | Production, modern setup |

**For bbsengine.org: Use mod_proxy + Gunicorn**

It's the sweet spot between simplicity and production-readiness.
