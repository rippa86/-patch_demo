# Bootstrap — lab.rippa.io webstore

Resolved later at deploy time from Ansible facts (this workstation could not
look up webapp01/webapp02). Allocated VIP: **10.10.4.50** for
`shoppingapp.lab.rippa.io`. Quorum host is `second-demo.lab.rippa.io` /
`10.10.4.110`.

## 0. DNS / hosts

Create an A record (or use the deploy playbook `/etc/hosts` lines):

- `shoppingapp.lab.rippa.io` → `10.10.4.50` (must be free on `10.10.4.0/24`)
- Confirm `10.10.4.50` is not already in use: `ping -c1 10.10.4.50`

## 1. Secrets

On all three hosts:

```bash
sudo mkdir -p /etc/webstore
sudo cp deploy/env.example /etc/webstore/webstore.env
sudo chmod 600 /etc/webstore/webstore.env
sudo vi /etc/webstore/webstore.env
```

Use the **same** `JWT_SECRET`, `INTERNAL_TOKEN`, `MARIADB_*`, `LDAP_*`,
`SYNTH_PASSWORD` on webapp01 and webapp02. Keep `DATABASE_URL` password in
sync with `MARIADB_PASSWORD`.

## 2. Ansible deploy (images, quadlets, keepalived, IPs)

From a controller that can SSH to the three hosts, in `ansible/`:

```bash
cp inventory.ini.example inventory.ini
ansible-playbook playbooks/deploy.yml
```

That playbook prints the live `webapp01` / `webapp02` addresses. It does not
invent last octets. It writes `/etc/hosts` for the lab FQDNs.

Apply firewalld from `deploy/firewalld/README.md`.

## 3. 389-ds on each shop host

```bash
sudo dscreate from-file /etc/webstore/instance.inf
sudo cp /opt/webstore/deploy/ldap/*.ldif /tmp/
sudo ldapadd -x -H ldap://localhost -D "cn=Directory Manager" -W -f /opt/webstore/deploy/ldap/suffix.ldif
# If the suffix already exists, skip suffix.ldif and add OUs/users only.
sudo ldapadd -x -H ldap://localhost -D "cn=Directory Manager" -W -f /opt/webstore/deploy/ldap/api-user.ldif
sudo ldapadd -x -H ldap://localhost -D "cn=Directory Manager" -W -f /opt/webstore/deploy/ldap/seed-users.ldif
sudo ldapmodify -x -H ldap://localhost -D "cn=Directory Manager" -W -f /opt/webstore/deploy/ldap/api-aci.ldif
source /etc/webstore/webstore.env
sudo ldappasswd -x -H ldap://localhost -D "cn=Directory Manager" -w "$LDAP_MANAGER_PASSWORD" \
  -s "$LDAP_API_PASSWORD" "uid=api,ou=Services,dc=webstore,dc=local"
```

Then MMR: follow `deploy/ldap/mmr.md` (replica-id 1 on webapp01, 2 on webapp02).

```bash
sudo dsconf webstore config replace nsslapd-listenhost=0.0.0.0
sudo systemctl enable --now dirsrv@webstore
```

## 4. Galera

Bootstrap **webapp01 only** (empty `gcomm://`), then join webapp02 and garbd:

```bash
ansible-playbook playbooks/galera-bootstrap.yml
ansible-playbook playbooks/galera-join.yml
```

Check: `podman exec webstore-mariadb mysql -e "SHOW STATUS LIKE 'wsrep_cluster_size';"`
should report **3** (two data nodes + garbd).

## 5. Start shop services

On **each** shop host:

```bash
sudo systemctl enable --now \
  webstore-backend.service \
  webstore-api-account.service \
  webstore-api-login.service \
  webstore-api-logout.service \
  webstore-api-cart.service \
  webstore-api-stats.service \
  webstore-httpd.service \
  webstore-haproxy.service \
  keepalived.service
```

On **second-demo**:

```bash
sudo systemctl enable --now webstore-httpd-dash.service
# After the shop VIP answers:
sudo systemctl enable --now webstore-synth-users.service
```

## 6. Smoke and drain

```bash
ansible-playbook playbooks/smoke.yml
ansible-playbook playbooks/drain.yml -e target=webapp01.lab.rippa.io
ansible-playbook playbooks/smoke.yml
ansible-playbook playbooks/restore.yml -e target=webapp01.lab.rippa.io
```

## URLs

- Shop: http://shoppingapp.lab.rippa.io/
- Create account: http://shoppingapp.lab.rippa.io/account.html
- Ops graph: http://second-demo.lab.rippa.io/
