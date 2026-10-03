#!/usr/bin/env python3
"""Seed Wine's ROOT cert store from the host CA bundle.

Wine ships ZERO trusted root CAs (a real Windows box imports them via
Windows Update, which never runs under Wine). Without them, the SSMS
bootstrapper fails Authenticode verification of vs_installer.opc with:

    0x80096004  CERT_E_UNTRUSTEDROOT   "Certificate is invalid"

certutil.exe and cert-sync.exe are both STUBS in Wine, so the only way
in is to write the registry yourself. Keys are named by SHA-1 thumbprint
(uppercase, no colons) and the value is a serialized CERT_CONTEXT blob.

NOTE: cert data here is deliberately stored as raw DER in the "Blob"
value. Wine tolerates this; a real Windows CERT_CONTEXT has a header, so
if you ever verify on Windows, use certutil instead.

Usage:  python3 seed-roots.py [--dry-run]
"""
import hashlib
import os
import re
import subprocess
import sys

CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"   # Arch/Debian
PREFIX = os.path.expanduser("~/.wine")
USER_REG = os.path.join(PREFIX, "user.reg")
# Windows registry keys use backslashes doubled inside .reg files.
KEY = r"HKCU\Software\Microsoft\SystemCertificates\Root\Certificates"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(CA_BUNDLE):
        sys.exit(f"no CA bundle at {CA_BUNDLE}")

    pem = open(CA_BUNDLE).read()
    blocks = re.findall(
        r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", pem, re.S
    )
    print(f"host CA bundle: {len(blocks)} certificates")

    tmp_pem, tmp_der = "/tmp/_seed.pem", "/tmp/_seed.der"
    entries = []
    for block in blocks:
        open(tmp_pem, "w").write(block + "\n")
        if run(["openssl", "x509", "-in", tmp_pem,
                "-outform", "DER", "-out", tmp_der]).returncode:
            continue
        der = open(tmp_der, "rb").read()
        thumb = hashlib.sha1(der).hexdigest().upper()
        hexstr = ",".join(f"{b:02x}" for b in der)
        # wrap at 76 cols with trailing backslashes, as reg.exe expects
        lines = ['"Blob"=hex:' + hexstr[:76]]
        rest = hexstr[76:]
        while rest:
            lines.append("  " + rest[:76])
            rest = rest[76:]
        entries.append((thumb, "\\\n".join(lines)))

    if not entries:
        sys.exit("no usable certificates converted - is openssl installed?")

    body = "Windows Registry Editor Version 5.00\r\n\r\n"
    for thumb, blob in entries:
        body += f"[{KEY}\\{thumb}]\r\n{blob}\r\n\r\n"

    out = os.path.join(PREFIX, "seed-roots.reg")
    if dry:
        out = "/tmp/seed-roots.dry.reg"
    open(out, "w", newline="\r\n").write(body)
    print(f"wrote {len(entries)} roots -> {out}")

    if dry:
        print("dry run: not importing")
        return

    # Wine must not be running mid-write or wineserver may overwrite us.
    if run(["wineserver", "-k"]).returncode != 0:
        print("note: wineserver -k returned non-zero (may not have been running)")
    run(["wine", "reg", "import", out])

    n = sum(
        1
        for line in open(USER_REG, encoding="utf-8", errors="replace")
        if r"SystemCertificates\\Root\\Certificates\\" in line
    )
    print(f"HKCU Root subkeys now in user.reg: {n}")
    print("verify with: wine reg query 'HKCU\\Software\\Microsoft\\"
          "SystemCertificates\\Root\\Certificates' | grep -c Certificates")


if __name__ == "__main__":
    main()
