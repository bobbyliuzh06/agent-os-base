#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, glob, sys

PENDING = "D:/agent-os/PENDING"
KEEP = 50
MAX_TOTAL_MB = 500

def log(s):
    print(s, flush=True)

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if not os.path.isdir(PENDING):
        log("PENDING dir missing, nothing to clean")
        return 0
    files = []
    for pat in ("*.reasoning.txt", "*.gate.reasoning.txt"):
        files += glob.glob(os.path.join(PENDING, pat))
    files = sorted({f for f in files if os.path.isfile(f)}, key=lambda x: os.path.getmtime(x))
    total = sum(os.path.getsize(f) for f in files)
    deleted = 0
    saved_total = total
    max_bytes = MAX_TOTAL_MB * 1024 * 1024
    while len(files) > KEEP or saved_total > max_bytes:
        if not files:
            break
        oldest = files.pop(0)
        try:
            sz = os.path.getsize(oldest)
            os.remove(oldest)
            deleted += 1
            saved_total -= sz
        except Exception as e:
            log("remove error: " + str(e))
    log("cleanup: scanned=%d deleted=%d total_before=%d(total_after=%d) keep=%d max_mb=%d" %
        (len(files) + deleted, deleted, total, saved_total, KEEP, MAX_TOTAL_MB))
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("cleanup error: " + str(e))
        sys.exit(1)
