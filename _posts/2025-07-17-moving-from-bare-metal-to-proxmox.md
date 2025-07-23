---
title: Moving From Bare-Metal To Proxmox
description: Read about my experience with moving from Docker to Proxmox
author: syntaxslinger
date: 2025-07-17 00:00:00 +1000
categories: Homelab
image:
  path: /assets/img/proxmox.webp
---


## My Home Server
I had a home server that was just a bare-metal Debian 12 install that has been serving me for about a year now once I started homelabbing. I knew I was outgrowing it and needed something a bit more advanced where I could play around with stuff a bit more. Especially with VM's and other operating systems.

### Bare-Metal
My server basically was just Debian 12 with a bunch of docker containers (I think I had over 70 at some point, it was a bloated mess now that I think back). I used docker for pretty much anything as it was just so easy and held me hand along the way. I had custom scripts for all my backups as well as custom scripts for pretty much everything else. It was actually really nice and I sort of miss it now.

### What I Wanted to Transition Too
I wanted something where I could be a bit more robust with my setup, and customise it the way I wanted. I knew that Proxmox was a thing, so I went with this.

## I Did It
I basically did it. I moved my bare-metal server that was running Debian 12, to a Proxmox cluster with an extra Intel NUC.

This was a very tedious process at first, as is all homelabbing, as I had no idea what I was doing.

### How Did I Do It
I'm not going to go into everything I did, as some techniques I tried ultimately failed. But I will share everything I did that actually made this work.

First I booted up a live CD of Linux and opened up an SSH server in it. I then did a file system image of my current boot drive using rsync (I also made a Clonezilla backup as well just in case I really messed up).

I then fired up the Proxmox installer and installed the OS over my old Debian machine which was a breeze.

After getting that out the way I made myself a new VM and booted up into another live environment inside the VM.

I then copied all my old data from the file system image I made earlier with rsync into this new drive inside the VM.

It worked! I had my new VM that was running inside of Proxmox. I just updated my DHCP server to use the new MAC for the IPs I wanted, and also updated the IPv6 addresses in my DNS.

This was ultimately a success.

### Where I Went From Here
I basically did this when I finished up my last blog post which was 3 months ago, as all my time has just been basically learning about Proxmox and virtualisation in general. As well as managing my own server infrastructure without docker.

I don't think I'll go into depth with it here. But I will list off a bit of a dot point list of achievements.

- Setup Proxmox Backup Server inside a VM (I know this is bad, but homelabbing on a budget will always have some hacks here and there)
- Migrated the Docker services inside my VM into individual LXC containers (this low-key took a really long time due to the LSIO containers change their paths to have all the config in /config as a docker volume)
- Set up a cache server for apt for all my new VM's and LXC containers
- Set up a macOS VM for iMessage on Android (I got the Apple ID banned from doing this, I do not recommend)
- Set up a Proxmox Cluster with an Intel NUC to spread out the load of all my LXC containers
- Virtualised OPNsense after buying a dual 10g NIC and putting that into my cluster
- Learned how to upgrade my infrastructure without hold-your-hand type tools like “Watchtower” in docker
- Learnt Caddy! (I think it's heaps easier than Nginx or NPM)
- Proxmox Email notifications for PVE and PBS
- GPU pass-through to LXC containers (I also did it with my first initial docker VM which was a LOT more complicated than doing it for an LXC)

## What Are The Major Differences
I think the biggest difference is how you manage a hypervisor like Proxmox running the same services as a Docker bare-metal install.

With my bare-metal install, I literally just setup watchtower and did absolutely nothing. If stuff broke, it broke and I would fix it later.

Now after setting my own infastructure with LXC containers, I feel like I know much more about what is going on with my containers, and I know how to update them manually if I need to. Not only that, but it taught me lots of skills about virtualisation technology in general, and I think for now I'm going to stick with Proxmox for a while until something more shiny shows up.