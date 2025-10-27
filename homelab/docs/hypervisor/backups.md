---
title: Backups
---

# Backups

Backups are probably the most important thing you need to do when running any kind of homelab.

For my homelab backups, I use two kinds of backups:

- **Proxmox Backup Server (PBS)**
- **Borg Backup**

## The 3-2-1 Backup Rule

Before diving into tools, it’s important to understand the **3-2-1 backup rule**: 

> **Keep 3 copies of your data, on 2 different types of media, with 1 copy stored offsite.**

Here’s I implement this in my homelab environment:

**3 Copies:**  

1. HDD on my desktop PC
2. SSD on my desktop PC
3. Offsite to a Virtual Private Server

**2 Types of Media:**  

1. HDD
2. SSD

**1 Offsite Copy:**  

1. A Virtual Private Server in the cloud 

I would love to try out immutable backups as well, but for my current setup at home and my threat model. This works perfectly.

## Borg Backup

I use Borg mainly for my files that aren't in VM's or LXC containers. For example - for my NAS LXC container where I have NFS and SMB setup, this uses my BTRFS storage as the backend storage provider, and because of the size of this - it doesn't get backed up at all.

This is where Borg comes in - I select the files I want manually to backup via a `bash` script, which will then backup to the same places my PBS instances go too:

1. My desktop PC for both the HDD and SSD
2. My VPS

These are encrypted backups with a different encryption scheme/key to the PBS datastores.

## Proxmox Backup Server

For anything that is Proxmox related like VM's or LXC containers, I use Proxmox Backup Server to do my backups with.

PBS is a great system for backing up VMs and LXC containers since it only backs up the data that has changed. It uses deduplication and compression, so your storage footprint stays small even with frequent backups.

In my setup:

- Each PVE node is configured to back up to a centralized PBS instance.
- Daily incremental backups run automatically.
- I keep **7 daily**, **4 weekly**, and **3 monthly** restore points.
- Backups are verified weekly to ensure integrity.
- All backups use **encryption** for protection and compliance.

This is installed inside Proxmox LXC container with a simple LXC mount that points to my BTRFS storage setup.

### Docker

I actually run 3 seperate instances of Proxmox Backup Server in my environment:

1. My desktop PC for both the HDD and SSD via Docker
2. My VPS via Docker

Here is the latest compose file I am using for this:

``` { .yaml .copy }
services:
  pbs:
    image: ayufan/proxmox-backup-server
    container_name: pbs
    hostname: pbs-desktop
    ports:
      - "127.0.0.1:8007:8007"
    volumes:
      - ./pbs_etc:/etc/proxmox-backup
      - ./pbs_logs:/var/log/proxmox-backup
      - ./pbs_lib:/var/lib/proxmox-backup
      - ./ssd-pbs:/data/ssd-pbs
      - /mnt/backups/hdd-pbs:/data/hdd-pbs
    tmpfs:
      - /run
    restart: unless-stopped
    stop_signal: SIGHUP
```

As you can see from the yaml, the SSD and HDD are both mounted and have seperate datastores inside of them.

Although this isn't recommended, the PBS software is actually just a .deb file that uses a few dependencies, so you can even install it bare metal if you want to. Of course you will miss out on the fancy features of PBS like the tape backups and smart monitoring, but this works super well for my setup.

## Linking Both Methods Together

I script both of these backups periodically with cron and systemd respectively. Cron sometimes isn't smart enough to handle starting scripts after the network is up - so I rely on systemd and it's `network-online.target` for some tasks.

### Offsite VPS

#### Borg Backup

I will start with the simplest backup that occurs - which is Borg too the VPS. This is just a simple script that runs every night with a crontab entry:

```bash
#!/bin/bash

DATE=$(date +%Y-%m-%d_%H-%M-%S)
export BORG_PASSPHRASE='this is a secret :P'

borg create --exclude '/mnt/btrfs-data/backups/PBS' --progress --stats --compression auto,lzma,6  ssh://ssh_host/root/backups/server::$DATE /mnt/btrfs-data/NAS/files /mnt/btrfs-data/backups
borg prune --keep-daily 7 --keep-weekly 4 --keep-monthly 3 ssh://ssh_host/root/backups/server
borg compact ssh://ssh_host/root/backups/server
```

This will handle all the files in my NAS LXC that I use for filesystem type operations.

#### Proxmox Backup Server

This is just a sync job from my PBS instance in a LXC container, to my VPS:

![Proxmox Backup Server Sync Job](/assets/img/pbs-sync-job-dark.webp#only-dark)
![Proxmox Backup Server Sync Job](/assets/img/pbs-sync-job-light.webp#only-light)

This will run every night and make sure all the containers are synced up, as well as remove old ones that don't exist anymore (cleanup).


### Desktop PC

This is a bit of a tricky one. My desktop PC is Linux will full disk encryption. There isn't a way that allows me to unlock my PC without storing my master encryption password somewhere on another system in cleartext. I have opted for the more sane approach.

***A bash script that runs on startup***

But this can't just run every time my computer boots up - as my backups are only done nightly.

This script needs to handle both of the Borg side, as well as the PBS side.

And we also need to start it with systemd so we can make sure the network is online + also make it non-blocking so I can still use my desktop environment.

```systemd
# /etc/systemd/system/daily-backup.service
[Unit]
Description=Startup script for backups
After=network-online.target
Wants=network-online.target

[Service]
Type=
ExecStart=/root/scripts/daily-backup.sh

[Install]
WantedBy=default.target
```

I found this works perfectly for systemd.

```bash
#!/bin/bash

BACKUP_STATE="/root/scripts/daily-backup-state"
BACKUP_LOG="/root/scripts/daily-backup.log"
LOCK_FILE="/tmp/daily-backup.lock"
TODAY=$(date '+%Y-%m-%d')

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "[$(date)] Backup already running. Exiting." | tee -a "$BACKUP_LOG"
    exit 0
fi

cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

until ping -c 1 -W 2 pve.localdomain > /dev/null 2>&1; do
    sleep 1
done

if [[ -f "$BACKUP_STATE" ]]; then
    LAST_BACKUP=$(cat "$BACKUP_STATE")
    if [[ "$LAST_BACKUP" == "$TODAY" ]]; then
        echo "[$(date)] Backup already completed today. Exiting." | tee -a "$BACKUP_LOG"
        exit 0
    fi
fi

echo "[$(date)] Starting daily backup..." | tee -a "$BACKUP_LOG"

/root/scripts/backup-to-pve.sh 2>&1 | tee -a "$BACKUP_LOG"

# BORG
### This command runs on the hypervisor so that I can use inode checking for borg = faster
ssh pve 'BORG_PASSPHRASE="this is a secret :P" /root/scripts/start-borgbackup.sh' 2>&1 | tee -a "$BACKUP_LOG"
su borguser -c '/home/borguser/prune.sh' 2>&1 | tee -a "$BACKUP_LOG"

echo "[$(date)] Borg backup completed successfully" | tee -a "$BACKUP_LOG"

# PBS STUFF
echo | tee -a "$BACKUP_LOG"
echo "Starting docker." | tee -a "$BACKUP_LOG"
systemctl start docker | tee -a "$BACKUP_LOG"
sleep 5
cd /root/Documents/docker-files/pbs
docker compose up --force-recreate --remove-orphans -d >/dev/null 2>&1

while ! nc -z localhost 8007 > /dev/null 2>&1; do
  sleep 5
done

sleep 5

# ssd-pbs
echo | tee -a "$BACKUP_LOG"
echo "Starting the task for SSD backups in pbs-desktop." | tee -a "$BACKUP_LOG"
echo | tee -a "$BACKUP_LOG"
echo "--------------- STARTING ---------------" | tee -a "$BACKUP_LOG"
docker exec pbs proxmox-backup-manager sync-job run s-30213d74-d194 | tee -a "$BACKUP_LOG"
echo "--------------- ENDING ---------------" | tee -a "$BACKUP_LOG"
echo | tee -a "$BACKUP_LOG"

sleep 60

docker restart pbs

sleep 60 | tee -a "$BACKUP_LOG"

echo "SSD is now done it's task." | tee -a "$BACKUP_LOG"


# hdd-pbs
echo | tee -a "$BACKUP_LOG"
echo "Starting the task for HDD backups in pbs-desktop." | tee -a "$BACKUP_LOG"
echo | tee -a "$BACKUP_LOG"
echo "--------------- STARTING ---------------" | tee -a "$BACKUP_LOG"
docker exec pbs proxmox-backup-manager sync-job run s-e85e330b-b368 | tee -a "$BACKUP_LOG"
echo "--------------- ENDING ---------------" | tee -a "$BACKUP_LOG"
echo | tee -a "$BACKUP_LOG"

sleep 5

echo "HDD is now done it's task." | tee -a "$BACKUP_LOG"

docker exec pbs sync
sync

echo | tee -a "$BACKUP_LOG"
echo "Stopping docker and docker.socket" | tee -a "$BACKUP_LOG"
cd /root/Documents/docker-files/pbs
docker compose down >/dev/null 2>&1
systemctl stop docker >/dev/null 2>&1
systemctl stop docker.socket >/dev/null 2>&1


# Update state file only on success
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "$TODAY" > "$BACKUP_STATE"
    echo "[$(date)] State file updated" | tee -a "$BACKUP_LOG"
else
    echo "[$(date)] Backup failed! State not updated" | tee -a "$BACKUP_LOG"
fi

if [ -e /tmp/daily-backup-shutdown ]; then
    systemctl poweroff
fi

su myuser -c notify-send "Daily backup finished! Make sure to check the logs briefly!"
```

Looks pretty bad I know. But it serves it purpose with the following features:

- Only runs once a day, if interrupted it will try again on next reboot.
- Handles both Borg and PBS.
- Uses inodes due to starting Borg remotely for a "push" rather than "pull" (faster).
- Supports shutdown if I want to leave for the day but I need the PC to say on for more backups.

## Restore Testing

Backups are literally pointless if you don't test them regularly. That is why I regularly once a month test to make sure that my VM's and LXC containers are restoreable, and my Borg repo offsite and on my desktop is able to be mounted (via python-pyfuse3) and restored from. 

## Other Backups

I mentioned encryption for all of this. So what happens if a fire hits my home and I lose everything and only have my offsite backup?

That is why I have a portable usb key that contains all my encryption keys protected with full disk encryption if I need to access this.

Since these keys don't get updated very often. It's just a matter of updating them when you make changes to your encryption.

I also keep my keys on my phone which already has full disk encryption by default which will probably be used before the USB key.
