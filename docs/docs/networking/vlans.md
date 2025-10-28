---
title: VLANs
---

# VLANs and Network Segmentation

## What are VLANs?

A VLAN, or Virtual Local Area Network, is a way to segment a physical network into multiple, isolated logical networks. Each VLAN behaves as if it is a separate network, even though multiple VLANs can share the same physical switches and cabling.

The main benefits of VLANs are:

- Isolation: Devices in one VLAN cannot directly communicate with devices in another VLAN unless explicitly allowed through routing or firewall rules. This improves security and limits broadcast traffic.
- Organization: You can separate different types of devices — for example, servers, workstations, IoT devices, and guest networks — into different VLANs.
- Scalability: VLANs make it easier to manage large networks by grouping devices logically rather than physically.

VLANs are defined by a VLAN ID (a number between 1–4094) and are implemented through a process called tagging. VLAN tags are added to network frames so that switches know which VLAN each frame belongs to.

In a homelab, VLANs are often used to:

- Isolate your lab servers from your home network
- Separate IoT or guest devices from your main network
- Create test environments without additional physical hardware

Understanding VLANs is essential before moving into more advanced topics like IPv6 subnetting and routing between different network segments.


## How I Implement VLANs In My Own Homelab

I implement VLANs using a managed switch, which allows me to separate network traffic logically while still using the same physical infrastructure. This setup helps improve security, organize my devices, and isolate sensitive systems from untrusted devices.

### My VLANs

Here is a nice graph of the structure of all my VLANs at the moment:

![VLANs Homelab](/assets/img/vlans-dark.svg#only-dark)
![VLANs Homelab](/assets/img/vlans-light.svg#only-light)


#### Trusted

This VLAN contains all devices that I personally manage and patch, like my personal computers, servers, and home automation devices. Devices here have full access to the internal network, including storage, servers, and internet. Access from the Guest or DMZ VLANs is restricted. This is where most of my own devices are located.

#### Untrusted

This VLAN is for devices I don’t manage directly, such as family members’ computers, IoT gadgets, or other potentially untrusted devices. Devices in this VLAN can access the internet but cannot directly reach Trusted or DMZ resources. Firewall rules keep these devices isolated from sensitive systems.

#### DMZ

The DMZ contains devices that are publicly accessible or semi-isolated, like web servers, VPN endpoints, or other services intended to be reached from outside. These devices are externally reachable if necessary, but access to Trusted VLAN devices is tightly controlled. The DMZ acts as a buffer between public traffic and the internal network, exposing only specific ports and services.
c and the internal network. Only specific ports/services are exposed.
