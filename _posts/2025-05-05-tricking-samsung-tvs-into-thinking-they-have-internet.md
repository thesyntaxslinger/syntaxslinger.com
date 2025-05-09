---
title: Tricking Samsung TVs Into Thinking They Have Internet (when they don't)
description: I don't like my smart TVs to connect to the internet, but I also want basic features like DNS to work with them. That is a basic feature right? "Wrong!" - Samsung
author: syntaxslinger
date: 2025-05-05 00:00:00 +1000
categories: Homelab
image:
  path: /assets/img/samsung-tv-firewalled.webp
---

If you don't know already. [Samsung](https://www.samsung.com/) has this odd thing with their Smart TV devices where if they don't constantly ping home, they go into a state where they turn off DNS and all other internet features.

The only thing that still works on them, is the ability to still access LAN IP addresses on the same subnet.

This has been quite annoying when self-hosting services like a Plex server for your friends and family to enjoy, as you need to use IP addresses instead of your over-engineered homelab with your own DNS server and rewrite rules.

Especially if you have something like a dynamic IPv6 prefix that changes a lot. Of course, you can just use a ULA for these devices, but then you lose out on the wonderful invention of GUA's for IPv6!

I came across a very old post made in 2014 recently [here](https://www.sodnpoo.com/posts.xml/spoofing_the_samsung_smart_tv_internet_check.xml). I thought I would give it a shot and try to replicate what the post did. To my horror, it worked. Samsung still haven't made it harder to try to do this, and it has been almost 11 years!

So I'll touch up quickly what I did to achieve this. I used a combination of these services running at home to pull it off.

- An [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) instance
- A server running [NGINX](https://github.com/nginx/nginx) with [PHP-FPM](https://php-fpm.org/) available for `fastcgi`
- A Samsung TV completely firewalled off from the internet

I went with AdGuard for this as they have a really powerful filtering rules section that allows you to use regex and specify specific clients.

The AdGuard Home DNS server will rewrite the DNS record for a few of Samsung's domains it uses to verify internet connectivity. It then passes that off to our NGINX server which will serve some files for it.

I have read that these domains can vary depending on your TV model and the country you're in. But they are pretty easy to find since Samsung uses unencrypted HTTP connections to fetch these files.

## How To Find The Domains

Use the AdGuard Home `Custom filtering rules` section in the `Filters` tab to rewrite all DNS queries for your Samsung TV to our NGINX server.

```
/.*/$dnsrewrite=192.168.1.2,client=192.168.1.84
```

The NGINX server in this case is `192.168.1.2` and the Samsung TV is `192.168.1.84`.

From that we should be able to `tail -f` the NGINX `access.log` file and see what domains the TV is trying to connect to. You will need to go to the internet settings on your Samsung TV and keep pressing the retry button.

Let's open that up on our NGINX server.

```bash
server@nginx ~ tail -f /var/log/nginx/access.log
[05/May/2025:09:50:52 +0000] 404 - GET http cdn.samsungcloudsolution.com "/Public/network/files/check.xml" [Client 192.168.1.84] [Length 150] [Gzip -] "-" "-"
[05/May/2025:09:50:54 +0000] 404 - GET http time.samsungcloudsolution.com "/openapi/timesync?client=T20O" [Client 192.168.1.84] [Length 150] [Gzip -] "-" "-"
```

I found both of these on my TV, which are actually both needed to spoof our internet.

The `cdn.samsungcloudsolution.com` is what seems to be hosting a `check.xml` file. So we can probably assume this is the file for internet checks.

The `time.samsungcloudsolution.com` domain is trying to query the current time. The time domain is as just as important, since if the time is out of sync, some requests to our local services will fail (at least in my testing).

> A significant note here is that I have a home setup where my router translates all plain text DNS requests on IPv4 and IPv6 to go through my own DNS server. I'm not 100% sure that the Samsung TVs aren't falling back to hard coded DNS servers. So just beware.
{: .prompt-warning }

## Setting Up Our Backend

So we need to mimic two domains here and they are both serving different files. The CDN domain is just going to be a static HTTP server block in our NGINX. The time domain is a different story. Since this is going to be dynamic, we can use a bit of PHP to get the current time, and serve this file instead.

First we can set up our root HTML files for our NGINX server and create the same directory structure that the CDN domain was using in our domain grabbing section above. Mine was `/Public/network/files/check.xml`, so I will make that file and then grab the file that the Samsung TV was trying to query.

```bash
mkdir -p /var/www/html/fake-samsung/Public/network/files
wget -P /var/www/html/fake-samsung/Public/network/files/. https://cdn.samsungcloudsolution.com/Public/network/files/check.xml
```

For the PHP script, I used this one and just put it in the root of our HTML directory with the filename `timesync.php`.

```php
<?php  
$milliseconds = round(microtime(true) * 1000);  
$mb_milliseconds = pack("QQ", $milliseconds, $milliseconds);  
echo $mb_milliseconds;  
?>
```


### NGINX

Now for the NGINX server blocks. Replace the domains you are using for this with the ones that you found.

```nginx
server {  
 listen 80;  
 listen [::]:80;  
 server_name cdn.samsungcloudsolution.com;  
 root /data/nginx/samsung-custom;  
}  
  
server {  
 listen 80;  
 listen [::]:80;  
 server_name time.samsungcloudsolution.com;  
  
 root /data/nginx/samsung-custom;  
 index index.php;  
  
 location = /openapi/timesync {  
   default_type application/octet-stream;  
   fastcgi_pass 127.0.0.1:9000;  
   include fastcgi_params;  
   fastcgi_param SCRIPT_FILENAME $document_root/timesync.php;  
   }
}
```

You might use a Unix sock for the fastcgi_pass, but I had already set up my environment with a listen port instead.

Restart NGINX and double check to make sure everything is still working in the `access.log` when you press the retry button in your Samsung TV network settings.

It should be saying the TV is online and connected to the internet even though it is completely firewalled up

### Stopping Our TVs From Blowing Up NGINX

We need to change the filtering rules now so that it stops directing all DNS requests of our Samsung TVs to our NGINX server.

```shell
/^(cdn|time)\.samsungcloudsolution\.com$/$dnsrewrite=192.168.1.2,client=192.168.1.84
```

The NGINX server in this instance is `192.168.1.2` and the Samsung TV is `192.168.1.84`

You can also replace all these IPv4 rules with IPv6 ones, but I am already running IPv4 and AdGuard Home doesn't return any AAAA records from the upstream server if you only specify a single A record.

## Conclusion

Now you can feel free again enjoying your Samsung TV with DNS enabled. It should be successfully querying the connectivity check server and the time server respectively.

As I stated, this might not work with all Samsung TVs, as I was only able to test with the two that reside in my house. But a better solution would be if the TVs would work with local DNS servers even though they had no internet connection from the factory… I wish!