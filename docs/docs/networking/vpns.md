# VPNs

Virtual Private Networks (VPNs) allow devices to communicate securely over untrusted networks by encrypting traffic and providing a private tunnel between endpoints. They’re commonly used to access remote systems, interconnect networks, or maintain privacy when connecting to the internet.


## Why Do I Need a VPN?

In most home networks, devices are hidden behind Network Address Translation (NAT), meaning they cannot be reached directly from the internet. This becomes a problem when you want to remotely access your internal services, connect to your homelab, or establish peer-to-peer (P2P) links.

Also, exposing a VPN endpoint is infinitely better than exposing a web server with its application behind it.

A VPN solves this by:

- Creating a secure, encrypted connection between devices or networks
- Bypassing NAT and Carrier-Grade NAT (CGNAT) limitations
- Allowing remote access to internal systems as if they were on the same LAN
- Improving security by preventing exposure of sensitive ports and services


## How I Use VPNs

### Tailscale

I use Tailscale, a mesh VPN built on WireGuard, for quick and seamless connectivity between my devices. It handles NAT traversal automatically, which is especially useful since my ISP uses CGNAT, making inbound connections nearly impossible.

With Tailscale, every device on my account forms a secure P2P mesh, authenticated via my chosen identity provider. This setup gives me easy access to my homelab, even when I’m away from home, without managing firewall rules or port forwarding.

Tailscale also supports MagicDNS for simple name resolution and ACLs to control which devices can talk to each other.

To get this setup, you need an OAuth provider account (Gmail seems to be the most popular) which you then make an account on [Tailscale](https://tailscale.com).

1. Make your `tailnet`
2. Add your devices to your tailnet
3. Run `tailscale up` or turn on the switch in the mobile app.

That's it! Yeah Tailscale is actually super simple, the software handles everything for you.

#### OPNsense/PFSense and Tailscale

These don't go to well for a few reasons.

In these OpenBSD OS's, they like to make it so outbound UDP connections through a NAT don't have a static port.

This adds a little bit of obscurity to outbound requests for your average users, but for us, it is breaking UDP hole punching - so we need to turn it off.

> Taken from the official Tailscale documentation on BSD routers [here](https://tailscale.com/kb/1097/install-opnsense)

##### Direct Connections for LAN Clients

As a router/firewall, OPNsense may also be providing internet connectivity for LAN devices which themselves have a Tailscale client installed. The NAT implementation in OPNsense is an [Endpoint-Dependent Mapping, or "hard" NAT](https://tailscale.com/blog/how-nat-traversal-works), which means that LAN devices have difficulty making direct connections and often resort to [DERP Relays](https://tailscale.com/kb/1232/derp-servers).

There are a few options in which OPNsense can enable devices on the LAN to make direct connections to remote Tailscale nodes. Static NAT port mapping and NAT-PMP.

##### Static NAT port mapping

By default, OPNsense software rewrites the source port on all outgoing connections to enhance security and prevent direct exposure of internal port numbers.

Static port mapping in OPNsense involves creating a fixed association between a specific external port number and an internal IP address and port, allowing incoming traffic to be directed to the correct destination within the local network.

Go to **Firewall > NAT**, **Outbound** tab. Select **Hybrid Outbound NAT rule generation**. Select **Save**. Select **↑ Add** to create a new NAT rule to the top of the list.

Configure the rule to match UDP traffic as shown below. Note, for each rule, select the appropriate **Address Family** (IP version), **IPv4** for one and **IPv6** for the other.

![Example Static NAT port mapping configuration in Firewall : NAT : Outbound](/assets/img/static-port-mapping-opnsense.webp)

Check **Static Port** in the **Translation** section of the page. Select **Save**. Select **Apply Changes**.

In your ACLs, set [randomizeClientPort](https://tailscale.com/kb/1337/policy-syntax#network-policy-options).

```json
{
  // Other configurations
  "randomizeClientPort": true
}
```

From the command line, use `tailscale ping` node to verify the connection path between two nodes. Also useful in this scenario is `tailscale netcheck`.


### WireGuard

I like to use WireGuard on mobile since it is a bit lighter than Tailscale due to the aggressive keep-alives needed to sustain a UDP hole punch session.

In my environment, I use WireGuard primarily over IPv6, allowing direct connectivity between systems without NAT traversal issues. The simplicity of its configuration just public/private key pairs and interface definitions makes it ideal for site-to-site tunnels or linking isolated environments.

WireGuard is also useful for connecting networks that need to route specific subnets, or when I want complete control over my VPN topology.

Here is a nice script to get you started off with WireGuard.

```bash
#!/bin/bash

# envs
SERVER_PRIV=$(wg genkey)
SERVER_PUB=$(echo $SERVER_PRIV | wg pubkey)

CLIENT_PRIV=$(wg genkey)
CLIENT_PUB=$(echo $CLIENT_PRIV | wg pubkey)

DEFAULT_ROUTE=$(ip route | awk '/default/ {print $5}')

random_hex=$(openssl rand -hex 7) 
IPV6_PREFIX="fd${random_hex:0:2}:${random_hex:2:4}:${random_hex:6:4}:${random_hex:10:4}::"

# make configs
mkdir -p configs

cat <<EOF > configs/server.conf
[Interface]
Address = ${IPV6_PREFIX}1/64
ListenPort = 51820
PrivateKey = $SERVER_PRIV

PostUp = ip6tables -A FORWARD -i wg0 -j ACCEPT
PostUp = ip6tables -t nat -A POSTROUTING -o $DEFAULT_ROUTE -j MASQUERADE
PostUp = ip6tables -t nat -A POSTROUTING -s ${IPV6_PREFIX}/64 -o $DEFAULT_ROUTE -j MASQUERADE


PostDown = ip6tables -D FORWARD -i wg0 -j ACCEPT
PostDown = ip6tables -t nat -D POSTROUTING -o $DEFAULT_ROUTE -j MASQUERADE
PostDown = ip6tables -t nat -D POSTROUTING -s ${IPV6_PREFIX}/64 -o $DEFAULT_ROUTE -j MASQUERADE


[Peer]
# Client 1
PublicKey = $CLIENT_PUB
AllowedIPs = ${IPV6_PREFIX}2/128
EOF

cat <<EOF > configs/client.conf
[Interface]
Address = ${IPV6_PREFIX}2/64
PrivateKey = $CLIENT_PRIV
DNS = ${IPV6_PREFIX}1

[Peer]
PublicKey = $SERVER_PUB
Endpoint = [SERVER_PUBLIC_IP]:51820
AllowedIPs = ::/0
EOF

echo "Both configs for server.conf and client.conf saved in ./configs folder."
```

This will spit out 2 configs for a server and client. Have fun!
