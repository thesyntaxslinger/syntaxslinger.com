---
title: How To Setup Port Forwarding to a WireGuard VPS with Docker
description: Whether you are behind CG-NAT or not, you should still be able to access your homelab externally.
author: syntaxslinger
date: 2025-05-01 12:00:00 +1000
categories: Homelab
image:
  path: /assets/img/Wireguard-Docker.webp
---

## Introduction

You set up your homelab, and you have some services running that you want to expose to the internet. All is well until your ISP steps in your way and bam! You cannot forward any ports since your ISP uses a CG-NAT for your IPv4 network. That sort of sucks and can be really tedious to get around.
There are a few options you can choose from whether that is to use [Cloudflare Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/), [Tailscale](https://tailscale.com), [Tayga](https://github.com/openthread/tayga). But Cloudflare Tunnels can only serve websites that are HTTP or HTTPS, so things like game servers and UDP services won't work.
Tailscale is great and allows you to do both, but getting everybody who wants to use your homelab services to install a client just to connect to you isn't very feasible. Especially if you are running something like a public website.
Tayga also works and allows you to do a complete pass-through at Layer 2. This is if you set it up in NAT64 mode, but you need public IPv6 address for this, as well as a VPS provider that gives you a subnet of IPv6. I found [apalrd](https://www,apalrd.net) has a really nice tutorial for this which you can find [here](https://www.apalrd.net/posts/2024/network_relay/#option-3---v4-to-v6-port-forwarding-with-tayga) as well as a few other solutions, check that out. 
If you are on an only IPv4 network in your homelab, you can slowly run out of options quickly. That is where WireGuard comes in.

## WireGuard

WireGuard is a VPN protocol that is modern, fast, and reliable. The only caveats to WireGuard is the ability to set up large infrastructure and scale up your VPN service since it basically just does the crypto with public and private keys and the networking. But that is out of the scope of this tutorial. 
For our use case it's going to be a perfect solution to expose our services.

## Tutorial

To properly set up this, you will need:

- A working Debian 12 VPS with a public IPv4 address (a dual-stack IPv4 and IPv6 would be even better)
- Some services you want to expose
- Docker and Docker Compose

First thing we will need to do it set up our compose file. Since we are working with Docker, we can add the service we want to expose to the WireGuard containers network stack.

```yaml
services:
  wireguard:
    image: lscr.io/linuxserver/wireguard
    container_name: wireguard
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    environment:
      - TZ=UTC
    ports:
      - "80:80"
    volumes:
      - ./wg-config:/config
      - /lib/modules:/lib/modules
    sysctls:
      - net.ipv4.conf.all.src_valid_mark=1
    restart: unless-stopped

  nextcloud:
    image: lscr.io/linuxserver/nextcloud:latest
    container_name: nextcloud
    network_mode: service:wireguard
    environment:
      - TZ=UTC
    volumes:
      - ./config:/config
      - ./data:/data
    # Ports is commented out since we are using the Wireguard containers network stack
    # ports:
      # - 80:80
    restart: unless-stopped
```
I used Nextcloud on http for this, but you can use anything. I also don't recommend exposing a port 80 to the internet since it can be very insecure, but for the sake of this tutorial it's fine.

The compose setup might be different depending on what kind of operating system your Docker host is running, so follow the documentation for that where ever you can find it. You can use any containers you like, but I went with the [LinuxServer.io](https://www.linuxserver.io/) containers as they are reputable, great support, and have very nice features. For example, adding in `PUID` and `PGID` variables to run these containers as non-root users (which not all containers on docker hub do).

Before we run this, we need to set up our WireGuard keys for both our container and the server. Here is a one-liner command that will generate you 2 pairs of private keys as well as a pre-shared key.

```bash
wg genkey | tee VPSprivatekey | wg pubkey > VPSpublickey && wg genkey | tee CLIENTprivatekey | wg pubkey > CLIENTpublickey && wg genpsk > PRESHAREDkey
```
Now you should have these files: `CLIENTprivatekey  CLIENTpublickey  PRESHAREDkey  VPSprivatekey  VPSpublickey` which I will now reference in the WireGuard configs from now on.


Before we create the client WireGuard config, let's make the server side first, since it makes more sense.

Run these commands.

```bash
# Install Wireguard
apt update
apt install wireguard -y

# Allow IPv4 forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Edit Wireguard config
vim /etc/wireguard/wg0.conf
```

Paste this into the file now.

```bash
[Interface]
Address = 10.132.64.1/24
ListenPort = 51820
PrivateKey = <VPSprivatekey>

PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT

# Peer 1
PostUp = iptables -A FORWARD -i eth0 -o wg0 -p tcp --dport 80 -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT
PostUp = iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j DNAT --to-destination 10.132.64.2
PostDown = iptables -D FORWARD -i eth0 -o wg0 -p tcp --dport 80 -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT
PostDown = iptables -t nat -D PREROUTING -i eth0 -p tcp --dport 80 -j DNAT --to-destination 10.132.64.2

PostUp = iptables -A FORWARD -i wg0 -o eth0 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -o eth0 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
# Nextcloud
PublicKey = <CLIENTpublickey>
PreSharedKey = <PRESHAREDkey>
AllowedIPs = 10.132.64.2/32
```

You will need to change `eth0` to whatever your interface is that has the public IPv4 address on it. You can also add more ports for this like UDP ports.
Now we can start our WireGuard interface, but don't forget to open the ports for it.

```bash
ufw allow 51820/udp
wg-quick up wg0
```

To make this persistent, you can use `systemd` by running `systemctl enable --now wg-quick@wg0`

For the WireGuard config, we can now create a new file in the `wg-config` folder called `wg0.conf`, this will be the client config.

```bash
[Interface]
PrivateKey = <CLIENTprivatekey>
Address = 10.132.64.2/32

[Peer]
PublicKey = <VPSpublickey>
PreSharedKey = <PRESHAREDkey>
Endpoint = <your-vps-ip-address>:51820
AllowedIPs = 10.132.64.1/32
PersistentKeepalive = 30
```

Now we have everything setup, we should be able to run our compose file and have a working setup!

```bash
docker compose up -d
```

Check to make sure everything is running correctly with `docker exec -it wireguard wg show`. You should get some output that looks like this.

```bash
interface: wg0
  public key: <CLIENTprivatekey>
  private key: (hidden)
  listening port: 54774
  fwmark: 0xca6c

peer: <VPSpublickey>
  endpoint: <vps-ip>:51820
  allowed ips: 10.132.64.1/32
  latest handshake: 34 seconds ago
  transfer: 16.65 GiB received, 48.84 GiB sent
```

Now you should be able to access that service remotely on your VPS IPv4 address from the browser, or a game server.
You can pretty much expose anything like this, you can even remove docker completely and just use a plain install on your client side and expose the ports that way.
