# Installing SSMS 22 from the offline layout (target machine)

Run everything from an **elevated** Command Prompt (Run as administrator).

## 1. Place the layout first, install second

Copy the layout to the **final** path, *then* install. The installer records
the layout path; moving it afterwards breaks updates and component adds.

```bat
D:\
  SSMS_Layout\
    vs_SSMS.exe
    vs_installer.exe
    Layout.json
    ChannelManifest.json
    Catalog.json
    certificates\
    <package folders>
```

From a `.zip`, extract with a tool that preserves long paths — package
directory names here reach ~160 chars, so `D:\SSMS_Layout\` keeps you under
MAX_PATH (260). Avoid extracting into a deeply nested folder.

## 2. Install

```bat
D:\SSMS_Layout\vs_SSMS.exe --noWeb --add Microsoft.Component.HelpViewer
```

| switch | meaning |
|---|---|
| `--noWeb` | never fall back to the internet for missing files |
| `--add ...` | must match the `--add` list used when the layout was built |
| `--passive` | progress bar, no interaction |
| `--quiet` | fully silent |
| `--norestart` | suppress auto-reboot |

Silent unattended install:

```bat
D:\SSMS_Layout\vs_SSMS.exe --noWeb --quiet --norestart --add Microsoft.Component.HelpViewer
```

> If you omit `--noWeb` and select a component that is not in the layout,
> the installer will try to download it — and fail on an air-gapped host.

## 3. Verify

```bat
"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -all -products * -format json
```

Confirm `Microsoft.VisualStudio.Product.SSMS` at version `22.10.x`. Then start
SSMS and connect to an instance.

## If it complains about missing components

The layout contains exactly what was requested at build time. This build has:

- ✅ base SSMS 22 x64
- ✅ offline help (`Microsoft.Component.HelpViewer`)
- ❌ Integration Services (`Microsoft.SSMS.Component.IS`)
- ❌ Reporting Services (`Microsoft.SSMS.Component.RS`)

For IS/RS you must **rebuild the layout** on the internet-connected build
machine with those `--add` flags (see `scripts/build-layout.sh`) — they
cannot be added retroactively on the offline host.

## Not yet proven

This checklist has **not** been executed on a real Windows machine. Layout
structure, manifest consistency, package count and SHA256 hashes were
verified on Linux; the install itself has not. Watch the first install
closely for any attempt to reach the network.
