---
title: DNS
---

# DNS

This page describes my homelab DNS setup, which is designed for speed, privacy, and internal resolution.

## Overview

I use AdGuard Home as my primary DNS server for the network. AdGuard Home handles ad-blocking, filtering, and local DNS resolution. To enhance privacy and security, AdGuard Home forwards queries to a local Unbound instance configured to use DNS-over-TLS (DoT) with external resolvers.

This setup allows:

- Centralized DNS filtering and logging via AdGuard Home
- Secure, encrypted DNS queries to external resolvers
- Redundant and distributed DNS across multiple nodes

## Resolvers

I maintain 4 Unbound resolvers distributed across my nodes:

| Node | Resolver | Notes |
|------|----------|-------|
| Node 1 | Unbound 1 |
| Node 2 | Unbound 2 |
| Node 3 | Unbound 3 |
| Node 1 | Unbound 4 | DNS64 turned off |

DNS64 is turned off for Unbound 4 for split-tunnel VPN clients

### Why Unbound?

AdGuard Home can do DNS64 on it's own, but there is actually a CNAME resolution bug where it will not follow a CNAME record properly and synthesise it to a NAT64 address. 

See [this issue](https://github.com/AdguardTeam/AdGuardHome/issues/6932) on GitHub.

To fix this, I put Unbound behind AdGuard Home and then configured Unbound to synthesise NAT64 addresses.

### Syncing AdGuard Instances

Node 1 contains the master/primary AdGuard Home instance which then has it's config taken and synced to the other 3.

There is no configuration needed for the DNS64 turned off node, since it is Unbound that handles that.

These are all synced with [adguardhome-sync](https://github.com/bakito/adguardhome-sync). 

Here is my current config for adguardhome-sync:

```yaml
cron: "0 */2 * * *"

runOnStart: true

continueOnError: true

origin:
  url: https://adguard-lxc.localdomain:443
  insecureSkipVerify: true
  username: admin
  password: 'secret'

replicas:
  - url: https://adguard2-lxc.localdomain:443
    username: admin
    password: 'secret'
    insecureSkipVerify: true

  - url: https://adguard3-lxc.localdomain:443
    username: admin
    password: 'secret'
    insecureSkipVerify: true

  - url: https://adguard4-lxc.localdomain:443
    username: admin
    password: 'secret'
    insecureSkipVerify: true

api:
  port: 0

features:
  generalSettings: true
  queryLogConfig: true
  statsConfig: true
  clientSettings: true
  services: true
  filters: true
  dhcp:
    serverConfig: true
    staticLeases: true
  dns:
    serverConfig: true
    accessLists: true
    rewrites: true
```

## Local DNS

I mainly have 2 domains for DNS. One is my bought domain from a domain registrar, and the other is for local DNS within the homelab.

I have 2 configured so that internally, services can communitcate with their `localdomain` addresses and end users can communicate with the front-facing Let's Encrypt domain that points to my [Caddy](https://github.com/caddyserver/caddy) LXC container. 
