#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import os
import re
import subprocess

JEKYLL_SITEMAP = "_site/sitemap.xml"
MKDOCS_SITEMAP = "docs/site/sitemap.xml"
OUTPUT_SITEMAP = "_site/sitemap.xml"

def read_urls(path):
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
            urls.append((loc.text.strip(), lastmod_el.text.strip() if lastmod_el is not None else None))
    return urls

def get_git_lastmod_for_url(url):
    """Try to infer lastmod from the git log using the corresponding file path"""
    rel_path = None
    if "/docs/" in url:
        rel_path = url.split("/docs/")[-1]
        rel_path = f"docs/docs/{rel_path.rstrip('/')}.md"
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
    """Ensure lastmod is full ISO8601; enhance date-only entries with real file timestamps if possible."""
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

    # Fallback
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def merge():
    urls = {}

    for source_path in (JEKYLL_SITEMAP, MKDOCS_SITEMAP):
        for loc, lastmod in read_urls(source_path):
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

