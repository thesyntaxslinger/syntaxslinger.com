# Nextcloud - Self-Hosted Google Cloud

I love Nextcloud. It has completely moved me away from Google's ecosystem.

## Installation

The Nextcloud installation is a bit of a pain. You are dealing with a whole LAMP stack. You could use docker and just use the prebuilt image from the Nextcloud devs, but I hate docker!

We need a lot of dependencies for Nextcloud. We are also going to be using NGINX over the standard Apache configuration, due to NGINX just being better.

```shell
apt update
apt install php nginx php-fpm
```

You will also have to install a bunch of other `php-*` packages that are different for every setup.

Next grab the latest Nextcloud release and put it into `/var/www/nextcloud` as this will be our home directory.

```shell
mkdir -p /var/www/nextcloud
cd /var/www/nextcloud
wget https://download.nextcloud.com/server/releases/latest.zip
unzip latest.zip
rm -r latest.zip
```

Next we need to set up NGINX so that our server is available. We aren't going to use TLS for this setup since we will be using [Caddy](/homelab/software/caddy) to reverse proxy it later.

You can find more documentation on NGINX at the [Nextcloud docs](https://docs.nextcloud.com/server/stable/admin_manual/installation/nginx.html).

### NGINX

```nginx
# Version 2025-07-23

upstream php-handler {
    #server 127.0.0.1:9000;
    server unix:/run/php/php8.4-fpm.sock;
}

# Set the `immutable` cache control options only for assets with a cache busting `v` argument
map $arg_v $asset_immutable {
    "" "";
    default ", immutable";
}

server {
    #listen 80 http2;
    #listen [::]:80 http2;
    # With NGinx >= 1.25.1 you should use this instead:
    listen 80;
    listen [::]:80;
    http2 on;
    server_name nextcloud-lxc.localdomain;

    # Path to the root of your installation
    root /var/www/nextcloud;

    # https://mozilla.github.io/server-side-tls/ssl-config-generator/
    #ssl_certificate     /etc/ssl/certs/ssl-cert-snakeoil.pem;
    #ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

    # Prevent nginx HTTP Server Detection
    server_tokens off;

    # HSTS settings
    # WARNING: Only add the preload option once you read about
    # the consequences in https://hstspreload.org/. This option
    # will add the domain to a hardcoded list that is shipped
    # in all major browsers and getting removed from this list
    # could take several months.
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # set max upload size and increase upload timeout:
    client_max_body_size 512M;
    client_body_timeout 300s;
    fastcgi_buffers 64 4K;

    # Proxy and client response timeouts
    # Uncomment an increase these if facing timeout errors during large file uploads
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    send_timeout 60s;

    # Enable gzip but do not remove ETag headers
    gzip on;
    gzip_vary on;
    gzip_comp_level 4;
    gzip_min_length 256;
    gzip_proxied expired no-cache no-store private no_last_modified no_etag auth;
    gzip_types application/atom+xml text/javascript application/javascript application/json application/ld+json application/manifest+json application/rss+xml application/vnd.geo+json application/vnd.ms-fontobject application/wasm application/x-font-ttf application/x-web-app-manifest+json application/xhtml+xml application/xml font/opentype image/bmp image/svg+xml image/x-icon text/cache-manifest text/css text/plain text/vcard text/vnd.rim.location.xloc text/vtt text/x-component text/x-cross-domain-policy;

    # Pagespeed is not supported by Nextcloud, so if your server is built
    # with the `ngx_pagespeed` module, uncomment this line to disable it.
    #pagespeed off;

    # The settings allows you to optimize the HTTP2 bandwidth.
    # See https://blog.cloudflare.com/delivering-http-2-upload-speed-improvements/
    # for tuning hints
    client_body_buffer_size 512k;

    # HTTP response headers borrowed from Nextcloud `.htaccess`
    add_header Referrer-Policy                   "no-referrer"       always;
    add_header X-Content-Type-Options            "nosniff"           always;
    add_header X-Frame-Options                   "SAMEORIGIN"        always;
    add_header X-Permitted-Cross-Domain-Policies "none"              always;
    add_header X-Robots-Tag                      "noindex, nofollow" always;
    add_header X-XSS-Protection                  "1; mode=block"     always;

    # Remove X-Powered-By, which is an information leak
    fastcgi_hide_header X-Powered-By;

    # Set .mjs and .wasm MIME types
    # Either include it in the default mime.types list
    # and include that list explicitly or add the file extension
    # only for Nextcloud like below:
    include mime.types;
    types {
        text/javascript mjs;
	application/wasm wasm;
    }

    # Specify how to handle directories -- specifying `/index.php$request_uri`
    # here as the fallback means that Nginx always exhibits the desired behaviour
    # when a client requests a path that corresponds to a directory that exists
    # on the server. In particular, if that directory contains an index.php file,
    # that file is correctly served; if it doesn't, then the request is passed to
    # the front-end controller. This consistent behaviour means that we don't need
    # to specify custom rules for certain paths (e.g. images and other assets,
    # `/updater`, `/ocs-provider`), and thus
    # `try_files $uri $uri/ /index.php$request_uri`
    # always provides the desired behaviour.
    index index.php index.html /index.php$request_uri;

    # Rule borrowed from `.htaccess` to handle Microsoft DAV clients
    location = / {
        if ( $http_user_agent ~ ^DavClnt ) {
            return 302 /remote.php/webdav/$is_args$args;
        }
    }

    location = /robots.txt {
        allow all;
        log_not_found off;
        access_log off;
    }

    # Make a regex exception for `/.well-known` so that clients can still
    # access it despite the existence of the regex rule
    # `location ~ /(\.|autotest|...)` which would otherwise handle requests
    # for `/.well-known`.
    location ^~ /.well-known {
        # The rules in this block are an adaptation of the rules
        # in `.htaccess` that concern `/.well-known`.

        location = /.well-known/carddav { return 301 /remote.php/dav/; }
        location = /.well-known/caldav  { return 301 /remote.php/dav/; }

        location /.well-known/acme-challenge    { try_files $uri $uri/ =404; }
        location /.well-known/pki-validation    { try_files $uri $uri/ =404; }

        # Let Nextcloud's API for `/.well-known` URIs handle all other
        # requests by passing them to the front-end controller.
        return 301 /index.php$request_uri;
    }

    # Rules borrowed from `.htaccess` to hide certain paths from clients
    location ~ ^/(?:build|tests|config|lib|3rdparty|templates|data)(?:$|/)  { return 404; }
    location ~ ^/(?:\.|autotest|occ|issue|indie|db_|console)                { return 404; }

    # Ensure this block, which passes PHP files to the PHP process, is above the blocks
    # which handle static assets (as seen below). If this block is not declared first,
    # then Nginx will encounter an infinite rewriting loop when it prepends `/index.php`
    # to the URI, resulting in a HTTP 500 error response.
    location ~ \.php(?:$|/) {
        # Required for legacy support
        rewrite ^/(?!index|remote|public|cron|core\/ajax\/update|status|ocs\/v[12]|updater\/.+|ocs-provider\/.+|.+\/richdocumentscode(_arm64)?\/proxy) /index.php$request_uri;

        fastcgi_split_path_info ^(.+?\.php)(/.*)$;
        set $path_info $fastcgi_path_info;

        try_files $fastcgi_script_name =404;

        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $path_info;
        fastcgi_param HTTPS on;

        fastcgi_param modHeadersAvailable true;         # Avoid sending the security headers twice
        fastcgi_param front_controller_active true;     # Enable pretty urls
        fastcgi_pass php-handler;

        fastcgi_intercept_errors on;
        fastcgi_request_buffering on;                   # Required as PHP-FPM does not support chunked transfer encoding and requires a valid ContentLength header.

        # PHP-FPM 504 response timeouts
        # Uncomment and increase these if facing timeout errors during large file uploads
        #fastcgi_read_timeout 60s;
        #fastcgi_send_timeout 60s;
        #fastcgi_connect_timeout 60s;

        fastcgi_max_temp_file_size 0;
    }

    # Serve static files
    location ~ \.(?:css|js|mjs|svg|gif|ico|jpg|png|webp|wasm|tflite|map|ogg|flac)$ {
        try_files $uri /index.php$request_uri;
        # HTTP response headers borrowed from Nextcloud `.htaccess`
        add_header Cache-Control                     "public, max-age=15778463$asset_immutable";
        add_header Referrer-Policy                   "no-referrer"       always;
        add_header X-Content-Type-Options            "nosniff"           always;
        add_header X-Frame-Options                   "SAMEORIGIN"        always;
        add_header X-Permitted-Cross-Domain-Policies "none"              always;
        add_header X-Robots-Tag                      "noindex, nofollow" always;
        access_log off;     # Optional: Don't log access to assets
    }

    location ~ \.(otf|woff2?)$ {
        try_files $uri /index.php$request_uri;
        expires 7d;         # Cache-Control policy borrowed from `.htaccess`
        access_log off;     # Optional: Don't log access to assets
    }

    # Rule borrowed from `.htaccess`
    location /remote {
        return 301 /remote.php$request_uri;
    }

    location / {
        try_files $uri $uri/ /index.php$request_uri;
    }
}
```

We are using the `http2 on;` as we are going to be using h2c with [Caddy](/homelab/software/caddy) for the reverse proxy.


## Configuration

The configuration for Nextcloud is relatively simple once you install all the dependencies.

We need to edit the config file in `/var/www/nextcloud/config/config.php`. My one is pretty mature, but I will leave it here for documentation purposes.

```php
<?php
$CONFIG = array (
  'instanceid' => 'secret',
  'passwordsalt' => 'secret',
  'secret' => 'secret',
  'trusted_domains' => 
  array (
    0 => 'nextcloud.mydomain.com',
  ),
  'trusted_proxies' => 
  array (
    0 => 'caddy-lxc.localdomain',
  ),
  'datadirectory' => '/var/www/nextcloud/data',
  'dbtype' => 'pgsql',
  'version' => 'version',
  'overwrite.cli.url' => 'https://nextcloud.mydomain.com',
  'overwriteprotocol' => 'https',
  'htaccess.RewriteBase' => '/',
  'dbname' => 'db',
  'dbhost' => 'postgresql-lxc.localdomain',
  'dbport' => '',
  'dbtableprefix' => 'oc_',
  'mysql.utf8mb4' => true,
  'dbuser' => 'user',
  'dbpassword' => 'password',
  'installed' => true,
  'maintenance' => false,
  'maintenance_window_start' => 1,
  'memcache.local' => '\\OC\\Memcache\\Redis',
  'memcache.distributed' => '\\OC\\Memcache\\Redis',
  'memcache.locking' => '\\OC\\Memcache\\Redis',
  'redis' => 
  array (
    'host' => '/run/redis/redis-server.sock',
    'port' => 0,
    'timeout' => 0.0,
  ),
  'oidc_login_provider_url' => 'https://auth.mydomain.com',
  'oidc_login_client_id' => 'nextcloud',
  'oidc_login_client_secret' => 'secret',
  'oidc_login_auto_redirect' => true,
  'oidc_login_end_session_redirect' => false,
  'oidc_login_button_text' => 'Log in with Authelia',
  'oidc_login_hide_password_form' => false,
  'oidc_login_use_id_token' => false,
  'oidc_login_attributes' => 
  array (
    'id' => 'preferred_username',
    'name' => 'name',
    'mail' => 'email',
  ),
  'oidc_login_default_group' => 'oidc',
  'oidc_login_use_external_storage' => false,
  'oidc_login_scope' => 'openid profile email',
  'oidc_login_proxy_ldap' => false,
  'oidc_login_disable_registration' => true,
  'oidc_login_redir_fallback' => false,
  'oidc_login_tls_verify' => true,
  'oidc_create_groups' => false,
  'oidc_login_webdav_enabled' => false,
  'oidc_login_password_authentication' => false,
  'oidc_login_public_key_caching_time' => 86400,
  'oidc_login_min_time_between_jwks_requests' => 10,
  'oidc_login_well_known_caching_time' => 86400,
  'oidc_login_update_avatar' => false,
  'oidc_login_code_challenge_method' => 'S256',
  'memories.db.triggers.fcu' => true,
  'memories.exiftool' => '/var/www/nextcloud/apps/memories/bin-ext/exiftool-amd64-glibc',
  'memories.vod.path' => '/var/www/nextcloud/apps/memories/bin-ext/go-vod-amd64',
  'enabledPreviewProviders' => 
  array (
    0 => 'OC\\Preview\\Image',
    1 => 'OC\\Preview\\HEIC',
    2 => 'OC\\Preview\\TIFF',
    3 => 'OC\\Preview\\Movie',
  ),
  'preview_max_x' => 1024,
  'preview_max_y' => 1024,
  'memories.vod.disable' => false,
  'memories.vod.ffmpeg' => '/usr/bin/ffmpeg',
  'memories.vod.ffprobe' => '/usr/bin/ffprobe',
  'memories.vod.vaapi' => true,
  'memories.vod.use_transpose' => true,
  'memories.index.mode' => '1',
  'mail_smtpmode' => 'smtp',
  'mail_smtpsecure' => 'ssl',
  'mail_sendmailmode' => 'smtp',
  'mail_from_address' => 'internal',
  'mail_domain' => 'mydomain.com',
  'mail_smtphost' => 'mail.mydomain.com',
  'mail_smtpport' => '25',
  'mail_smtpauth' => true,
  'mail_smtpname' => 'internal@mydomain.com',
  'mail_smtppassword' => 'password',
  'default_phone_region' => 'AU',
  'filelocking.enabled' => true,
  'loglevel' => 3,
  'theme' => '',
  'defaultapp' => 'notes',
);
```

### Redis

I am using redis for my setup. Set it up with:

```shell
apt update
apt install redis -y
systemctl enable --now redis
```

You can use either a Linux socket or TCP.
