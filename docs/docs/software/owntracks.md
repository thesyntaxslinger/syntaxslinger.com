# OwnTracks - Self-Hosted Life360

This app is a lifesaver for me since friends and family want me to share my location with them, but I don't want some company in California USA to have a whole data structure of my own personal habits and lifestyle.

## Installation and Configuration

We will be using a Debian 13 LXC container for this and the [OwnTracks Quicksetup Booklet](https://owntracks.org/booklet/guide/quicksetup/) since the awesome devs behind OwnTracks have made the setup so simple you don't even have to do much setup.

First we will clone the repo:

```shell
apt update
apt install git -y
git clone --depth=1 https://github.com/owntracks/quicksetup
```

Then we will edit the configuration.

```shell
cp configuration.yaml.example configuration.yaml
vim configuration.yaml
```

Here is my configuration:

```yaml
dns_domain: "owntracks.mydomain.com"

email: "username@email.com"

opencage_apikey: "secret"

friends:
  - { tid: "UR", username: "user", devicename: "device", password: "" }
  - { tid: "UR", username: "user", devicename: "device", password: "" }
  - { tid: "UR", username: "user", devicename: "device", password: "" }
  - { tid: "UR", username: "user", devicename: "device", password: "" }
  - { tid: "UR", username: "user", devicename: "device", password: "" }
  - { tid: "UR", username: "user", devicename: "device", password: "" }
```

Now bootstrap the quicksetup which will install everything for you:

```shell
sudo ./bootstrap
```

This should install a webserver, an MQTT broker, and the [OwnTracks Frontend](https://github.com/owntracks/frontend).

Simply go to your `dns_domain` and you can get setup with all the apps on your devices and configure them how you want.
