"""
build_dataset.py - rebuild Website_urls.csv from fresh public sources.

Run it from the folder that holds manage.py (detection_of_phishing_websites):

    python build_dataset.py                    # ~40k URLs per class
    python build_dataset.py --per-class 60000  # bigger
    python build_dataset.py --keep-old         # also keep rows from the current CSV

Sources (all on GitHub, no account or API key needed):
  Phishing : mitchellkrogza/Phishing.Database  (active phishing links, refreshed daily)
  Safe     : faizann24 labeled URL set (real URLs WITH paths), top-1M domain list,
             OpenDNS top domains
Uses only the Python standard library + pandas (already in your venv).

Why it is built this way (so the model learns the URL, not the data source):
  * URLs are normalised (no http(s)://, no www.) exactly like ml_engine.normalize_url().
  * At most MAX_PER_HOST phishing URLs per host, so a few free-hosting sites
    (000webhostapp, pages.dev ...) cannot flood the data.
  * Safe and phishing rows are MATCHED on "has a path?" and URL length bucket.
    Without this the model just learns "long URL = phishing".
  * Any host seen in the phishing feed is removed from the safe set, and phishing
    URLs on the most popular safe sites are removed, so no URL carries both labels.
"""
import argparse
import csv
import io
import os
import random
import re
import sys
import urllib.request
from collections import Counter, defaultdict

import pandas as pd

BASE = "https://raw.githubusercontent.com"
SOURCES = {
    "phish": f"{BASE}/mitchellkrogza/Phishing.Database/master/phishing-links-ACTIVE.txt",
    "faiz": f"{BASE}/faizann24/Using-machine-learning-to-detect-malicious-URLs/master/data/data.csv",
    "top1m": f"{BASE}/zer0h/top-1000000-domains/master/top-1000000-domains",
    "opendns": f"{BASE}/opendns/public-domain-lists/master/opendns-top-domains.txt",
}
CACHE_DIR = "_data_cache"
MAX_PER_HOST = 2          # phishing URLs kept per host
TOP1M_TAKE = 30000        # how many top-1M domains to use as safe bare domains
MAX_URL_LEN = 250
LEN_BINS = [0, 15, 25, 40, 60, 90, 140, 10_000]

# Hosting suffixes where the *subdomain* is the real owner (treated like a registered domain)
PRIVATE_SUFFIXES = (
    "pages.dev", "github.io", "web.app", "firebaseapp.com", "netlify.app", "vercel.app",
    "herokuapp.com", "000webhostapp.com", "weebly.com", "wixsite.com", "blogspot.com",
    "workers.dev", "onrender.com", "glitch.me", "repl.co", "godaddysites.com",
)
TWO_LEVEL = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.in", "co.jp",
    "com.br", "com.cn", "co.za", "com.mx", "co.nz", "com.tr", "com.ar", "com.sg", "co.kr",
}


def download(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, key + ".txt")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    print(f"  downloading {key} ...", flush=True)
    req = urllib.request.Request(SOURCES[key], headers={"User-Agent": "phishguard-dataset-builder"})
    with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return path


def normalize(url):
    """Same rule as ml_engine.normalize_url()."""
    u = str(url).strip().lower()
    for p in ("https://", "http://", "ftp://"):
        if u.startswith(p):
            u = u[len(p):]
            break
    if u.startswith("www."):
        u = u[4:]
    return u


def host_of(u):
    h = u.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    h = h.split("@")[-1].split(":")[0]
    return h.strip(".")


def registered(host):
    for s in PRIVATE_SUFFIXES:
        if host == s or host.endswith("." + s):
            parts = host[: -len(s)].strip(".").split(".")
            return (parts[-1] + "." + s) if parts and parts[-1] else s
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in TWO_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def has_path(u):
    rest = u.split("/", 1)
    return len(rest) > 1 and rest[1].strip("/") != ""


def len_bucket(u):
    n = len(u)
    for i in range(len(LEN_BINS) - 1):
        if LEN_BINS[i] <= n < LEN_BINS[i + 1]:
            return i
    return len(LEN_BINS) - 2


def read_lines(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line:
                yield line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="Website_urls.csv")
    ap.add_argument("--keep-old", action="store_true", help="also include rows from the existing CSV")
    ap.add_argument("--cache-dir", default="_data_cache")
    args = ap.parse_args()
    global CACHE_DIR
    CACHE_DIR = args.cache_dir
    rnd = random.Random(args.seed)

    print("1/5 downloading sources")
    p_phish, p_faiz, p_top, p_open = (download(k) for k in ("phish", "faiz", "top1m", "opendns"))

    print("2/5 loading phishing feed")
    phish_all_hosts = set()
    per_host = defaultdict(list)
    for line in read_lines(p_phish):
        u = normalize(line)
        if not u or len(u) > MAX_URL_LEN or " " in u or "." not in u:
            continue
        h = host_of(u)
        if not h or "." not in h:
            continue
        phish_all_hosts.add(h)
        per_host[h].append(u)
    popular = set(normalize(l).split("/")[0] for l in read_lines(p_open))
    popular_reg = {registered(h) for h in popular}
    phish_pool = []
    dropped_popular = 0
    for h, urls in per_host.items():
        if registered(h) in popular_reg:       # phishing hosted on a top-10k site: ambiguous, skip
            dropped_popular += len(urls)
            continue
        rnd.shuffle(urls)
        phish_pool.extend(urls[:MAX_PER_HOST])
    print(f"   phishing pool: {len(phish_pool):,} URLs from {len(per_host):,} hosts "
          f"(skipped {dropped_popular:,} on popular sites)")

    print("3/5 loading safe sources")
    safe_pool = set()
    faiz = pd.read_csv(p_faiz, on_bad_lines="skip")
    for u in faiz.loc[faiz["label"] == "good", "url"].astype(str):
        u = normalize(u)
        if u and len(u) <= MAX_URL_LEN and " " not in u and "." in u:
            safe_pool.add(u)
    for i, line in enumerate(read_lines(p_top)):
        if i >= TOP1M_TAKE:
            break
        d = normalize(line.split(",")[-1])
        if "." in d and "/" not in d:
            safe_pool.add(d)
    safe_pool |= {d for d in popular if "." in d and "/" not in d}

    if args.keep_old and os.path.exists(args.out):
        old = pd.read_csv(args.out).dropna()
        for url, label in zip(old["URL"].astype(str), old["Label"]):
            u = normalize(url)
            if label == "Non Phishing":
                safe_pool.add(u)
            elif label == "Phishing":
                phish_pool.append(u)

    # never let a host appear on both sides
    before = len(safe_pool)
    safe_pool = [u for u in safe_pool if host_of(u) not in phish_all_hosts]
    print(f"   safe pool: {len(safe_pool):,} URLs (removed {before - len(safe_pool):,} seen in phishing feed)")
    phish_pool = list(dict.fromkeys(phish_pool))

    print("4/5 matching length / path distributions between the classes")
    def key(u):
        return (has_path(u), len_bucket(u))
    sb, pb = defaultdict(list), defaultdict(list)
    for u in safe_pool:
        sb[key(u)].append(u)
    for u in phish_pool:
        pb[key(u)].append(u)
    n_b = {k: min(len(sb[k]), len(pb[k])) for k in set(sb) | set(pb)}
    total = sum(n_b.values())
    f = min(1.0, args.per_class / total) if total else 0
    rows = []
    for k, n in n_b.items():
        n = int(round(n * f))
        rnd.shuffle(sb[k])
        rnd.shuffle(pb[k])
        rows += [(u, "Non Phishing") for u in sb[k][:n]]
        rows += [(u, "Phishing") for u in pb[k][:n]]
    rnd.shuffle(rows)

    print("5/5 writing", args.out)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["URL", "Label"])
        w.writerows(rows)
    df = pd.DataFrame(rows, columns=["URL", "Label"])
    print(df.Label.value_counts().to_string())
    print("path share      :", df.assign(p=df.URL.map(has_path)).groupby("Label").p.mean().round(3).to_dict())
    print("avg URL length  :", df.assign(n=df.URL.str.len()).groupby("Label").n.mean().round(1).to_dict())
    print(f"done: {len(df):,} rows -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
