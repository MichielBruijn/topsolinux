#!/usr/bin/env python3
"""Download the TopSolid installation media from TopSolid's own download server.

usage: fetchmedia.py DEST [--version-only]

This is the server TopSolid.Downloader.exe (on the installation media) uses: a CurrentVersion.txt with
the current release, and per release a files.xml listing every file with its size and SHA-1. Files that
are already complete are skipped, so an interrupted download continues where it stopped.
Progress lines ("# text" and a percentage) suit zenity --progress.
"""
import concurrent.futures
import hashlib
import os
import sys
import threading
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'https://cdn2.topsolid.com/BE3B5E20-CF79-4B83-8C17-B24F5E62E2D5'
WORKERS = 6
lock = threading.Lock()
done_bytes = 0


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest().upper()


def report(total):
    print(f'{done_bytes * 100 / total:.1f}\n# Downloading TopSolid: {done_bytes / 1e9:.1f} of {total / 1e9:.1f} GB',
          flush=True)


def download(base, dest, path, size, sha1, total):
    global done_bytes
    local = os.path.join(dest, *path.split('\\'))
    if os.path.isfile(local) and os.path.getsize(local) == size and sha1_of(local) == sha1:
        with lock:
            done_bytes += size
        return
    os.makedirs(os.path.dirname(local), exist_ok=True)
    url = base + '/' + urllib.parse.quote(path.replace('\\', '/'))
    for attempt in range(4):
        got = 0
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(local + '.part', 'wb') as f:
                for block in iter(lambda: r.read(1 << 20), b''):
                    f.write(block)
                    got += len(block)
                    with lock:
                        done_bytes += len(block)
            if os.path.getsize(local + '.part') == size and sha1_of(local + '.part') == sha1:
                os.replace(local + '.part', local)
                return
        except OSError as e:
            print(f'# retrying {path}: {e}', file=sys.stderr, flush=True)
        with lock:
            done_bytes -= got
    raise RuntimeError(f'could not download {path}')


def main():
    dest = sys.argv[1]
    version = fetch(BASE + '/CurrentVersion.txt').decode('utf-8-sig').strip()
    if '--version-only' in sys.argv:
        print(version)
        return
    base = BASE + '/' + urllib.parse.quote(version)
    root = ET.fromstring(fetch(base + '/files.xml'))
    files = [(f.get('path'), int(f.get('size')), f.get('sha1').upper()) for f in root.iter('file')]
    total = sum(size for _, size, _ in files)
    os.makedirs(dest, exist_ok=True)
    stop = threading.Event()

    def ticker():
        while not stop.wait(2):
            report(total)

    threading.Thread(target=ticker, daemon=True).start()
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        for job in [pool.submit(download, base, dest, p, s, h, total) for p, s, h in files]:
            job.result()
    stop.set()
    report(total)
    print(f'# TopSolid {version} downloaded', flush=True)


if __name__ == '__main__':
    main()
