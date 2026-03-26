#!/usr/bin/env python3
"""
Script para extrair abstracts das URLs do Springer e atualizar o arquivo .bib.
"""

import re
import time
import sys
import random
import requests
from bs4 import BeautifulSoup

INPUT_BIB = "springerlink_2026-03-26.bib"
OUTPUT_BIB = "springerlink_2026-03-26_with_abstracts.bib"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def fetch_abstract(url: str, retries: int = 3) -> str:
    """Fetches the abstract from a Springer article/chapter URL."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 429:
                wait = 60 + random.uniform(5, 15)
                print(f"  Rate limited. Waiting {wait:.0f}s...", flush=True)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code} for {url}", flush=True)
                return ""
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple selectors common in Springer pages
            selectors = [
                # Article abstract section
                {"id": "Abs1-content"},
                # Chapter abstract section
                {"id": "abstract-content"},
                # Generic meta description fallback
            ]
            for sel in selectors:
                tag = soup.find(attrs=sel)
                if tag:
                    text = tag.get_text(separator=" ").strip()
                    text = re.sub(r"\s+", " ", text)
                    return text

            # Try section with class abstractSection
            tag = soup.find("div", class_=re.compile(r"abstract", re.I))
            if tag:
                text = tag.get_text(separator=" ").strip()
                text = re.sub(r"\s+", " ", text)
                return text

            # Try meta description as last resort
            meta = soup.find("meta", attrs={"name": "description"})
            if meta and meta.get("content"):
                return meta["content"].strip()

            print(f"  No abstract found for {url}", flush=True)
            return ""

        except requests.RequestException as e:
            print(f"  Request error (attempt {attempt+1}): {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(5)
    return ""


def parse_bib_entries(bib_text: str):
    """
    Parse raw .bib text into a list of (entry_type, key, fields_dict, raw_text) tuples.
    Preserves order and raw text for reconstruction.
    """
    # Split into entries using a simple approach: find @Type{ or @Type spaces {
    # We'll work line by line to keep raw blocks
    entries = []
    current_lines = []
    brace_depth = 0
    in_entry = False

    for line in bib_text.splitlines(keepends=True):
        stripped = line.strip()

        if not in_entry:
            if stripped.startswith("@"):
                in_entry = True
                current_lines = [line]
                brace_depth = line.count("{") - line.count("}")
            # skip blank lines between entries
        else:
            current_lines.append(line)
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                entries.append("".join(current_lines))
                current_lines = []
                in_entry = False
                brace_depth = 0

    return entries


def extract_url_from_entry(entry: str) -> str:
    """Extract the url field value from a .bib entry."""
    m = re.search(r'\burl\s*=\s*\{([^}]+)\}', entry, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r'\burl\s*=\s*"([^"]+)"', entry, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def has_abstract(entry: str) -> bool:
    """Check if the entry already has an abstract field."""
    return bool(re.search(r'\babstract\s*=', entry, re.IGNORECASE))


def inject_abstract(entry: str, abstract: str) -> str:
    """Insert abstract field into a bib entry before the closing brace."""
    if not abstract:
        return entry
    # Escape special chars for BibTeX: { }
    abstract = abstract.replace("{", "{{").replace("}", "}}")
    # Find last } to insert before it
    last_brace = entry.rfind("}")
    if last_brace == -1:
        return entry
    # Find the line ending before last brace to add comma if needed
    before = entry[:last_brace].rstrip()
    if not before.endswith(","):
        before += ","
    abstract_field = f'\n abstract = {{{abstract}}}\n'
    return before + abstract_field + entry[last_brace:]


def main():
    print(f"Reading {INPUT_BIB}...", flush=True)
    with open(INPUT_BIB, "r", encoding="utf-8") as f:
        bib_text = f.read()

    entries = parse_bib_entries(bib_text)
    print(f"Found {len(entries)} entries.", flush=True)

    updated_entries = []
    failed = []

    for i, entry in enumerate(entries):
        url = extract_url_from_entry(entry)
        # Extract entry key for logging
        m = re.match(r'@[^{]+\{([^,\s]+)', entry)
        key = m.group(1) if m else f"entry_{i}"

        if has_abstract(entry):
            print(f"[{i+1}/{len(entries)}] {key}: already has abstract, skipping.", flush=True)
            updated_entries.append(entry)
            continue

        if not url:
            print(f"[{i+1}/{len(entries)}] {key}: no URL found, skipping.", flush=True)
            updated_entries.append(entry)
            continue

        print(f"[{i+1}/{len(entries)}] {key}: fetching {url}", flush=True)
        abstract = fetch_abstract(url)

        if abstract:
            print(f"  Abstract found ({len(abstract)} chars).", flush=True)
            entry = inject_abstract(entry, abstract)
        else:
            print(f"  No abstract retrieved.", flush=True)
            failed.append((key, url))

        updated_entries.append(entry)

        # Polite delay between requests
        delay = random.uniform(1.5, 3.5)
        time.sleep(delay)

    print(f"\nWriting output to {OUTPUT_BIB}...", flush=True)
    with open(OUTPUT_BIB, "w", encoding="utf-8") as f:
        f.write("\n".join(updated_entries))

    print(f"\nDone! {len(entries)} entries processed.", flush=True)
    if failed:
        print(f"\nFailed to retrieve abstract for {len(failed)} entries:", flush=True)
        for key, url in failed:
            print(f"  - {key}: {url}", flush=True)


if __name__ == "__main__":
    main()
