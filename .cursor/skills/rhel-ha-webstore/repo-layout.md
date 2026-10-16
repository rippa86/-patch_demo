# Target repository layout

```
frontend/                      # shop httpd
  index.html                   # cart + 3 products
  account.html                 # create account
  css/app.css
  js/api.js                    # calls four public APIs
  js/app.js
  healthz.txt
dashboard/                     # ops VM httpd
  index.html                   # logged-in count + graph
  js/dashboard.js
  healthz.txt
synth-users/                   # ops VM load generator
  Containerfile
  requirements.txt
  synth.py                     # 100 users, independent 15–45s login/out
api-account/
  Containerfile
  requirements.txt
  app/main.py
api-login/
  Containerfile
  requirements.txt
  app/main.py
api-logout/
  Containerfile
  requirements.txt
  app/main.py
api-cart/
  Containerfile
  requirements.txt
  app/main.py
api-stats/
  Containerfile
  requirements.txt
  app/main.py
backend/
  Containerfile
  requirements.txt
  app/main.py
  app/db.py
  app/models.py
  app/routes.py
ansible/
  ansible.cfg
  inventory.ini.example
  playbooks/drain.yml
  playbooks/restore.yml
  playbooks/smoke.yml
  roles/…                      # haproxy drain/wait, systemd/podman, galera desync
deploy/
  quadlets/
  haproxy/haproxy.cfg
  keepalived/
  galera/
  ldap/
  firewalld/
  env.example
docs/HLD.md
```

No `deploy/scripts/webstore-drain.sh`. Smoke is `ansible/playbooks/smoke.yml`.

## Quadlet unit names

`webstore-net.network`, `webstore-haproxy.container`, `webstore-httpd.container`, `webstore-api-account.container`, `webstore-api-login.container`, `webstore-api-logout.container`, `webstore-api-cart.container`, `webstore-api-stats.container`, `webstore-backend.container`, `webstore-mariadb.container`.

Ops VM: `webstore-httpd-dash.container`, `webstore-garbd.container`, `webstore-synth-users.container`.

Env for synth: `STORE_BASE_URL` (VIP), `SYNTH_COUNT=100`, `SYNTH_MIN_SEC=15`, `SYNTH_MAX_SEC=45`, shared lab password.

## Interface freeze

Account: `POST /api/account` `{ "username", "password", "email" }` → `{ "username" }`

Login: `POST /api/login` `{ "username", "password" }` → `{ "token" }`

Logout: `POST /api/logout` header `Authorization: Bearer` → `{ "ok": true }`

Cart:

- `GET /api/cart/products` → three products
- `GET /api/cart` `PUT /api/cart` `{ "items": [{ "product_id", "qty" }] }`
- `POST /api/cart/checkout` → `{ "order_id" }`

Stats (ops only): `GET /api/stats/logged-in` → `{ "count": n, "series": [{ "t", "n" }] }`

Backend internal (not on VIP): `/healthz`, `/internal/sessions`, `/internal/cart`, `/internal/products`, `/internal/orders`.

Every API container also serves `GET /healthz`.

## Images

UBI 10 httpd / Python 3.12; MariaDB with Galera; HAProxy on UBI or official image. Pin tags, never `:latest`.
