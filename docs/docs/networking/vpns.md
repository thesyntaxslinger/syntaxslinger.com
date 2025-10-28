# VPNs

Virtual Private Networks (VPNs) allow devices to communicate securely over untrusted networks by encrypting traffic and providing a private tunnel between endpoints. They’re commonly used to access remote systems, interconnect networks, or maintain privacy when connecting to the internet.


## Why Do I Need a VPN?

In most home networks, devices are hidden behind Network Address Translation (NAT), meaning they cannot be reached directly from the internet. This becomes a problem when you want to remotely access your internal services, connect to your homelab, or establish peer-to-peer (P2P) links.

Also, exposing a VPN endpoint is infinitely better than exposing a webserver with it's application behind it.

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

### WireGuard

For more traditional or self-hosted VPN setups, I use WireGuard directly. It’s lightweight, modern, and extremely efficient compared to older VPN protocols.

In my environment, I use WireGuard primarily over IPv6, allowing direct connectivity between systems without NAT traversal issues. The simplicity of its configuration — just public/private key pairs and interface definitions — makes it ideal for site-to-site tunnels or linking isolated environments.

WireGuard is also useful for connecting networks that need to route specific subnets, or when I want complete control over my VPN topology.
