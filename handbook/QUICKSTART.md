# Quick Start

> Status: canonical. Updated 2026-09-04.
> Audience: operators standing up bbsengine6 for the first time.

## Goal

Stand up bbsengine6 from a clean checkout in roughly five minutes: install
OS and Python deps, build the wheel, bring up the database, run the BBS
door, and confirm the public website renders. For production
deployment, jump to [./DEPLOYMENT.md](./DEPLOYMENT.md).

## 1. OS packages (Debian / Ubuntu)

```bash
sudo apt-get install \
 postgresql postgresql-contrib libpq-dev \
    python3 python3-venv python3-dev build-essential \
    php8.1 php8.1-cli php8.1-pgsql libapache2-mod-php \
    apache2 libapache2-mod-wsgi-py3 libapache2-mod-proxy-uwsgi \
    libapache2-mod-rewrite
```

PHP extensions `pdo` and `pgsql` are pulled in by `php8.1-pgsql`.
Smarty and HTML_QuickForm2 come from PEAR:

```bash
sudo pear install html_quickform2 Smarty Log
```

## 2. Python package

Install into Python 3.10 (mediapipe does not support 3.13+):

```bash
cd bbsengine6/py/src
python3.10 -m build
python3.10 -m pip install dist/bbsengine6-*.whl --force-reinstall
```

Editable install for development:

```bash
cd bbsengine6/py
python3 -m pip install -e .
```

## 3. PHP deps (Composer)

```bash
cd bbsengine6
composer install
```

This pulls `erusev/parsedown-extra` (declared in `composer.json`) into
`vendor/`.

## 4. Bring up the database

`python -m bbsengine6.startup` is the idempotent bootstrap. It runs the
`backend.check*` routines (role provisioning, schema ownership, schema
import), then opens the interactive console menu.

```bash
python -m bbsengine6.startup
```

For a non-interactive bring-up, use the `stage_one` routine directly
(see `py/src/bbsengine6/backend/`).

The startup wizard expects PostgreSQL to be reachable as the current
user (typically via `ident` or `peer` auth on the local socket). The
dedicated `zoid6` role is created by `backend.checkzoid6role` and the
five `SECURITY DEFINER` helpers are reassigned to it by
`backend.checkzoid6owner` — both idempotent.

## 5. Run the BBS door

The `bed` console script is the TUI client:

```bash
bed
```

For browser/CLI clients, run the WebSocket daemon. The router is loaded
from `zoid6.api.handler.MessageRouter`:

```bash
bed --router zoid6.api.handler.MessageRouter \
    --config /etc/zoid6/bed.json
```

`bed` is the thin shim in `py/src/bbsengine6/bed.py`; the daemon
lifecycle (auth, services, signal handling) lives in the bed package
above this repo. The daemon opens a TCP/WS port that the
`net/transport.py` WebSocket clients connect to.

## 6. Serve the public website

Add the Apache site config (see [./DEPLOYMENT.md](./DEPLOYMENT.md) for
the full production deployment, including WSGI/uWSGI):

```bash
sudo cp handbook/handbook-wsgi.conf /etc/apache2/sites-available/
sudo a2ensite handbook-wsgi.conf
sudo systemctl restart apache2
```

Then visit `http://localhost/handbook/` for the docs and
`http://localhost/engine/` for the public site.

## 7. Verify

| Check | Command |
|---|---|
| Package installed | `python -c "import bbsengine6; print(bbsengine6.__file__)"` |
| Database reachable | `python -m bbsengine6.startup` (re-run is safe) |
| `bed` on PATH | `which bed` |
| Apache config valid | `sudo apache2ctl configtest` |
| Handbook renders | `curl -fsSL http://localhost/handbook/ \| head` |
| Composer install clean | `composer validate --no-check-publish` |

## Next steps

- **Production deployment** — [./DEPLOYMENT.md](./DEPLOYMENT.md)
  covers Apache mod_proxy_uwsgi, mod_wsgi, and gunicorn+mod_proxy,
  systemd units, log rotation, and the production checklist.
- **Handbook serving model** — [./HANDBOOK_SERVING.md](./HANDBOOK_SERVING.md)
  covers runtime conversion vs. pre-built static HTML and the Flask
  app.
- **Security model** — [./SECURITY.md](./SECURITY.md) summarises the
  Phase 0-5 hardening and links to `../ROBUSTNESS_REVIEW.md`.
- **Router operation** — [./ROUTER.md](./ROUTER.md) documents the
  `/engine/router.php` entry point and its handler chain.
- **Build / install notes** — the `python -m build` +
  `pip install --force-reinstall` sequence and the Python 3.10
  constraint are captured in the `CHANGELOG.md` build-system entries.
