# Paperless-ngx - Simple Document Organisation

The greatest software to track your documents and to go... Paperless!

## Installation

Paperless-ngx is a pretty heavy python app. The devs recommend to use docker, but we are not a fan of docker here, so we are going to install it in an LXC bare-metal manually ourselves.

> These instructions are taken from [the official paperless-ngx docs](https://docs.paperless-ngx.com/setup/#bare_metal) and modified for my own setup.

Install dependencies. Paperless requires the following packages.

```shell
apt update
apt install -y \
  redis \
  build-essential \
  imagemagick \
  fonts-liberation \
  optipng \
  libpq-dev \
  libmagic-dev \
  libzbar0t64 \
  poppler-utils \
  default-libmysqlclient-dev \
  automake \
  libtool \
  pkg-config \
  libtiff-dev \
  libpng-dev \
  libleptonica-dev \
  unpaper \
  icc-profiles-free \
  qpdf \
  libleptonica6 \
  libxml2 \
  pngquant \
  zlib1g \
  tesseract-ocr \
  tesseract-ocr-eng \
  ghostscript
```

Then we need to grab the latest release and extract it into a directory of choice.

```shell
cd /opt
wget $(curl -fsSL https://api.github.com/repos/paperless-ngx/paperless-ngx/releases/latest | grep browser_download_url | grep tar.xz | cut -d\" -f4)
tar -xf *.tar.xz
rm *.tar.xz
```

Create our paperless user to run paperless with.

```shell
adduser paperless --system --home /opt/paperless-ngx --group
chown -R paperless:paperless /opt/paperless-ngx/{media,data,consume}
```

We are also going to use `uv` which is the new fast python package manager.

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
cd /opt/paperless-ngx
uv venv
uv sync --all-extras
```

Install the Natural Language Toolkit.

```shell
cd /opt/paperless-ngx
uv run python -m nltk.downloader -d /usr/share/nltk_data snowball_data
uv run python -m nltk.downloader -d /usr/share/nltk_data stopwords
uv run python -m nltk.downloader -d /usr/share/nltk_data punkt_tab || \
uv run python -m nltk.downloader -d /usr/share/nltk_data punkt
for policy_file in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml; do
  if [[ -f "$policy_file" ]]; then
    sed -i -e 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' "$policy_file"
  fi
done
```

Create all the systemd services.

```shell
cat <<EOF >/etc/systemd/system/paperless-scheduler.service
[Unit]
Description=Paperless Celery beat
Requires=redis.service

[Service]
WorkingDirectory=/opt/paperless-ngx/src
ExecStart=uv run -- celery --app paperless beat --loglevel INFO

[Install]
WantedBy=multi-user.target
EOF

cat <<EOF >/etc/systemd/system/paperless-task-queue.service
[Unit]
Description=Paperless Celery Workers
Requires=redis.service
After=postgresql.service

[Service]
WorkingDirectory=/opt/paperless-ngx/src
ExecStart=uv run -- celery --app paperless worker --loglevel INFO

[Install]
WantedBy=multi-user.target
EOF

cat <<EOF >/etc/systemd/system/paperless-consumer.service
[Unit]
Description=Paperless consumer
Requires=redis.service

[Service]
WorkingDirectory=/opt/paperless-ngx/src
ExecStartPre=/bin/sleep 2
ExecStart=uv run -- python manage.py document_consumer

[Install]
WantedBy=multi-user.target
EOF

cat <<EOF >/etc/systemd/system/paperless-webserver.service
[Unit]
Description=Paperless webserver
After=network.target
Wants=network.target
Requires=redis.service

[Service]
WorkingDirectory=/opt/paperless-ngx/src
ExecStart=uv run -- granian --interface asginl --ws "paperless.asgi:application"
Environment=GRANIAN_HOST=::
Environment=GRANIAN_PORT=8000
Environment=GRANIAN_WORKERS=1

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
```

We aren't going to start the services yet as we still need to do some configuration.

## Configuration

The paperless configuration file lives in `/opt/paperless-ngx/paperless.conf` which we can change. Here is my current config.

```conf
PAPERLESS_TIME_ZONE=UTC
PAPERLESS_DISABLE_REGULAR_LOGIN=true
PAPERLESS_REDIRECT_LOGIN_TO_SSO=true
PAPERLESS_APPS="allauth.socialaccount.providers.openid_connect"
PAPERLESS_SOCIALACCOUNT_PROVIDERS='{"openid_connect":{"SCOPE":["openid","profile","email"],"OAUTH_PKCE_ENABLED":true,"APPS":[{"provider_id":"secret","name":"secret","client_id":"secret","secret":"secret","settings":{"server_url":"https://auth.mydomain.com/.well-known/openid-configuration"}}]}}'

PAPERLESS_REDIS=redis+socket:///run/redis/redis-server.sock
PAPERLESS_DBHOST=postgresql-lxc.localdomain
PAPERLESS_DBPORT=5432
PAPERLESS_DBNAME=secret
PAPERLESS_DBUSER=secret
PAPERLESS_DBPASS=secret

PAPERLESS_CONSUMPTION_DIR=/opt/paperless/consume
PAPERLESS_DATA_DIR=/opt/paperless/data
PAPERLESS_MEDIA_ROOT=/opt/paperless/media
PAPERLESS_STATICDIR=/opt/paperless/static

PAPERLESS_SECRET_KEY=secret
PAPERLESS_URL=https://paperless.mydomain.com
```

Then just make sure your postgresql database is setup and ready to accept connections from paperless, then we can start all the services.

```shell
systemctl enable --now paperless-webserver paperless-scheduler paperless-task-queue paperless-consumer
```

You might need to follow some extra documentation to setup an admin user from the CLI.
