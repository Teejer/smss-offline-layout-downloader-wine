# SSMS 22 offline layout, built on Linux with Wine

Reproducible recipe for building a self-contained **SQL Server Management
Studio 22** offline install layout on Linux, using Wine.

Verified working on **Arch Linux / wine-11.18**, 2026-10-03.

> **Do not commit the layout.** It is ~2.4 GB. `.gitignore` excludes
> `SSMS_Layout/`, `vs_SSMS.exe`, `*.vsix` and `*.opc`. This repo holds the
> *procedure*, not the payload.

## What was built

| | |
|---|---|
| Product | SQL Server Management Studio **22.10.2** |
| Build | `22.10.12217.157` |
| Channel | `SSMS.22.SSMS.Release` |
| Arch | x64 |
| Layout size | **2.4 GB**, 1266 packages, 1094 `payload.vsix`, 1383 files |
| Integrity | 4110 SHA256 checks passed, 0 failures, 0 errors |
| Bootstrapper | `vs_SSMS.exe`, 5,695,176 bytes |
| Bootstrapper sha256 | `b874555237e9dfdd4900fda23d08e84ec23808ee18e7dd0dc3ab64c5de65b4ae` |

The layout is genuinely offline: `Layout.json` sets
`installChannelUri` to `.\ChannelManifest.json` (a local file).

## The problem

The MS guide
([create-offline](https://learn.microsoft.com/en-us/ssms/install/create-offline))
says to run `vs_SSMS.exe --layout C:\SSMS_Layout`. Under Wine that fails,
and the failure is easy to misdiagnose as a network problem:

```
Error 0x80096004: Certificate is invalid: vs_installer.opc
Download failed using WebClient engine. InvalidSignatureException
Download failed using Bits engine. System.NotImplementedException
Querying HTTP information failed with error code: 12150
```

It re-downloads the same ~48 MB `vs_installer.opc` forever: three download
engines (WinInet → WebClient → BITS), each retried, each failing signature
verification. Network is fine — TLS handshakes verify cleanly.

`0x80096004` is `CERT_E_UNTRUSTEDROOT`. **Wine ships zero trusted root
CAs** — a real Windows box imports them through Windows Update, which never
runs under Wine.

## The fix

Three things. Together these reproducibly work (whether all three are
individually necessary is not fully proven — see the caveat later):

```bash
# 1. install wine + helpers
sudo pacman -S --needed wine wine-mono wine-gecko winetricks cabextract p7zip

# 2. seed Wine's ROOT cert store from the host CA bundle
python3 scripts/seed-roots.py

# 3. install real .NET Framework 4.8 (sets mscoree=native)
winetricks -q dotnet48
```

Then build:

```bash
export WINEDEBUG=-all
wine vs_SSMS.exe --layout 'C:\SSMS_Layout' \
     --add Microsoft.Component.HelpViewer --passive
```

### Why each part is needed

**Wine has no code-signing roots.** And the obvious tools are stubs:

| Attempt | Result |
|---|---|
| `certutil.exe -addstore ROOT` | `fixme:certutil:wmain stub` — silent no-op |
| `cert-sync.exe` (wine-mono) | every import `NotImplementedException` |
| `~/.mono/certs/` file seeding | Mono still cannot build the chain |
| `wine reg import` into **HKCU** ROOT | **works** — seeds 121; store enumerates 125 |

Registry keys are named by uppercase SHA-1 thumbprint, value `Blob`=hex DER.

**Real .NET, not Mono.** The bootstrapper is a .NET Framework 4.7.2 app.
Under Wine it defaults to Mono, whose `X509Store.Import` is
`NotImplementedException` — so Mono's trust store can *never* be populated,
and Mono's `Environment.OSVersion` trips an earlier gate:

```
Error: Operating system version not supported. Requires Windows 7 SP1 or Higher.
```

`winetricks dotnet48` installs real `clr.dll` and sets
`HKCU\Software\Wine\DllOverrides\*mscoree = native`, routing
`WinVerifyTrust` through Wine's **working** native `crypt32`.

> A caveat on writing this up honestly: fixes 2 and 3 were applied in
> sequence, and the only isolation test I ran (flipping `mscoree` back to
> `builtin`) failed earlier, at the OS-version gate, so it never reached the
> certificate stage. I have **not** proven which of the two is individually
> decisive. Together they reproducibly work — re-verified with a second run
> that reached `verification returned Success` and downloaded 1.3 GB.

### Verified success signature in the log

```
Package signature verification returned Success for path: ...\vs_installer.opc
Saving Certificates to layout folder
Successfully extracted ...
Completed 'Layout' operation
```

## Install on the target Windows machine

From an **elevated** prompt, on the machine you want SSMS on:

```bat
D:\SSMS_Layout\vs_SSMS.exe --noWeb --add Microsoft.Component.HelpViewer
```

- `--noWeb` is what stops it reaching for the internet for anything missing.
- Use the **same `--add` list** used to build the layout.
- **Copy the layout to its final path before installing.** The path is
  recorded at install time; moving it later breaks updates and component adds.

## Scope: what is and is not in this layout

Built with `--add Microsoft.Component.HelpViewer`, so it is
**base SSMS 22 + offline help**.

- ❌ `Microsoft.SSMS.Component.IS` (Integration Services) — **not** included
- ❌ `Microsoft.SSMS.Component.RS` (Reporting Services) — **not** included

To include them, add them at build time:

```bash
wine vs_SSMS.exe --layout 'C:\SSMS_Layout' \
  --add Microsoft.Component.HelpViewer \
  --add Microsoft.SSMS.Component.IS \
  --add Microsoft.SSMS.Component.RS --passive
```

Layout grows ~300 MB+, and both need SQL Server-side components to be
useful, so build IS/RS only if you actually deploy those.

## Space

WebView2 ships arm64/x64/x86 (552 MB); ~384 MB is dead weight on x64.
Deleting `*arm64*` / `*machinearch=x86*` directories is **not recommended** —
the installer validates the manifest against what is on disk.

## Unverified

**I never ran the offline install itself.** That needs a Windows machine.
Layout structure, manifest consistency, package count and all SHA256 hashes
are verified; a clean offline install is inferred, not proven. On first
install, confirm it does not attempt downloads.

## Contents

```
README.md              this file
WINDOWS-INSTALL.md     checklist for the target machine
scripts/
  seed-roots.py       populate Wine's ROOT store from host CAs
  build-layout.sh     full build driver
  verify-layout.py    integrity + scope checks on a built layout
```

## Reference links

- [Create an offline layout — SSMS](https://learn.microsoft.com/en-us/ssms/install/create-offline)
- [SSMS release notes](https://learn.microsoft.com/en-us/sql/ssms/release-notes-ssms)
- Channel manifest: `https://aka.ms/ssms/22/release/channel`
