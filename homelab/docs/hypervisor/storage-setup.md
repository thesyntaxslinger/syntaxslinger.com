---
title: Storage Setup
parent: Hypervisor
nav_order: 0
---

# Storage Setup

For my storage setup, I have a pretty cursed setup. If you read the [introduction](/homelab/) you know that my first "homelab" was actually just a repurposed desktop running Debian 11.

Since I migrated this same machine later into node for my Proxmox cluster, I kept the same type of filesystem since I didn't have a spare 18TB hard drive just laying around that I can use for the migration.

I have gone with ZFS for my boot drive on all my nodes without redundancy, and then for my big storage box, I have 3 HDD's using BTRFS without redudancy either. Sounds scary I know, but I have a good back up method for it all, so I am not too worried about loosing data.

Here is a nice little graph.

![storage graph](/assets/drawio.svg#only-dark)
![storage graph](/assets/drawio-light.svg#only-light)


As you can see. This isn't the biggest setup in the world. But it is enough to run some sort of HA setup and works overall pretty well for my own usecase.
