# Miniflux

Miniflux is a great RSS reader as it is quite minimal, easy to use, super simple setup.

## Installation

Installation is simple. Miniflux provides a repository for Debian releases.

Here is a basic template for `/etc/apt/sources.list.d/miniflux.list`:

```shell
echo "deb [trusted=yes] https://repo.miniflux.app/apt/ * *" | sudo tee /etc/apt/sources.list.d/miniflux.list > /dev/null
apt update
apt install miniflux
```

## Configuration

We will be using Postgres as our database backend as this is the only database type Miniflux supports.

Make our config at `/etc/miniflux.conf`.

```conf
RUN_MIGRATIONS=1
DATABASE_URL=postgres://secret:secret@postgresql-lxc.localdomain:5432/secret?sslmode=disable
CREATE_ADMIN=1
ADMIN_USERNAME=username
ADMIN_PASSWORD=secret
OAUTH2_OIDC_DISCOVERY_ENDPOINT=https://auth.mydomain.com
OAUTH2_CLIENT_ID=miniflux
OAUTH2_CLIENT_SECRET=secret
OAUTH2_OIDC_PROVIDER_NAME=Authelia
OAUTH2_PROVIDER=oidc
OAUTH2_REDIRECT_URL=https://miniflux.mydomain.com/oauth2/oidc/callback
OAUTH2_USER_CREATION=1
LISTEN_ADDR=[::]:8080
```

### systemd

We need a systemd file to run Miniflux which the `.deb` package should have provided. If not, here is mine:

```systemd
[Unit]
Description=Miniflux
Documentation=man:miniflux(1) https://miniflux.app/docs/index.html
After=network.target postgresql.service

[Service]
ExecStart=/usr/bin/miniflux
User=miniflux
EnvironmentFile=/etc/miniflux.conf
Type=notify
WatchdogSec=60s
WatchdogSignal=SIGKILL
Restart=always
RestartSec=5
RuntimeDirectory=miniflux
AmbientCapabilities=CAP_NET_BIND_SERVICE
ProtectSystem=strict
PrivateTmp=yes
NoNewPrivileges=yes
RestrictNamespaces=yes
ProtectHome=yes
PrivateDevices=yes
ProtectControlGroups=yes
ProtectKernelModules=yes
ProtectKernelTunables=yes
ProtectHostname=yes
RestrictRealtime=yes
ProtectKernelLogs=yes
ProtectClock=yes
SystemCallArchitectures=native
LockPersonality=yes
MemoryDenyWriteExecute=yes

[Install]
WantedBy=multi-user.target
```
