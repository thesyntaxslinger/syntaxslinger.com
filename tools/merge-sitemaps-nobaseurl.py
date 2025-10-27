#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import os
import re
import subprocess
from urllib.parse import urlparse, urlunparse

JEKYLL_SITEMAP = "_site/sitemap.xml"
MKDOCS_SITEMAP = "homelab/site/sitemap.xml"
OUTPUT_SITEMAP = "_site/sitemap.xml"
MKDOCS_BASE = "homelab"   # 👈 adjust this if you ever change the folder

def read_urls(path, prefix=None):
    urls = []
    if not os.path.exists(path):
        return urls
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for url in root.findall("sm:url", ns):
        loc = url.find("sm:loc", ns)
        lastmod_el = url.find("sm:lastmod", ns)
        if loc is not None:
            loc_text = loc.text.strip()
            # 👇 Add /homelab/ prefix if missing and this is a MkDocs sitemap
            if prefix and f"/{prefix}/" not in loc_text:
                parsed = urlparse(loc_text)
                new_path = f"/{prefix}{parsed.path}"
                loc_text = urlunparse(parsed._replace(path=new_path))
            urls.append((loc_text, lastmod_el.text.strip() if lastmod_el is not None else None))
    return urls

def get_git_lastmod_for_url(url):
    rel_path = None
    if f"/{MKDOCS_BASE}/" in url:
        rel_path = url.split(f"/{MKDOCS_BASE}/")[-1]
        rel_path = f"{MKDOCS_BASE}/docs/{rel_path.rstrip('/')}.md"
    else:
        rel_path = f"{url.split('/')[-2]}.md"

    if not os.path.exists(rel_path):
        return None

    try:
        output = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "--", rel_path],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if output:
            return output
    except Exception:
        pass
    return None

def normalize_lastmod(lastmod, url=None):
    if not lastmod:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\+\d{2}:\d{2}|Z)$", lastmod):
        return lastmod

    if re.match(r"^\d{4}-\d{2}-\d{2}$", lastmod):
        git_time = get_git_lastmod_for_url(url) if url else None
        if git_time:
            return git_time
        dt = datetime.strptime(lastmod, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.isoformat(timespec="seconds")

    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def merge():
    urls = {}

    # Jekyll sitemap (no prefix)
    for loc, lastmod in read_urls(JEKYLL_SITEMAP):
        urls[loc] = normalize_lastmod(lastmod, url=loc)

    # MkDocs sitemap (force /homelab/ prefix)
    for loc, lastmod in read_urls(MKDOCS_SITEMAP, prefix=MKDOCS_BASE):
        urls[loc] = normalize_lastmod(lastmod, url=loc)

    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for loc, lastmod in sorted(urls.items()):
        url_el = ET.SubElement(urlset, "url")
        ET.SubElement(url_el, "loc").text = loc
        ET.SubElement(url_el, "lastmod").text = lastmod

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    tree.write(OUTPUT_SITEMAP, encoding="utf-8", xml_declaration=True)
    print(f"✅ Combined sitemap written to {OUTPUT_SITEMAP} ({len(urls)} URLs)")

if __name__ == "__main__":
    merge()

