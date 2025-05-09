---
title: How To Setup Miniflux and Flaresolverr
description: Trying to set up your RSS reader can be troubling when trying to deal with website owners bot protection, but there is a fix.
author: syntaxslinger
date: 2025-04-29 00:00:00 +1000
categories: [Homelab]
image:
  path: /assets/img/miniflux.webp
---

## Miniflux

Miniflux is a great application that allows you to subscribe to website RSS feeds. It is a very simplistic piece of software and is my choice of an RSS reader.
There's an issue though, and that is some websites have not setup their websites properly that will block your Miniflux instance from being able to fetch and read your feeds.
To get past this, Miniflux developers recommend getting into contact with these websites and ask them to unblock their RSS feeds from bot traffic. Sometimes, this can be unfeasible, though. I decided to go down another path.

## Flaresolverr

Flaresolverr is another great piece of software. It was developed to access websites that use Cloudflare captchas to then act as a sort of proxy for other software.

## How Can We Combine Both?

By default, Miniflux doesn't have support for Flaresolverr, so we need to find another way that we can pass through traffic from Flaresolverr to Miniflux.
I chose to go with the Flask framework that is Python, since it was easy, and I have experience with Python.
To set up, you are going to need to install Flask into your environment.

```bash
pip3 install flask
```
Or you can use your package manager to install it without a virtual environment
```bash
apt install python3-flask
```

After we have installed Flask, we can now move onto the script.
You will need a working installation for both Miniflux and Flaresolverr for this.

```python
#!/usr/bin/python3

from flask import Flask, request, Response
import requests

app = Flask(__name__)
FLARESOLVERR_URL = "http://127.0.0.1:8191/v1"

@app.route('/', defaults={'path': ''}, methods=["GET", "POST"])
@app.route('/<path:path>', methods=["GET", "POST"])
def proxy(path):
    target_url = request.args.get('url')

    if not target_url:
        return "Missing 'url' parameter", 400

    data = {
        "cmd": "request.get",
        "url": target_url,
        "maxTimeout": 60000,
        "session": "miniflux_session"
    }

    try:
        response = requests.post(FLARESOLVERR_URL, json=data)
        result = response.json()
        if result['status'] == "ok":
            return Response(result['solution']['response'], mimetype="text/html")
        else:
            return "FlareSolverr error", 500
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)

```

Depending on whether you are running Miniflux and Flaresolverr in either Docker or bare-metal, you will need to change this script so that it reflects the internal addresses of your Docker network.

Simply run the script to start your Flask server.

```bash
python3 ./miniflux-flaresolverr-flask.py
```
Now your script is running and is available to your Miniflux instance at http://127.0.0.1:5000, to query it to test, use the `curl` command.

```bash
curl -I "http://127.0.0.1:5000?url=https://domain.tld/feed.rss"
```
You should get an output that looks something like this.

```bash
HTTP/1.1 200 OK
Server: Werkzeug/3.1.3 Python/3.13.3
Date: Wed, 29 Apr 2025 07:24:03 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 224748
Connection: close
```

Flaresolverr would look like this.

```bash
2025-04-29 17:24:01 INFO     Incoming request => POST /v1 body: {'cmd': 'request.get', 'url': 'https://domain.tld/feed.rss', 'maxTimeout': 60000, 'session': 'miniflux_session'}
2025-04-29 17:24:03 INFO     Challenge not detected!
2025-04-29 17:24:03 INFO     Response in 2.243 s
2025-04-29 17:24:03 INFO     127.0.0.1 POST http://127.0.0.1:8191/v1 200 OK
```

Also, the Flask server should look like this.

```bash
127.0.0.1 - - [29/Apr/2025 07:24:03] "HEAD /?url=https://domain.tld/feed.rss HTTP/1.1" 200 -
```
Congrats! You have a working way to query websites through Flaresolverr, but we still require a way for our Miniflux instance to actually send requests through our Flask instance.
For this, we can use the [URL Rewrite Rules](https://miniflux.app/docs/rules.html#rewriteurl-rules) to get Miniflux to rewrite requests to our new URL.
We need to use a bit of regex for this one.

```bash
rewrite("^https:\/\/domain\.tld(\/.*)?$"|"http://127.0.0.1:5000?url=https://domain.tld$1")
```
Paste this into the feed options inside your Miniflux instance for the specific feed you want to pass through to Flaresolverr, and all is done!