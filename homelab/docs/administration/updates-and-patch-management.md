---
title: Updates & Patch Management
---

# Updates and Patch Management

This is the most tedious part of any homelab. Some people choose to be lazy and install some kind of service like [watchtower](https://github.com/containrrr/watchtower), or just flat out don't patch anything at all.

I like to opt-in for a more involved approach though.

## Debian

Most of my VM's and LXC containers are using Debian 13 as their base operating system.

### Unattended Upgrades

I use the unattended-upgrades package to do security updates for my homelab.

This is sort of lazy! But I decided that I want security updates as soon as possible, as the Debian security updates are designed to be applied as soon as possible in a stable way.

The worst thing that could happen is that a Debian update breaks from an unattended-upgrade, and I view the log `/var/log/unattended-upgrades/unattended-upgrades.log` and reverse the breaking changes until a fix is developed.

Here is my simple config that is applied to all machines when I bootstrap them:

```bash
Unattended-Upgrade::Origins-Pattern {
        "origin=Debian,codename=${distro_codename},label=Debian-Security";
        "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
};
```

Obviously this kind of automatic updating is lazy and shouldn't be encouraged. If this was a production environment, I would not be patching machines this way at all and would opt for some of the better methods below.

### Ansible

For automatic patching for non security updates, I like to use ansible. It completely automates the way I patch my machines, and will alert me of failures along the way.

I have 2 pretty simple Ansible playbooks that cover this. `apt-check.yaml` and `apt-upgrade.yaml`.

#### `apt-check.yaml`
```yaml
---
- name: Check for available APT updates
  hosts: debian_hosts,debian_containers
  tasks:
    - name: Update APT package index
      apt:
        update_cache: yes
        cache_valid_time: 3600
      changed_when: false
      register: apt_update
      until: apt_update is succeeded
      retries: 3
      delay: 5

    - name: Check for available updates
      command: apt list --upgradable
      register: apt_updates
      changed_when: false
      environment:
        LC_ALL: C

    - name: Extract upgradable packages
      set_fact:
        # Create an ACTUAL list of package names
        upgradable_packages: >
          {{ 
            (apt_updates.stdout_lines | default([]))[1:] | 
            map('split', '/') | map('first') | 
            reject('==', '') | unique | list 
          }}

    - name: Show available updates
      debug:
        msg: |
          Available updates:
          {% for pkg in upgradable_packages %}
            - {{ pkg }}
          {% endfor %}
      when: upgradable_packages | length > 0

    - name: Show no updates available
      debug:
        msg: "No available updates"
      when: upgradable_packages | length == 0
```

#### `apt-upgrade.yaml`

```yaml
---
- name: Update and upgrade apt packages
  hosts: debian_containers
  #become: yes
  serial: "{{ batch_size | default('100%') }}"  # Controls rolling updates

  tasks:
    - name: Update apt package index
      ansible.builtin.apt:
        update_cache: yes
        cache_valid_time: 3600  # Only update if older than 1 hour
      register: apt_update
      until: apt_update is succeeded
      retries: 3
      delay: 5

    - name: Upgrade packages (all updates but not dist)
      ansible.builtin.apt:
        upgrade: yes
        autoremove: yes
        autoclean: yes
      register: apt_upgrade
      async: 300
      poll: 15

    - name: Check if reboot required
      ansible.builtin.stat:
        path: /var/run/reboot-required
      register: reboot_required

    - name: Reboot host if needed
      ansible.builtin.reboot:
        msg: "Rebooting after kernel update"
        connect_timeout: 5
        reboot_timeout: 300
        pre_reboot_delay: 15
        post_reboot_delay: 30
      when: 
        - reboot_required.stat.exists
```

The workflow is usually to run the `apt-check.yaml` playbook to see what kind of packages will be updated/if there even is any. Then manually search up what these updates do and if there are any breaking changes that might conflict with my current configurations, and then to finally run the `apt-upgrade.yaml` playbook - put my feet up and watch the magic happen.

## Other Updates

Some software isn't in Debian repositories and needs to be updated manually whether that is through a GUI or re-compiling from source.

### RSS

RSS or real-simple-syndication feeds are a great way to get the latest updates/notifications for new software updates.

It is as simple as getting the GitHub releases page for the software you are using, then adding `.atom` onto the end of the url.

This will create an RSS feed for that software which will show up in your RSS reader. 

Now on the next update that the comes from the software maintainer, you can browse it and read the latest patch notes and any breaking changes if any exist.

This helps when patching, since you know what to expect and can become a better systems administrator.

![RSS Update Feed](/assets/img/updates-in-software-releases-light.webp#only-light)
![RSS Update Feed](/assets/img/updates-in-software-releases-dark.webp#only-dark)


### Updating ZSH Globally With Ansible

I love ZSH. So here is how I update all my VM's, LXC containers and VPS's with ansible:

```yaml
---
- name: Sync .zshrc files to hosts
  hosts: debian_hosts,debian_containers,remote_hosts
  gather_facts: true
  vars:
    local_zshrc: "{{ lookup('env', 'HOME') }}/.config/zsh/.zshrc"
    remote_zshrc: "{{ ansible_env.HOME }}/.config/zsh/.zshrc"

  tasks:
    - name: Ensure remote zsh config directory exists
      file:
        path: "{{ remote_zshrc | dirname }}"
        state: directory
        mode: '0755'

    - name: Copy local .zshrc to remote hosts
      copy:
        src: "{{ local_zshrc }}"
        dest: "{{ remote_zshrc }}"
        mode: '0644'

    
# ------------------------------------------------
- name: Update .zshrc on webserver
  hosts: pkgcache
  gather_facts: false
  tasks:
    - name: Copy .zshrc
      copy:
        src: "{{ lookup('env', 'HOME') }}/.config/zsh/.zshrc"
        dest: "/var/www/webserver/static/zsh/.zshrc"
        mode: '0644'

```

## Why Manually Applying Patches Matters

A good example of this recently was an update to my RSS reader [Miniflux](https://github.com/miniflux/v2).

In a [release](https://github.com/miniflux/v2/releases/tag/2.2.14) they listed that this update had a breaking change and that you should run some SQL commands to fix them.

Without seeing this patch note, I would have been stuck wondering why my app was no longer working.

If I was using something like [watchtower](https://github.com/containrrr/watchtower), then I would have been screwed.


