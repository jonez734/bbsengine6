# Apache2 + mod_proxy_uwsgi Setup for BBSEngine Handbook

## Great News!

Your zoidlan infrastructure already has **mod_proxy_uwsgi** configured, which is perfect for running Python applications with Apache2.

This is **better than mod_wsgi or Gunicorn** for your environment because:
- ✓ Already installed and available
- ✓ Optimized for Python WSGI applications
- ✓ Better performance than mod_wsgi
- ✓ Process isolation like mod_proxy + Gunicorn
- ✓ Official Apache module (not third-party)

---

## Architecture

```
Request
   ↓
Apache httpd (your reverse proxy)
   ↓
mod_proxy_uwsgi (native Apache module)
   ↓
uWSGI process (separate, auto-managed)
   ↓
Flask application
   ↓
HTML response
```

This is the **native Apache approach** - cleaner than mod_proxy + TCP socket.

---

## Quick Setup (5 minutes)

### 1. Install uWSGI

```bash
pip install uwsgi
```

### 2. Create Apache Configuration

Based on your existing `/etc/apache2/mods-available/proxy_uwsgi.load`:

Create `/etc/apache2/sites-available/handbook.conf`:

```apache
<VirtualHost *:80>
    ServerName handbook.bbsengine.org
    ServerAlias docs.bbsengine.org

    DocumentRoot /home/opencode/data/work/bbsengine6/handbook

    # Enable proxy modules
    <IfModule mod_proxy.c>
        ProxyPreserveHost On

        # Use mod_proxy_uwsgi to connect to uWSGI
        # Format: uwsgi://socket or uwsgi://host:port
        ProxyPass /handbook/ uwsgi://127.0.0.1:5000/handbook/
        ProxyPassReverse /handbook/ uwsgi://127.0.0.1:5000/handbook/
    </IfModule>

    # Security headers
    <IfModule mod_headers.c>
        Header set X-Content-Type-Options "nosniff"
        Header set X-Frame-Options "SAMEORIGIN"
        Header set X-XSS-Protection "1; mode=block"
    </IfModule>

    # Compression
    <IfModule mod_deflate.c>
        AddOutputFilterByType DEFLATE text/html text/plain text/xml application/json
    </IfModule>

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/handbook-error.log
    CustomLog ${APACHE_LOG_DIR}/handbook-access.log combined
</VirtualHost>
```

### 3. Enable Modules

```bash
# mod_proxy and mod_proxy_uwsgi should already be available
sudo a2enmod proxy proxy_uwsgi
sudo a2enmod headers deflate
```

### 4. Create uWSGI Configuration

Create `/etc/uwsgi/apps-available/handbook.ini`:

```ini
[uwsgi]
# Application
chdir = /home/opencode/data/work/bbsengine6/handbook
module = wsgi:application
master = true

# Socket
socket = 127.0.0.1:5000
protocol = uwsgi

# Processes
processes = 4
threads = 2
worker-reload-mercy = 60
worker-lifetime = 3600
reload-on-as = 256

# Logging
logto = /var/log/uwsgi/handbook.log

# Daemonize
daemonize = /var/log/uwsgi/handbook-daemon.log

# Auto-restart
auto-restart = true
vacuum = true
```

### 5. Create systemd Service (Optional but Recommended)

Create `/etc/systemd/system/uwsgi-handbook.service`:

```ini
[Unit]
Description=uWSGI service for BBSEngine Handbook
After=network.target
Wants=uwsgi-handbook.socket

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/home/opencode/data/work/bbsengine6/handbook
ExecStart=/usr/local/bin/uwsgi \
    --ini /etc/uwsgi/apps-available/handbook.ini \
    --socket 127.0.0.1:5000 \
    --protocol=uwsgi \
    --processes 4 \
    --threads 2
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 6. Start Services

```bash
# Enable Apache config
sudo a2ensite handbook.conf

# Enable and start uWSGI service
sudo systemctl daemon-reload
sudo systemctl enable uwsgi-handbook.service
sudo systemctl start uwsgi-handbook.service

# Restart Apache
sudo systemctl restart apache2
```

### 7. Test

```bash
curl -v http://localhost/handbook/
# Should return markdown documentation

# Check uWSGI is running
ps aux | grep uwsgi

# Check logs
sudo tail -f /var/log/uwsgi/handbook.log
```

---

## Why mod_proxy_uwsgi is Better

| Aspect | mod_proxy + Gunicorn | mod_proxy_uwsgi (uWSGI) |
|--------|---------------------|------------------------|
| **Setup** | External app | Integrated |
| **Performance** | TCP overhead | Direct protocol |
| **Modules** | Apache + Gunicorn | Apache native |
| **Complexity** | 2 services | 1 service |
| **Configuration** | Apache + systemd | Apache only |
| **Standards** | Industry standard | Apache native |
| **Your Infrastructure** | ✗ Not ready | ✓ Already available |

**For your bbsengine.org:** Use mod_proxy_uwsgi (it's already there!)

---

## uWSGI vs Gunicorn Comparison

### uWSGI
```
Pros:
  ✓ Works natively with mod_proxy_uwsgi
  ✓ Better integration with Apache
  ✓ Can use Unix sockets (faster)
  ✓ More configuration options
  ✓ Better for complex deployments

Cons:
  ✗ More complex configuration
  ✗ Larger learning curve
  ✗ Documentation scattered
```

### Gunicorn
```
Pros:
  ✓ Simpler configuration
  ✓ Better documentation
  ✓ Easier to understand
  ✓ Popular with beginners

Cons:
  ✗ Requires TCP socket overhead
  ✗ Not native Apache integration
  ✗ Extra service management
```

**For your setup:** uWSGI is already available, so use it!

---

## Advanced Configuration

### Use Unix Socket Instead of TCP

More efficient than TCP (no network overhead):

```apache
# In Apache config
ProxyPass /handbook/ uwsgi:unix:/run/uwsgi-handbook.sock|uwsgi:/handbook/
```

```ini
# In uWSGI config
socket = /run/uwsgi-handbook.sock
chmod-socket = 666
```

### Multiple Processes

```ini
[uwsgi]
# 8 processes for high-traffic
processes = 8
threads = 4

# Memory limit per process
memory-report = true
reload-on-as = 256
```

### Caching Headers

```apache
# In Apache config
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresDefault "access plus 1 hour"
</IfModule>
```

---

## Monitoring

### Check Service Status

```bash
sudo systemctl status uwsgi-handbook.service
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u uwsgi-handbook.service -f

# Or from uWSGI log file
tail -f /var/log/uwsgi/handbook.log
```

### Monitor Processes

```bash
ps aux | grep -i uwsgi
top -p $(pgrep -f uwsgi)
```

### Check Apache Configuration

```bash
sudo apache2ctl configtest
sudo apache2ctl -M | grep proxy
```

---

## Troubleshooting

### Module Not Found

```bash
# Check if module is available
ls /usr/lib/apache2/modules/mod_proxy_uwsgi.so

# If missing, install:
sudo apt-get install libapache2-mod-proxy-uwsgi
```

### Socket Connection Refused

```bash
# Check if uWSGI is listening
sudo netstat -tuln | grep 5000
sudo ss -tuln | grep 5000

# Check if process is running
ps aux | grep uwsgi
```

### Apache Configuration Error

```bash
# Test Apache config
sudo apache2ctl configtest

# If OK, reload
sudo systemctl reload apache2
```

### Permission Denied

```bash
# Ensure www-data can connect to socket
sudo chown www-data:www-data /run/uwsgi-handbook.sock
sudo chmod 666 /run/uwsgi-handbook.sock
```

---

## Restarting Services

### Restart uWSGI Only (without Apache)

```bash
sudo systemctl restart uwsgi-handbook.service
```

### Reload uWSGI (graceful, no downtime)

```bash
sudo systemctl reload uwsgi-handbook.service
```

### Restart Apache

```bash
sudo systemctl restart apache2
```

---

## Integration with zoidlan Infrastructure

Your zoidlan setup already has:

```
zoidlan/merlin/jammy/apache2/
├── mods-available/
│   ├── proxy.load          ✓ (base proxy module)
│   ├── proxy_uwsgi.load    ✓ (uWSGI proxy module)
│   └── ...
├── sites-available/
│   ├── bbsenginedotorg.conf
│   ├── engine.conf
│   └── ...
└── ...
```

This means you're already set up for uWSGI applications. Just add:
1. Create `handbook.conf` in sites-available
2. Enable it with `a2ensite handbook.conf`
3. Start uWSGI service
4. Restart Apache

---

## Performance Tuning

### Socket Buffer Size

```apache
# In Apache config
ProxyIOBufferSize 32768
```

### Process Tuning

```ini
# In uWSGI config
[uwsgi]
processes = 4           # CPU cores * 2
threads = 2             # For I/O-bound
listen = 1024          # Socket backlog
```

### Enable Caching

```apache
<IfModule mod_cache.c>
    <IfModule mod_cache_disk.c>
        CacheEnable disk /handbook/
        CacheRoot /var/cache/apache2
        CacheQuickHandler off
    </IfModule>
</IfModule>
```

---

## Production Checklist

- [ ] uWSGI installed (`pip install uwsgi`)
- [ ] Apache modules enabled (`a2enmod proxy proxy_uwsgi`)
- [ ] Configuration files created
- [ ] Permissions correct (www-data user)
- [ ] Service enabled (`systemctl enable`)
- [ ] Services started (`systemctl start`)
- [ ] Apache config tested (`apache2ctl configtest`)
- [ ] Application tested (`curl http://localhost/handbook/`)
- [ ] Logs monitored (`journalctl -u uwsgi-handbook -f`)
- [ ] Performance verified (response times, load)
- [ ] Backups configured
- [ ] Monitoring/alerting set up

---

## Files Provided

In `/home/opencode/data/work/bbsengine6/handbook/`:

- `app.py` - Flask application (unchanged)
- `wsgi.py` - WSGI entry point (unchanged)
- `APACHE_UWSGI_SETUP.md` - This file
- `APACHE_QUICK_COMPARISON.md` - Comparison of all approaches
- `APACHE_INTEGRATION.md` - Detailed Apache analysis

---

## See Also

- **Apache mod_proxy_uwsgi docs:** https://httpd.apache.org/docs/current/mod/mod_proxy_uwsgi.html
- **uWSGI docs:** https://uwsgi-docs.readthedocs.io/
- **Your infrastructure:** `/home/opencode/data/work/zoidlan/merlin/jammy/apache2/`

---

## Final Recommendation

For **bbsengine.org**, use **mod_proxy_uwsgi** because:

1. ✓ Already available in your infrastructure
2. ✓ Better than mod_wsgi (native Apache module)
3. ✓ Better than mod_proxy + Gunicorn (no TCP overhead)
4. ✓ Professional, stable approach
5. ✓ Perfect for your zoidlan setup

**Setup time:** 5-10 minutes  
**Complexity:** Medium  
**Maintenance:** Simple (`systemctl restart uwsgi-handbook`)  
**Reliability:** High (auto-restart via systemd)  

This is the **cleanest solution for your environment**.
