# Security Firewall

My firewall setup is fairly straightforward but intentionally restrictive. The goal is to minimize exposure while maintaining functionality across both LAN and WAN environments.

## LAN

My LAN is tightly locked down. I only expose the services I actually want accessible within the network, and everything else stays protected behind key-based authentication or other access controls.

### Proxmox

* Default policy: Deny all incoming traffic, allow all outgoing.
* SSH (Port 22): Allowed for remote management, with additional hardening handled by the [bootstrapping script](/homelab/administration/bootstrapping/).
* ICMP/ICMPv6: Permitted for network diagnostics (ping checks).
* Internal service access: Restricted by default. For example, only specific containers are allowed to communicate with PostgreSQL on port 5432—everything else is blocked unless explicitly allowed.

## WAN

My WAN firewall is even more restrictive, since I prefer not to expose any public-facing services unnecessarily. Anything that can live behind a VPN stays there.

* The only service exposed to the WAN is WireGuard on port `51820/UDP`.
* Access is limited to Australian IP ranges only, which provides a light layer of obscurity and helps block random global scanning and bot traffic.

## Conclustion

Since this is a homelab environment, there isn't really much firewalling for me to be doing. I am on a seperate VLAN to the untrusted devices, and everything here is relatively already pretty restrictive.
