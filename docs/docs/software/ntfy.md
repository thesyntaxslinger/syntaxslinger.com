# ntfy - Self-Hosted Push Notifications

ntfy is a self-hosted service that you can pipe multiple applications notifications through essentially. I like it since I don't need to shove my homelab notifications through cloud services like Google FCM or Apples IOS.

I also use it for apps that support `UnifiedPush` notifications.

## Installation

To get started with ntfy, we are going to use a Debian 13 LXC container and install their apt repository.

```shell
mkdir -p /etc/apt/keyrings
curl -L -o /etc/apt/keyrings/ntfy.gpg https://archive.ntfy.sh/apt/keyring.gpg
apt install apt-transport-https
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/ntfy.gpg] https://archive.ntfy.sh/apt stable main" \
    | tee /etc/apt/sources.list.d/ntfy.list
apt update
apt install ntfy
```

## Configuration

Ntfy uses a pretty simple authentication file being `yaml` that we can populate at `/etc/ntfy/server.yml`:

> This configuration uses `enable-signup: false` so you will not be able to make a user unless you change this to `true`. You can change it back later to `false` if you want to disable signup (probably better for a private instance).

```yaml
cache-batch-size: 0
cache-batch-timeout: "0ms"

auth-file: /var/lib/ntfy/auth.db
auth-default-access: "deny-all"

behind-proxy: true

attachment-cache-dir: /var/lib/ntfy/attachments
attachment-total-size-limit: "2G"
attachment-file-size-limit: "15M"
attachment-expiry-duration: "3h"

enable-signup: false
enable-login: true
```

Now start the ntfy systemd unit which should have been automatically provided on installation.

```shell
systemctl enable --now ntfy
```

### UnifiedPush

This is probably the main selling point of ntfy. You can pipe a lot of other self-hosted apps through this.

We will need to set this up, because by default with our instance, we can only push to ntfy if we are signed in. We need to change this for the `UnifiedPush` protocol.

```shell
ntfy access '*' 'up*' write-only
```

## Extra

I like to start tasks and then get notified later from them when doing sys-admin work. I wrote a nice little bash script that I just `curl | bash` for when I want to do this.

Here is the script:

```bash
#!/bin/bash

check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: Required command '$1' not found in PATH" >&2
        exit 1
    fi
}

check_dependency curl
check_dependency jq

INPUT=$(cat)

JSON=$(jq -n --arg msg "$INPUT" \
             --arg title "Command output" \
             --arg topic "up-secret" \
             --argjson priority 3 \
             '{topic: $topic, title: $title, message: $msg, priority: $priority}')


curl -X POST -H "Content-Type: application/json" \
     -d "$JSON" \
     'https://ntfy.mydomain.com'
```

I then just can do a task like this:

```shell
ls -alh | bash -c "$(curl -fsSL https://scripts.mydomain.com/ntfysend.sh)"  
```

Which gets send straight to my ntfy instance.
