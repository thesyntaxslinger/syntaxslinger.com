# Gitea - The self-hosted GitHub

I use Gitea for all my code repositories. I love it because I can have personal repos that aren't hosted on someone else's computer.

Furthermore, I also mirror some of my repositories to GitHub for public viewing as well.

## Installation

The installation for Gitea is quick, and easy. Since Gitea is just a single binary written in Go as well, we can just download it and run it straight away.

```shell
mkdir /opt/gitea
cd /opt/gitea
wget $(curl -s https://api.github.com/repos/go-gitea/gitea/releases/latest \
    | grep browser_download_url | grep -E 'linux-amd64.xz"$' | cut -d\" -f4)
xz -d gitea-*.xz
mv gitea-* gitea
chmod +x /opt/gitea/gitea
```

We should make a Gitea user as well so that we can use SSH for repos later.

```shell
sudo adduser --system --home /etc/gitea --shell /usr/bin/bash gitea
```

### systemd

Now we just need to make a systemd service to actually run Gitea.

```systemd
[Unit]
Description=Gitea (Git with a cup of tea)
After=syslog.target
After=network.target

[Service]
# Uncomment the next line if you have repos with lots of files and get a HTTP 500 error because of that
# LimitNOFILE=524288:524288
RestartSec=2s
Type=notify
User=gitea
Group=gitea
#The mount point we added to the container
WorkingDirectory=/var/lib/gitea
#Create directory in /run
RuntimeDirectory=gitea
ExecStart=/opt/gitea/gitea web --config /etc/gitea/app.ini
Restart=always
Environment=USER=gitea HOME=/var/lib/gitea/data GITEA_WORK_DIR=/var/lib/gitea
WatchdogSec=30s
#Capabilities to bind to low-numbered ports
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

## Configuration

Configuring Gitea is just a single file `/etc/gitea/app.ini`.

This obviously changes for everyone, but here is my config at the moment.

```ini
APP_NAME = Gitea
RUN_USER = gitea
WORK_PATH = /var/lib/gitea
RUN_MODE = prod

[database]
DB_TYPE = postgres
HOST = postgresql-lxc.localdomain:5432
NAME = gitea
USER = gitea
PASSWD = secret
SSL_MODE = disable
LOG_SQL = false

[repository]
ROOT = /var/lib/gitea/data/gitea-repositories

[server]
SSH_DOMAIN = gitea-lxc.localdomain
DOMAIN = gitea.mydomain.com
HTTP_PORT = 3000
ROOT_URL = https://gitea.mydomain.com/
APP_DATA_PATH = /var/lib/gitea/data
DISABLE_SSH = false
SSH_PORT = 22
LFS_START_SERVER = true
LFS_JWT_SECRET = secret 
OFFLINE_MODE = true

[lfs]
PATH = /var/lib/gitea/data/lfs

[mailer]
ENABLED = false

[service]
REGISTER_EMAIL_CONFIRM = false
ENABLE_NOTIFY_MAIL = false
DISABLE_REGISTRATION = true
ALLOW_ONLY_EXTERNAL_REGISTRATION = false
ENABLE_CAPTCHA = false
REQUIRE_SIGNIN_VIEW = true
DEFAULT_KEEP_EMAIL_PRIVATE = false
DEFAULT_ALLOW_CREATE_ORGANIZATION = false
DEFAULT_ENABLE_TIMETRACKING = true
NO_REPLY_ADDRESS = noreply.localhost
ENABLE_PASSWORD_SIGNIN_FORM = false
ENABLE_BASIC_AUTHENTICATION = false

[openid]
ENABLE_OPENID_SIGNIN = false
ENABLE_OPENID_SIGNUP = false

[cron.update_checker]
ENABLED = false

[session]
PROVIDER = file

[log]
MODE = console
LEVEL = info
ROOT_PATH = /var/lib/gitea/log

[repository.pull-request]
DEFAULT_MERGE_STYLE = merge

[repository.signing]
DEFAULT_TRUST_MODEL = committer

[security]
INSTALL_LOCK = true
INTERNAL_TOKEN = secret
PASSWORD_HASH_ALGO = argon2
LOGIN_REMEMBER_DAYS = 30

[oauth2]
JWT_SECRET = secret
```

You will need a Postgres database for this setup, or you can use `sqlite3`.

Now we can start Gitea!

```shell
systemctl enable --now gitea
```
