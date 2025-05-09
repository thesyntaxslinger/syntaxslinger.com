---
title: Protect WordPress With Fail2Ban
description: Sadly there are some pesky people in the world that just love brute forcing WordPress login pages. Let's fix that.
author: syntaxslinger
date: 2025-05-03 00:00:00 +1000
categories: [Web Development]
image:
  path: /assets/img/wordpress-login-page.webp
---

## WordPress

[WordPress](https://wordpress.org) is probably one of the most popular content management systems (CMS) ever, and it continues to be. Even though it is miles behind a lot of other content management systems with all the security risks of the vast plugin system. It still continues to be used widely in this day and age. Sadly there are some really annoying people in the world that just seem to love dedicating their free time to trying to brute-force these websites. 

This can cost you a lot of bandwidth for your WordPress site and is also a massive security risk if you aren't using strong passwords (you should be).

## The Fix

We can utilise Fail2Ban to mitigate these attacks and offload this to our Linux kernel, or an even better option would be [Cloudflare](https://github.com/fail2ban/fail2ban). If we offload this to Cloudflare, we can easily take the load off of our little WordPress server and have a happy life again.

We will be using an [NGINX](https://nginx.org/) server for this. NGINX makes it very easy to set up and parse the `access.log` file and get the IP address of our attacker if you have your NGINX server setup correctly to use the `CF-CONNECTING-IP` header.

No biggie, this is actually really easy to do since [Cloudflare publishes their IP ranges](https://www.cloudflare.com/ips/) that they use. We can also make some rules to block all IP's that are not from Cloudflare. 


### Cloudflare

If you aren't using Cloudflare, you can just [skip this step](#fail2ban) and proceed ahead. 

For the Cloudflare setup, we can run a simple script that will generate our NGINX directives for us.

```bash
#!/bin/bash

NGINX_REAL_IP="/etc/nginx/cloudflare/real_ips.conf"
NGINX_ALLOWED="/etc/nginx/cloudflare/allowed.conf"
CLOUDFLARE_IPV4="$(curl -s https://www.cloudflare.com/ips-v4)"
CLOUDFLARE_IPV6="$(curl -s https://www.cloudflare.com/ips-v6)"

mkdir -p /etc/nginx/cloudflare

echo "$CLOUDFLARE_IPV4" | sed 's/^/set_real_ip_from /; s/$/;/' > $NGINX_REAL_IP
echo "$CLOUDFLARE_IPV6" | sed 's/^/set_real_ip_from /; s/$/;/' >> $NGINX_REAL_IP
echo "real_ip_header CF-Connecting-IP;" >> $NGINX_REAL_IP

echo "$CLOUDFLARE_IPV4" | sed 's/^/allow /; s/$/;/' > $NGINX_ALLOWED
echo "$CLOUDFLARE_IPV6" | sed 's/^/allow /; s/$/;/' >> $NGINX_ALLOWED
echo "deny all;" >> $NGINX_ALLOWED

```

Include the both files in your NGINX config before any other locations on your site.

```nginx
# /etc/nginx/sites-enabled/my-website.conf

include /etc/nginx/cloudflare/allowed.conf;
include /etc/nginx/cloudflare/real_ips.conf;
```

The reason for two files is that sometimes you might have a `.well-known` location that you use for [Let's Encrypt](https://letsencrypt.org/) certificates, so you don't want to be blocking those. Place the `real_ips.conf` above this location and the `allowed.conf` file below it.

```nginx
# /etc/nginx/sites-enabled/my-website.conf

include /etc/nginx/cloudflare/real_ips.conf;

location ~ /.well-known {
  auth_basic off;
  allow all;
}

include /etc/nginx/cloudflare/allowed.conf;
```

You can put the script in a cronjob and have it run automatically to dynamically update your Cloudflare IP's cache.

### Fail2Ban

We will need two files for this, a filter and an action.

#### Action Snippet

Make sure to set the permissions for this action file to be `640` as it contains your Cloudflare Global API Key.

```
# /etc/fail2ban/actions.d/cloudflare-custom.conf

[Definition]
actionban = curl -s -o /dev/null -X POST <_cf_api_prms> \  
           -d '{"mode":"block","configuration":{"target":"<cftarget>","value":"<ip>"},"notes":"Fail2Ban <name>"}' \  
           <_cf_api_url>  
  
actionunban = id=$(curl -s -X GET <_cf_api_prms> \  
                  "<_cf_api_url>?mode=block&configuration_target=<cftarget>&configuration_value=<ip>&page=1&per_page=1&notes=Fail2Ban%%20<name>" \  
                  | { jq -r '.result[0].id' 2>/dev/null || tr -d '\n' | sed -nE 's/^.*"result"\s*:\s*\[\s*\{\s*"id"\s*:\s*"([^"]+)".*$/\1/p'; })  
             if [ -z "$id" ]; then echo "<name>: id for <ip> cannot be found"; exit 0; fi;  
             curl -s -o /dev/null -X DELETE <_cf_api_prms> "<_cf_api_url>/$id"  
  
_cf_api_url = https://api.cloudflare.com/client/v4/user/firewall/access_rules/rules  
_cf_api_prms = -H 'X-Auth-Email: <cfuser>' -H 'X-Auth-Key: <cftoken>' -H 'Content-Type: application/json'  
  
[Init]  
  
cftoken = <YOUR-SECRET-GLOBAL-API-KEY>
  
cfuser = <YOUR-EMAIL>
  
cftarget = ip  
  
[Init?family=inet6]  
cftarget = ip6
```


#### Filter Snippet

```
# /etc/fail2ban/filter.d/nginx-wp-login.conf

[Definition]
failregex = ^<HOST> .* "POST /wp-login.php
            ^<HOST> .* "POST /wp/wp-login.php
            ^<HOST> .* "POST .*xmlrpc.php
ignoreregex =
```

#### Jail Snippet

Depending on whether you are using Cloudflare, these will be different.

```
# /etc/fail2ban/jail.local

[DEFAULT]  
bantime  = 24h  
findtime = 10m  
maxretry = 20  
action   = iptables-allports  
           cloudflare-custom


[nginx-wp-login]  
enabled  = true  
port     = http,https  
filter   = nginx-wp-login  
logpath  = /var/log/nginx/access.log  
maxretry = 20
backend  = polling
```

If you aren't using Cloudflare, simply delete the `cloudflare-custom` line as it is not needed.

Start up Fail2Ban and enjoy your new addition to your security suite.

```bash
systemctl enable --now fail2ban
```

I would try to test it to see if your IP actually gets banned or not. Without Cloudflare, it should be pretty instant, but if you use the Cloudflare method, sometimes it can take up to a minute to actually mark your IP as banned.

You can see banned IP's with this command.

> You need to be careful when testing Fail2Ban as you will indeed lock your own IP address out. I suggest using either IPv6 privacy extensions, or a VPN to bypass this so you can log back into your server to unban your IP. Use this command to unban your IP `fail2ban-client unban ip *`
{: .prompt-danger }

```shell
root@vps:~ fail2ban-client status nginx-wp-login
Status for the jail: nginx-wp-login
|- Filter
|  |- Currently failed: 0
|  |- Total failed:     0
|  `- File list:        /var/log/nginx/access.log
`- Actions
   |- Currently banned: 0
   |- Total banned:     0
   `- Banned IP list:   
```