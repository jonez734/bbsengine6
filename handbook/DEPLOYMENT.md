# Production Deployment

> Status: canonical. Updated 2026-09-04.
> Replaces: `PRODUCTION_DEPLOYMENT.md`, `APACHE_INTEGRATION.md`,
> `APACHE_QUICK_COMPARISON.md`, `APACHE_UWSGI_SETUP.md`.

## Options

Three viable paths for putting bbsengine6 behind Apache httpd. The
comparison data below is reconciled from the four source docs;
**mod_proxy_uwsgi is recommended** because the production host
already has the module installed and `zoidlan/merlin/jammy/apache2/`
ships `proxy_uwsgi.load` enabled.

| Approach | Setup time | Process isolation | Restart blast radius | Best for |
|---|---|---|---|---|
| **mod_proxy_uwsgi** | ~10 min | Yes (separate uWSGI process) | Handbook service only | **Production (recommended)** |
| mod_wsgi | ~2 min | No (embedded in Apache) | Entire Apache | Simple sites, internal tools |
| mod_proxy + gunicorn | ~10 min | Yes (separate gunicorn process) | Handbook service only | Operators familiar with gunicorn |

**Do not use `mod_python`.** It has been unmaintained since 2013, is
not compatible with Apache 2.4, and has had no security updates in over
a decade. Every Apache integration source doc agrees on this point;
the four-way comparison collapsed cleanly here.

**Do not run the Flask development server in production.** It is
single-threaded, has no process supervision, and is explicitly
designed for development only.

## mod_proxy_uwsgi (recommended for production)

This is the path used on the production host. uWSGI runs as a
separate systemd-managed service; Apache terminates TLS and proxies
via the native `mod_proxy_uwsgi` module — no TCP loopback overhead.

### Architecture

```
Request ↓
Apache httpd
   ↓
mod_proxy_uwsgi (native Apache module)
   ↓
uWSGI process (separate, systemd-managed)
   ↓
Flask application (handbook/app.py)
   ↓
HTML response
```

### Apache configuration

Create `/etc/apache2/sites-available/handbook.conf`:

```apache
<VirtualHost *:80>
    ServerName handbook.bbsengine.org
    ServerAlias docs.bbsengine.org

    DocumentRoot /home/opencode/data/work/bbsengine6/handbook

    <IfModule mod_proxy.c>
        ProxyPreserveHost On
        ProxyPass /handbook/ uwsgi://127.0.0.1:5000/handbook/
        ProxyPassReverse /handbook/ uwsgi://127.0.0.1:5000/handbook/
    </IfModule>

    <IfModule mod_headers.c>
        Header set X-Content-Type-Options "nosniff"
        Header set X-Frame-Options "SAMEORIGIN"
        Header set X-XSS-Protection "1; mode=block"
    </IfModule>

    <IfModule mod_deflate.c>
        AddOutputFilterByType DEFLATE text/html text/plain text/xml application/json
    </IfModule>

    ErrorLog ${APACHE_LOG_DIR}/handbook-error.log
    CustomLog ${APACHE_LOG_DIR}/handbook-access.log combined
</VirtualHost>
```

### uWSGI configuration

Create `/etc/uwsgi/apps-available/handbook.ini`:

```ini
[uwsgi]
chdir = /home/opencode/data/work/bbsengine6/handbook
module = wsgi:application
master = true

socket = 127.0.0.1:5000
protocol = uwsgi

processes = 4
threads = 2
worker-reload-mercy = 60
worker-lifetime = 3600
reload-on-as = 256

logto = /var/log/uwsgi/handbook.log
daemonize = /var/log/uwsgi/handbook-daemon.log

auto-restart = true
vacuum = true
```

### systemd unit

Create `/etc/systemd/system/uwsgi-handbook.service`:

```ini
[Unit]
Description=uWSGI service for BBSEngine Handbook
After=network.target

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

### Bring-up

```bash
sudo a2enmod proxy proxy_uwsgi
sudo a2enmod headers deflate
sudo a2ensite handbook.conf
sudo systemctl daemon-reload
sudo systemctl enable uwsgi-handbook.service
sudo systemctl start uwsgi-handbook.service
sudo systemctl restart apache2
```

Verify:

```bash
curl -v http://localhost/handbook/
ps aux | grep uwsgi
sudo tail -f /var/log/uwsgi/handbook.log
```

### Tuning

For higher throughput on a 4-core host, raise to `processes = 8` and
`threads = 4` (I/O-bound load — markdown conversion is CPU-light).
Adjust `listen = 1024` and `buffer-size = 32768` in the `[uwsgi]`
block if you see `listen queue overflow` in the logs.

To swap the TCP loopback for a Unix socket (faster, no port
collision risk):

```apache
ProxyPass /handbook/ uwsgi:unix:/run/uwsgi-handbook.sock|uwsgi:/handbook/
```

```ini
socket = /run/uwsgi-handbook.sock
chmod-socket = 666
```

```bash
sudo chown www-data:www-data /run/uwsgi-handbook.sock
```

## mod_wsgi (alternative — simplest)

`mod_wsgi` embeds the Python app inside Apache. One module install, no
extra service. Trade-off: a Python crash disables the module until
Apache restarts, and the entire Apache restarts whenever you ship new
Python code.

### Install

```bash
sudo apt-get install libapache2-mod-wsgi-py3
sudo a2enmod wsgi
```

### Configuration

`handbook/handbook-wsgi.conf` (already in the repo):

```apache
WSGIDaemonProcess handbook user=www-data group=www-data threads=5 processes=2
WSGIScriptAlias /handbook /home/opencode/data/work/bbsengine6/handbook/wsgi.py

<Directory /home/opencode/data/work/bbsengine6/handbook>
    WSGIProcessGroup handbook
    WSGIApplicationGroup %{GLOBAL}
    Require all granted

    <IfModule mod_headers.c>
        Header set X-Content-Type-Options "nosniff"
        Header set X-Frame-Options "SAMEORIGIN"
        Header set X-XSS-Protection "1; mode=block"
        Header set Referrer-Policy "strict-origin-when-cross-origin"
    </IfModule>

    <IfModule mod_expires.c>
        ExpiresActive On
        ExpiresDefault "access plus 1 hour"
    </IfModule>

    <IfModule mod_deflate.c>
        AddOutputFilterByType DEFLATE text/html text/plain text/xml application/json text/javascript
    </IfModule>
</Directory>

<IfModule mod_alias.c>
    AliasMatch ^/handbook/(.*\.(?:css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot))$ \
        /home/opencode/data/work/bbsengine6/handbook/static/$1
</IfModule>

<Directory /home/opencode/data/work/bbsengine6/handbook/static>
    Require all granted
    <IfModule mod_expires.c>
        ExpiresActive On
        ExpiresByType image/* "access plus 1 month"
        ExpiresByType font/* "access plus 1 month"
        ExpiresByType text/css "access plus 1 week"
        ExpiresByType application/javascript "access plus 1 week"
    </IfModule>
</Directory>

ErrorLog ${APACHE_LOG_DIR}/handbook-error.log
CustomLog ${APACHE_LOG_DIR}/handbook-access.log combined
```

```bash
sudo cp handbook/handbook-wsgi.conf /etc/apache2/sites-available/
sudo a2ensite handbook-wsgi.conf
sudo systemctl restart apache2
```

To reload Python code: `sudo systemctl restart apache2`. The whole
server restarts.

## gunicorn + mod_proxy (alternative)

> **Status: alternative, not the production path on `bbsengine.org`.**
> The production host runs uWSGI behind `mod_proxy_uwsgi` — see
> [mod_proxy_uwsgi](#mod_proxy_uwsgi-recommended-for-production)
> above. This section exists for operators who already run gunicorn
> elsewhere and prefer its operational model.

gunicorn over `mod_proxy_http` — process-isolated like uWSGI but with
the most popular Python WSGI server. Pick this if your team already
knows gunicorn.

### Install

```bash
pip install gunicorn
sudo a2enmod proxy proxy_http
```

### Apache vhost

```apache
<VirtualHost *:80>
    ServerName handbook.bbsengine.org

    ProxyPreserveHost On
    ProxyPass /handbook/ http://127.0.0.1:8000/handbook/
    ProxyPassReverse /handbook/ http://127.0.0.1:8000/handbook/

    ErrorLog ${APACHE_LOG_DIR}/handbook-error.log
    CustomLog ${APACHE_LOG_DIR}/handbook-access.log combined
</VirtualHost>
```

### systemd unit (`/etc/systemd/system/handbook-gunicorn.service`)

The shipped `handbook/handbook-gunicorn.service` is the authoritative
copy. The block below mirrors it for inline reference; if the two
diverge, trust the file in the repo.

```ini
[Unit]
Description=BBSEngine Handbook Gunicorn Application Server (alternative, non-production)
Documentation=https://gunicorn.org/
Documentation=file:///home/opencode/data/work/bbsengine6/handbook/DEPLOYMENT.md
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/home/opencode/data/work/bbsengine6/handbook
ExecStart=/usr/local/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --bind 127.0.0.1:8000 \
    --timeout 30 \
    --graceful-timeout 30 \
    --access-logfile /var/log/handbook-access.log \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
    --error-logfile /var/log/handbook-error.log \
    --log-level info \
    wsgi:application

# Reload on config change (SIGHUP). Gunicorn also reopens access/error
# log files on SIGHUP, which logrotate relies on.
ExecReload=/bin/kill -s HUP $MAINPID

Restart=on-failure
RestartSec=5s

KillMode=mixed
KillSignal=SIGTERM

# Service hardening
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log /var/log/handbook

StandardOutput=journal
StandardError=journal
SyslogIdentifier=handbook-gunicorn

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable handbook-gunicorn.service
sudo systemctl start handbook-gunicorn.service
sudo a2ensite handbook-gunicorn.conf
sudo systemctl restart apache2
```

The shipped unit binds TCP only (`127.0.0.1:8000`), which is what the
Apache vhost above proxies to. If you prefer a Unix socket, switch
the unit to `--bind unix:/run/handbook.sock` and replace the Apache
`ProxyPass` line with:

```apache
ProxyPass /handbook/ unix:/run/handbook.sock|http://127.0.0.1/handbook/
```

## Production checklist

Security, log hygiene, and operational readiness — applies regardless
of which deployment path you chose.

### Security headers

The vhost config above already sets `X-Content-Type-Options`,
`X-Frame-Options`, `X-XSS-Protection`, and `Referrer-Policy`. Add
HSTS once TLS is terminated at Apache:

```apache
<IfModule mod_headers.c>
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
</IfModule>
```

Do not echo raw `PDOException` text to clients. The
`bbsengine6\util\echo_traceback` helper (Phase 3 finding 3.2 in
[`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md)) logs the full
exception to syslog and emits a generic error string instead.

### Session cookie hardening

The session cookie (`php/session.php`) sets `Secure`, `HttpOnly`, and
`SameSite=Lax` (Phase 3 findings 3.4, 3.5, 3.6). `$secure` is
auto-derived from `$_SERVER['HTTPS']` and `HTTP_X_FORWARDED_PROTO`
so reverse-proxy setups work.

### Path traversal

All filesystem reads in `engine/router.php` and `php/folder.php` go
through `bbsengine6\util\safe_path_web()`, which resolves both the
base and the requested path to absolute paths and asserts the result
is inside the base.

### CSRF

`csrfCheckRequest()` (in `php/util.php`) defaults to backward-compatible
behavior (GET requests without a token are accepted). For new
state-changing endpoints, pass `requireOnGet: true` so GET requests
also require a token. The CSRF detail is in
[./csrf/README.md](./csrf/README.md).

### Log rotation

uWSGI and gunicorn both write to `/var/log/*`. Add a `logrotate`
config at `/etc/logrotate.d/bbsengine6`:

```
/var/log/uwsgi/handbook*.log
/var/log/handbook-*.log
/var/log/apache2/handbook-*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload uwsgi-handbook.service || true
        systemctl reload handbook-gunicorn.service || true
        systemctl reload apache2 > /dev/null 2>&1 || true
    endscript
}
```

### systemd hardening

Add to the `[Service]` block of any uwsgi/gunicorn unit:

```ini
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/uwsgi /var/log/handbook
```

### `.htaccess` rules

The `www/.htaccess` rewrite rule is the entry point for clean URLs
into `/engine/router.php`:

```apache
RewriteEngine On
RewriteBase /

RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^([a-zA-Z0-9_/-]+)$ /engine/router.php?mode=browse&uri=$1 [last,qsappend]
```

The router's handler chain (blurb → folder → markdown → error) is
documented in [./ROUTER.md](./ROUTER.md). Static-site prefixes
(`/achilles/`, `/empyre/`, `/murdermotel/`) must be processed
**before** this rule — place the rewrite before the router rule.

### Monitoring

| Check | Command |
|---|---|
| Service status | `systemctl status uwsgi-handbook` |
| Recent errors | `journalctl -u uwsgi-handbook -n 50 -f` |
| Apache config valid | `apache2ctl configtest` |
| Proxy modules loaded | `apache2ctl -M \| grep proxy` |
| Listening sockets | `ss -tuln \| grep -E '5000\|8000'` |
| Memory per worker | `top -p $(pgrep -f uwsgi)` |

## Troubleshooting

**`uwsgi` not found.** `pip install uwsgi` into the system Python or
whichever interpreter the systemd unit points at.

**`mod_proxy_uwsgi.so` missing.**

```bash
sudo apt-get install libapache2-mod-proxy-uwsgi
sudo a2enmod proxy_uwsgi
sudo systemctl restart apache2
```

**Port 5000 already in use.** `sudo lsof -i :5000` — adjust `[uwsgi]
socket` and `ProxyPass` together.

**Handbook returns 500.** Tail `journalctl -u uwsgi-handbook -f` and
`/var/log/apache2/handbook-error.log` together. Most common: the
handbook source moved but the `[uwsgi] chdir` path didn't.

**Permission denied on Unix socket.** `sudo chown www-data:www-data
/run/uwsgi-handbook.sock && sudo chmod 666 /run/uwsgi-handbook.sock`.

**Apache config errors.** `sudo apache2ctl configtest` before
`reload`.

## See also

- [./HANDBOOK_SERVING.md](./HANDBOOK_SERVING.md) — runtime conversion
  vs. pre-built static, the Flask app, `convert_markdown.py`, the
  Makefile.
- [./SECURITY.md](./SECURITY.md) — security overview and links to the
  Phase 0-5 hardening audit.
- [./ROUTER.md](./ROUTER.md) — `/engine/router.php` operation.
- [`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md) — the full
  audit; Phase 3 covers the PHP web layer.
