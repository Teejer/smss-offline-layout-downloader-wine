#!/usr/bin/env python3
"""Check an SSMS offline layout: required files, manifest, scope, arch bloat.

Usage: python3 verify-layout.py [PATH]   (default ~/Downloads/smss/SSMS_Layout)
"""
import json
import os
import subprocess
import sys

LAYOUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Downloads/smss/SSMS_Layout")

REQUIRED = ["Layout.json", "ChannelManifest.json", "Catalog.json",
            "certificates"]


def main():
    if not os.path.isdir(LAYOUT):
        sys.exit(f"no layout at {LAYOUT}")
    print(f"layout: {LAYOUT}")
    fail = 0

    for name in REQUIRED:
        ok = os.path.exists(os.path.join(LAYOUT, name))
        print(f"  [{'ok' if ok else 'MISSING'}] {name}")
        fail += 0 if ok else 1

    lay = json.load(open(os.path.join(LAYOUT, "Layout.json")))
    uri = lay.get("installChannelUri", "")
    offline = uri.startswith(".")
    print(f"  [{'ok' if offline else 'WARN'}] installChannelUri={uri}"
          f"  ({'offline' if offline else 'POINTS ONLINE'})")
    fail += 0 if offline else 1
    print(f"  productId={lay.get('productId')} arch={lay.get('arch')}")
    print(f"  add={lay.get('add')}")

    ch = json.load(open(os.path.join(LAYOUT, "ChannelManifest.json")))
    info = ch.get("info", {})
    print(f"  version={info.get('productDisplayVersion')} "
          f"build={info.get('buildVersion')}")

    dirs = [d for d in os.listdir(LAYOUT)
            if os.path.isdir(os.path.join(LAYOUT, d))]
    pkgs = [d for d in dirs if "," in d]
    for comp in ("IS", "RS"):
        hit = [d for d in pkgs if f"SSMS.Component.{comp}" in d]
        print(f"  component {comp}: {'present' if hit else 'NOT included'}")

    # cross-check every payload listed by the channel manifest exists
    miss = 0
    total = 0
    for it in ch.get("channelItems", []):
        # 'Manifest' items are the source channel manifests themselves;
        # the layout stores the parsed ChannelManifest.json instead, so
        # their payload files legitimately do not appear in the layout.
        if it.get("type") == "Manifest":
            continue
        for pl in it.get("payloads", []):
            fn = pl.get("fileName")
            if not fn:
                continue
            total += 1
            if not any(os.path.exists(os.path.join(LAYOUT, d, fn))
                       for d in pkgs) and not os.path.exists(
                           os.path.join(LAYOUT, fn)):
                miss += 1
    print(f"  channel payloads: {total} checked, {miss} missing")

    empty = [r for r, _, fs in os.walk(LAYOUT) for f in fs
             if os.path.getsize(os.path.join(r, f)) == 0]
    print(f"  zero-byte files: {len(empty)}")

    size = subprocess.run(["du", "-sh", LAYOUT], capture_output=True,
                         text=True).stdout.split("\t")[0]
    n = subprocess.run(["find", LAYOUT, "-type", "f"],
                       capture_output=True, text=True).stdout.count("\n")
    print(f"  size={size} files={n}")
    print("\nRESULT:", "PROBLEMS FOUND" if (fail or miss) else "LAYOUT OK")
    return 1 if (fail or miss) else 0


if __name__ == "__main__":
    sys.exit(main())
