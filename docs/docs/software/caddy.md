# Caddy - The easiest reverse proxy

I switched to Caddy from NGINX and haven't looked back. The setup for Caddy is super easy and to maintain it is just a single file. Not to mention that the blob itself is just a single go binary.

## Installation 

I will still install it via a package manager though, as it makes it even easier to maintain.

```shell
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list
chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
chmod o+r /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install caddy
systemctl --enable now caddy
```

## Configuration

The configuration is super easy. Since I am in a homelab environment, there are some challenges:

- Let's Encrypt certificates do not work unless you use some sort of DNS challenge
- Caddy has a sort of bad implementation of DNS challenges depending on your provider.

I am going to get around this by using `certbot` as I find it super simple to set up TLS certificates and have them auto update and not have to rely on Caddy being funky.

### Certbot

My DNS provider is Cloudflare, so I am going to use the python plugin for Cloudflare.

```shell
apt install certbot python3-certbot-dns-cloudflare
```

We can then make a file in /etc/letsencrypt/cloudflare.ini which will contain our Cloudflare API token.

> You can use an email and global API key, but that is a lot more permissive than a DNS only API token.

```shell
touch /etc/letsencrypt/cloudflare.ini
chmod 600 /etc/letsencrypt/cloudflare.ini
echo "dns_cloudflare_api_token = TOKEN" >> /etc/letsencrypt/cloudflare.ini
```

Make sure to replace the TOKEN with your actual API token.

Now we can grab the cert.

```shell
certbot certonly --dns-cloudflare \
    --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
    -d mydomain.com -d '*.mydomain.com'
```

#### Linking Certbot to Caddy

Caddy can't actually use Certbot certificates yet as the private key will not be owned by the caddy user.

We can fix this with a simple hook in Certbot to automatically deploy new certificates once they come down.

First we need to set up the certs folder.

```shell
mkdir /etc/caddy/certs
chown 0700 /etc/caddy/certs
```

Now we can place this script into `/etc/letsencrypt/renewal-hooks/deploy`.

```bash
#!/bin/bash

rsync -av --no-owner --no-group "$(readlink -f /etc/letsencrypt/live/mydomain.com/fullchain.pem)" /etc/caddy/certs/fullchain.pem
rsync -av --no-owner --no-group "$(readlink -f /etc/letsencrypt/live/mydomain.com/privkey.pem)" /etc/caddy/certs/privkey.pem

chown -R caddy:caddy /etc/caddy/certs

systemctl reload caddy
```

Make the script executable and then run it once so we can populate the certs folder.

```shell
chmod +x /etc/letsencrypt/renewal-hooks/deploy/certbot-caddy.sh
bash /etc/letsencrypt/renewal-hooks/deploy/certbot-caddy.sh
```

## Caddyfile

Now we have our certs setup and ready to go, we can make our Caddyfile.

You can start off with something like this.

```caddyfile
{
	log {
		output file /var/log/caddy/access.log {
			roll_size 100mb
			roll_keep 10
			roll_keep_for 720h
		}
		format json
		level ERROR
	}
}

*.mydomain.com {
	tls /etc/caddy/certs/fullchain.pem /etc/caddy/certs/privkey.pem

	encode gzip

	@authelia host auth.mydomain.com
	handle @authelia {
		reverse_proxy {env.AUTHELIA_HOST}
	}

	@miniflux host miniflux.mydomain.com
	handle @miniflux {
		forward_auth {env.AUTHELIA_HOST} {
			uri /api/authz/forward-auth
			copy_headers Remote-User Remote-Groups Remote-Email Remote-Name
		}
		reverse_proxy miniflux-lxc.localdomain:8080 {
			header_up Cookie "authelia_session=[^;]+" "authelia_session=_"
		}
	}
}
```

You can add or remove as many subdomains as you like to this and have all your services. This seems to be the best setup for myself though.
