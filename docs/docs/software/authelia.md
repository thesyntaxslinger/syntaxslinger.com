# Authelia - Easy SSO

Authelia is a simple way to get 2-factor authentication on all your homelab services.

I have Authelia in front of almost all HTTPS endpoints in my homelab via Caddy forward auth.

This means that all requests that are sent through also send a request through to Caddy.

## Setup

I set up Authelia in a Debian 13 LXC container.

Pretty simple setup, you can just follow the docs on Authelia's website [here](https://www.authelia.com/integration/deployment/bare-metal/#debian).

### Add the APT Repository

Add the required packages and download the repository key:

```shell
sudo apt install ca-certificates curl gnupg
sudo curl -fsSL https://www.authelia.com/keys/authelia-security.gpg -o /usr/share/keyrings/authelia-security.gpg
```

Verify the downloaded key:

```shell
gpg --no-default-keyring --keyring /usr/share/keyrings/authelia-security.gpg --list-keys --with-subkey-fingerprint
```

Example output showing the correct Key IDs:

```text
/usr/share/keyrings/authelia-security.gpg
-----------------------------------------
pub   rsa4096 2025-06-27 [SC]
      192085915BD608A458AC58DCE461FA1531286EEA
uid           [ unknown] Authelia Security <security@authelia.com>
uid           [ unknown] Authelia Security <team@authelia.com>
sub   rsa2048 2025-06-27 [E] [expires: 2033-06-25]
      7DBA42FED0069D5828A44079975E8FFC6876AFBB
sub   rsa2048 2025-06-27 [SA] [expires: 2033-06-25]
      C387CC1B5FFC25E55F75F3E6A228F3BD04CC9652
```

Add the repository to `sources.list.d`:

```shell
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/authelia-security.gpg] https://apt.authelia.com stable main" | \
  sudo tee /etc/apt/sources.list.d/authelia.list > /dev/null
```

Update the cache and install:

```shell
sudo apt update && sudo apt install authelia
```

### Configuration

The config for Authelia will depend on your setup. You can get really technical with it.

I run my Authelia with a Postgres Database, Redis, YAML users database.

I could probably upgrade the user's database to something else, but it's just me! If I was in a more enterprise environment, this would 100% be LDAP.

```yaml
---
###############################################################
#                   Authelia configuration                    #
###############################################################

theme: dark

server:
  endpoints:
    authz:
      forward-auth:
        implementation: 'ForwardAuth'

log:
  level: 'debug'


identity_validation:
  reset_password:
    jwt_secret: 'secret'

authentication_backend:
  file:
    path: '/etc/authelia/users_database.yml'
    watch: false
    search:
      email: false
      case_insensitive: false
    password:
      algorithm: 'bcrypt'
      bcrypt:
        variant: 'standard'
        cost: 12

access_control:
  default_policy: 'deny'
  rules:
    # Rules applied to everyone
    - domain: '*.mydomain.com'
      policy: 'two_factor'
    - domain: 'mydomain.com'
      policy: 'two_factor'

totp:
  disable: false
  issuer: 'authelia.com'
  algorithm: 'sha1'
  digits: 6
  period: 30
  skew: 1
  secret_size: 32
  allowed_algorithms:
    - 'SHA1'
  allowed_digits:
    - 6
  allowed_periods:
    - 15
  disable_reuse_security_policy: false

session:
  secret: 'secret'
  redis:
    host: '/run/redis/redis-server.sock'
    port: 0
    timeout: '5s'
    max_retries: 0
    database_index: 0
    maximum_active_connections: 8
    minimum_idle_connections: 0

  cookies:
    - name: 'authelia_session'
      domain: 'mydomain.com'
      authelia_url: 'https://auth.mydomain.com'
      expiration: '1 hour'
      inactivity: '5 minutes'

regulation:
  max_retries: 3
  find_time: '2 minutes'
  ban_time: '5 minutes'

storage:
  encryption_key: 'secret'
  postgres:
    address: 'tcp://postgresql-lxc.localdomain:5432'
    database: 'secret'
    username: 'secret'
    password: 'secret'
    schema: 'public'
    timeout: '5s'

notifier:
  disable_startup_check: false
  filesystem:
    filename: '/etc/authelia/notification.txt'

identity_providers:
  oidc:
    hmac_secret: 'secret'
    jwks:
      - key: |
          -----BEGIN PRIVATE KEY-----

                    SECRET

          -----END PRIVATE KEY-----
    enable_client_debug_messages: false
    minimum_parameter_entropy: 8
    enforce_pkce: 'public_clients_only'
    enable_pkce_plain_challenge: false
    enable_jwt_access_token_stateless_introspection: false
    discovery_signed_response_alg: 'none'
    discovery_signed_response_key_id: ''
    require_pushed_authorization_requests: false
    authorization_policies:
      policy_name:
        default_policy: 'deny'
        rules:
          - policy: 'two_factor'
            subject: 'user:username'
    cors:
      endpoints:
        - 'authorization'
        - 'token'
        - 'revocation'
        - 'introspection'
      allowed_origins:
        - 'https://auth.mydomain.com'
      allowed_origins_from_client_redirect_uris: false
    clients:
      - client_id: 'nextcloud'
        client_name: 'NextCloud'
        client_secret: 'secret'
        public: false
        authorization_policy: 'two_factor'
        consent_mode: 'implicit'
        require_pkce: true
        pkce_challenge_method: 'S256'
        redirect_uris:
          - 'https://nextcloud.mydomain.com/apps/oidc_login/oidc'
        scopes:
          - 'openid'
          - 'profile'
          - 'email'
          - 'groups'
        response_types:
          - 'code'
        grant_types:
          - 'authorization_code'
        access_token_signed_response_alg: 'none'
        userinfo_signed_response_alg: 'none'
        token_endpoint_auth_method: 'client_secret_basic'
      - client_id: 'miniflux'
        client_name: 'Miniflux'
        client_secret: 'secret'
        public: false
        consent_mode: 'implicit'
        authorization_policy: 'two_factor'
        redirect_uris:
          - 'https://miniflux.mydomain.com/oauth2/oidc/callback'
        scopes:
          - 'openid'
          - 'profile'
          - 'email'
        userinfo_signed_response_alg: 'none'
        token_endpoint_auth_method: 'client_secret_basic'
      - client_id: 'paperless'
        client_name: 'Paperless'
        client_secret: 'secret'
        public: false
        require_pkce: true
        pkce_challenge_method: 'S256'
        consent_mode: 'implicit'
        authorization_policy: 'two_factor'
        redirect_uris:
          - 'https://paperless.mydomain.com/accounts/oidc/authelia/login/callback/'
        scopes:
          - 'openid'
          - 'profile'
          - 'email'
        userinfo_signed_response_alg: 'none'
        token_endpoint_auth_method: 'client_secret_basic'
      - client_id: 'gitea'
        client_name: 'Gitea'
        client_secret: 'secret'
        public: false
        authorization_policy: 'two_factor'
        consent_mode: 'implicit'
        redirect_uris:
          - 'https://gitea.mydomain.com/user/oauth2/authelia/callback'
        scopes:
          - 'openid'
          - 'email'
          - 'profile'
        response_types:
          - 'code'
        grant_types:
          - 'authorization_code'
        access_token_signed_response_alg: 'none'
        userinfo_signed_response_alg: 'none'
        token_endpoint_auth_method: 'client_secret_basic'
```

### User's Database

```yaml
---
###############################################################
#                         Users Database                      #
###############################################################

# This file can be used if you do not have an LDAP set up.

# List of users
users:
  username:
    disabled: false
    displayname: 'username'
    # Password is authelia
    password: '$6$rounds=50000$BpLnfgDsc2WD8F2q$Zis.ixdg9s/UOJYrs56b5QEZFiZECu0qZVNsIYxBaNJ7ucIL.nlxVCT5tqh8KHG8X4tlwCFm5r6NTOZZ5qRFN/'
    email: 'username@email.com'
    groups:
      - 'admins'
      - 'dev'
      - 'admin'
...
```

### systemd

Make the systemd unit.

```systemd
[Unit]
Description=Authelia authentication and authorization server
Documentation=https://www.authelia.com
After=multi-user.target

[Service]
User=authelia
Group=authelia
UMask=027
Environment=AUTHELIA_SERVER_DISABLE_HEALTHCHECK=true
ExecStart=/usr/bin/authelia --config /etc/authelia/configuration.yml
SyslogIdentifier=authelia
CapabilityBoundingSet=
NoNewPrivileges=yes
RestrictNamespaces=yes
ProtectHome=true
PrivateDevices=yes
PrivateUsers=yes
ProtectControlGroups=yes
ProtectKernelModules=yes
ProtectKernelTunables=yes
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
```

Then enable it.

```shell
systemctl enable --now authelia
```

### Redis

Redis is super simple to setup, and we can just use the defaults here.

```shell
apt update
apt install redis
systemctl enable --now redis
```

## Caddy Integration

I use Caddy to integrate Authelia to all my services.

You can that up pretty easily.

```caddy
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
```

I like to include the blank `authelia_session` so that the backend servers do not see the session cookie for Authelia.
