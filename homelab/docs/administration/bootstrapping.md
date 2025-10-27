---
title: Bootstrapping
---

# Bootstrapping

I hate doing repetitive tasks over and over. Especially when I need to create a new container for something.

To fix this issue and succumb to my laziness. I wrote a nice little bootstrap script to auto setup a new VM or LXC container.

```bash
# bootstrap.sh

set -euo pipefail

# This just setups up my apt cache
bash -c "$(wget -qO- https://webserver.localdomain/rewrite.sh)"

# Debian bootstrapping
if [ -d "/etc/apt/sources.list.d" ]; then
        apt-get update
        SUDO_FORCE_REMOVE=yes apt-get remove sudo nano -y
        apt-get dist-upgrade -y
        apt-get install vim unattended-upgrades rsync curl zsh htop zsh-autosuggestions zsh-syntax-highlighting -y
fi

usermod -p '*' root

# install fake sudo
cat <<'EOF' > /usr/bin/sudo
#!/bin/bash
runuser -u root -- "$@"
EOF
chmod 755 /usr/bin/sudo

cat <<EOF > /etc/ssh/sshd_config.d/00-custom.conf
Port 22
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
AllowTcpForwarding yes
AcceptEnv LANG LC_* COLORTERM NO_COLOR
EOF
systemctl restart sshd

# better vim colors
if ! grep -q "colorscheme default" /etc/vim/vimrc; then
    cat <<EOF >> /etc/vim/vimrc

colorscheme default
EOF
fi

# install zsh
echo 'export ZDOTDIR="$HOME/.config/zsh"' > $HOME/.zprofile
export ZSH_RC="$HOME/.config/zsh/.zshrc"
mkdir -p $HOME/.config/zsh
bash -c "$(wget -qO- https://webserver.localdomain/zsh.sh)" # this just downloads some zsh stuff
mkdir -p $HOME/paths
chsh root -s /usr/bin/zsh

ln -sf /usr/share/zoneinfo/Australia/Melbourne /etc/localtime
sed -Ei 's/^# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/g' /etc/locale.gen
locale-gen
echo 'LANG="en_US.UTF-8"' > /etc/locale.conf

echo "This is what you need to put into systemctl edit container-getty@tty1"
echo "[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear --keep-baud tty%I 115200,38400,9600 $TERM
"

mkdir -p '/etc/systemd/system/container-getty@1.service.d' ; bash -c 'cat <<EOF > /etc/systemd/system/container-getty@1.service.d/override.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear --keep-baud tty%I 115200,38400,9600 $TERM
EOF'

systemctl daemon-reload; systemctl restart container-getty@1.service
```
