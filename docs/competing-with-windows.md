# What stops Linux competing with Windows, and what Lumen does about each

Status: draft for the owner's review (2026-10-27). Decision record: [ADR 0001](decisions/0001-compete-with-windows.md).

**Goal.** Someone leaving Windows should be able to switch without losing a file, an app, a game they care about or a device they own. Where something won't come with them, Lumen tells them honestly *before* they install, and offers the best way around it.

This is a living list. Each gap is either covered by the spec, partly covered, a proposed addition, or something no distro can fix today (we say so plainly instead of pretending).

**Legend:** ✅ in the spec · 🟡 partly in the spec · ➕ proposed addition · ⛔ can't be fixed by us today; be honest about it · ⚠️ spec is technically wrong here

## 1. Windows apps

| Gap | Linux today | Lumen plan | Status |
| --- | --- | --- | --- |
| Windows-only desktop apps | Wine works for many apps, but users must know Wine exists, which version to use and which add-ons each app needs | Double-clicking an `.exe` or `.msi` opens an "Open Windows app" dialog. It shows a compatibility rating, applies a tested recipe and installs the app into its own sandboxed Bottles bottle. The app then appears in the app menu like any other | 🟡 spec has a Bottles shortcut; ➕ ratings, recipes, dialog |
| No way to know if an app will work | Users search forums (ProtonDB, WineHQ) after the fact | Lumen compatibility database: a rating in plain English (Works great / Works with issues / Won't work / Not tested yet), the reason, known issues and alternatives. Shown in the Store, in the `.exe` dialog and with `lumen app check` | ➕ |
| Microsoft Office desktop | Microsoft 365 desktop apps don't install reliably under Wine | Say so in the rating. Offer Office on the web as an installable web app, plus LibreOffice or OnlyOffice. Ship metric-compatible fonts (Liberation, Carlito, Caladea) so Word and Excel files keep their layout | ⛔ desktop Office; ➕ web app and fonts |
| Adobe Creative Cloud, big CAD suites, exam lockdown browsers, some banking and tax tools | Mostly don't run | Rating says "Won't work" with the reason, then lists alternatives (web or native) | ⛔ (honest rating) |
| Apps that will never run under Wine | Users keep a Windows partition | Later: "Windows apps in a window" running a Windows virtual machine with the user's own Windows licence (approach like the open-source WinApps project) | ➕ after v0.1 |
| Web apps feel second-class | Bookmarks in a browser | The Store can install a website as an app with its own icon and window (Office on the web, Teams, Photopea, Canva, Xbox Cloud Gaming) | ➕ |
| Windows malware in `.exe` downloads | Wine is not a sandbox | Each Windows app gets its own bottle with no access to the home folder by default. The dialog explains this in plain English | ➕ |

## 2. Games

| Gap | Linux today | Lumen plan | Status |
| --- | --- | --- | --- |
| Steam games | Proton runs most of the Steam library | Steam, Proton, Gamescope, MangoHud, GameMode | ✅ |
| Wine/Proton speed | Windows-style thread syncing needs the `ntsync` kernel module (Linux 6.14+). Fedora 44 loads it through an `ntsync-autoload` package | Image ships the module autoloaded; boot test checks `/dev/ntsync` exists | ➕ |
| Epic, GOG, EA, Ubisoft, Battle.net launchers | Possible with Heroic, Lutris or Bottles, but users must find them | Heroic and Lutris in the Store's Gaming collection with a one-click setup; database entries for each launcher | ➕ |
| Games with kernel anti-cheat (for example Valorant and some Call of Duty titles) | Blocked by the game publisher; no technical fix | Show anti-cheat status before install, using AreWeAntiCheatYet data | ⛔ (honest status) |
| Game Pass / Xbox app | No native app | Xbox Cloud Gaming as an installable web app | ⛔ native; ➕ web app |
| DirectX 12 slower on NVIDIA under Proton | Upstream driver and VKD3D-Proton work in progress | Track upstream; note it in the rating where it matters | ⛔ (upstream) |

## 3. Switching and installing

| Gap | Linux today | Lumen plan | Status |
| --- | --- | --- | --- |
| Getting Linux onto a Windows PC is scary | Download an ISO, find a USB writer, change firmware settings | "Lumen Setup for Windows": a Windows app (a fork of Fedora Media Writer, which already downloads, verifies and writes USBs on Windows). It also runs the hardware check, checks BitLocker, Fast Startup and Secure Boot certificates, shrinks the Windows partition with Windows' own tools, and sets the Windows clock to UTC | ➕ |
| "Will it work on my PC?" before downloading | Only after booting a live USB | Same `hardware.json` check, run from Windows by Lumen Setup | ✅ live USB; ➕ from Windows |
| BitLocker is on by default on many Windows 11 PCs | Linux tools can't resize a BitLocker partition; the Windows drive can't be read without the recovery key | "Install alongside Windows" detects BitLocker and tells the user to shrink from Windows (or Lumen Setup does it). Welcome's import unlocks the drive with the recovery key (`cryptsetup` supports BitLocker) and shows where to find that key | ⚠️ spec says "resize NTFS", which fails on BitLocker; ➕ |
| Windows Fast Startup leaves the Windows drive locked | The drive mounts read-only or not at all | Detect it, explain it, link to the one setting to turn off | ➕ |
| Clock is wrong after switching between Windows and Lumen | Windows keeps the hardware clock in local time, Linux in UTC | Lumen Setup sets Windows to UTC; Health check catches a mismatch | ➕ |
| Windows updates sometimes reset the boot order | The Lumen boot entry disappears | Health check detects the missing boot entry and restores it | ➕ |
| Secure Boot certificate change | Microsoft's 2011 UEFI CA expired in June 2026. A PC whose firmware lacks the 2023 CA can't boot a shim signed only with the new key | Hardware check reads the firmware's trusted keys and, if the 2023 CA is missing, tells the user to run Windows Update or a firmware update *before* erasing Windows | ➕ |
| Bringing files across | Manual copying | Welcome step 7 imports Documents, Pictures, Music and bookmarks | ✅ |
| Bringing apps across | Users rebuild their app list by memory | Welcome reads the programs installed on the Windows drive and shows, for each one: Lumen version available / runs as a Windows app / use this alternative | ➕ |
| Familiar shortcuts | Vary by desktop | Windows-style shortcuts (Super+E, Super+L, Super+V, Super+., Super+Shift+S) | ✅ |
| Familiar layout | Top bar plus dock feels like a Mac | Optional "Familiar" layout in Welcome: bottom taskbar-style dock with a Start-style launcher. Owner to decide | ➕ (owner's call) |

## 4. Hardware and drivers

| Gap | Linux today | Lumen plan | Status |
| --- | --- | --- | --- |
| NVIDIA | Proprietary driver is fiddly, breaks Secure Boot | Signed NVIDIA image variant | ✅ |
| Hardware check before install | Rare | Live-USB report against `hardware.json` | ✅ |
| Battery life: hibernation | With Secure Boot on, kernel lockdown blocks hibernation by design (the resume image can't be verified). An upstream opt-in was only proposed in July 2026 | Don't promise suspend-then-hibernate. Use suspend with tuned power profiles, a safe shutdown at critical battery, and turn hibernation on only if a verified upstream method lands. Never turn off lockdown or Secure Boot to get it | ⚠️ spec promises suspend-then-hibernate |
| Peripheral vendor apps (RGB lighting, gaming mice, Logitech devices) | Windows-only vendor apps | Image ships the needed device rules and daemons; Store offers OpenRGB, Piper and Solaar in Essentials | ➕ |
| Drivers outside the kernel on an image-based system (DisplayLink docks, some Wi-Fi and printers) | Users can't install driver packages on a read-only system | Build extra drivers as signed kernel modules in CI (same pipeline as NVIDIA). Printers: driverless IPP plus OpenPrinting Printer Applications. Scanners: `sane-airscan` | 🟡 printers ✅; ➕ others |
| Media codecs and hardware video decoding | Fedora strips patent-encumbered codecs; hardware H.264/HEVC decoding is off for AMD in Fedora's Mesa, which costs battery on video | Flatpak apps get codecs from Flathub's codec extensions. Whether the system layer adds full codecs (for example RPM Fusion's builds) is a legal choice for the owner, recorded in an ADR | ➕ 👤 decision |
| Touchscreens and 2-in-1s | Works, rough edges | On-screen keyboard and auto-rotate on by default on touch devices (pen input already in spec) | 🟡 |
| Windows Hello face unlock | No mature, secure option | Fingerprint only for now | ⛔ |
| Snapdragon (ARM) laptops | Upstream support still maturing | Later target | ✅ (later) |

## 5. Everyday expectations

| Gap | Linux today | Lumen plan | Status |
| --- | --- | --- | --- |
| 4K Netflix, Disney+ and similar | Streaming services limit Linux browsers to lower resolutions (DRM) | Say so in the FAQ | ⛔ |
| OneDrive | No official client | An open-source OneDrive client in the Store (pick in step 7.1); Google via KDE online accounts | 🟡 |
| iCloud and iPhone | No official client; KDE Connect is limited on iPhone | Web access; KDE Connect for Android | ⛔ |
| Work VPNs (Cisco, GlobalProtect, Fortinet) | Need extra NetworkManager plugins | Ship OpenConnect plugins; Settings imports these alongside WireGuard and OpenVPN | ➕ |
| "Reset this PC" | No equivalent | Settings: "Reset Lumen", either keeping files or erasing everything | 🟡 spec has "reset to defaults"; ➕ |
| Remote help from a friend (like Quick Assist) | Possible but technical | "Get help from a friend" using Plasma's built-in remote desktop, behind a visible indicator and a one-time code | ➕ |
| Parental controls | Little on KDE | Age-rated app filtering and per-user app limits | ➕ after v0.1 |
| Voice typing | Not built in | Local-only dictation (no cloud, no telemetry) | ➕ after v0.1 |
| Work and school sign-in (Active Directory, Entra ID), device management | Possible but uncommon | Consumer focus for v1; revisit later | ⛔ for v1 |
| Screen reader parity | Orca is behind NVDA and JAWS | Orca tests per spec | 🟡 |
| Built-in AI assistant (Windows has Copilot) | None | Owner to decide; if added, local-first and opt-in | ❓ owner's call |
| Preinstalled on PCs in shops | OEM deals | Business, not engineering | ⛔ |

## Data sources for compatibility ratings

| Source | What it gives | Licence | Notes |
| --- | --- | --- | --- |
| Lumen CI and maintainers | Automated install-and-launch tests, hand-written recipes | Ours | Primary source; every entry records how and when it was last tested |
| ProtonDB report exports | Game reports keyed by Steam App ID | ODbL 1.0 + DbCL ([announcement](https://protondb.com/news/report-exports-odbl)) | ODbL needs attribution and share-alike, so the Lumen database should be published under ODbL too. Confirm the export repository is still updated |
| AreWeAntiCheatYet | Anti-cheat status per game | Listed as MIT on third-party sites ([repo](https://github.com/AreWeAntiCheatYet/AreWeAntiCheatYet)) | Confirm the LICENSE file before use |
| WineHQ AppDB | App reports | Not checked | Check licence and current status; never scrape |

Privacy: the whole database downloads like AppStream metadata and lookups happen offline. Lumen never sends "this user is installing X" anywhere. A "Report how it went" button can come later, as an explicit, per-report opt-in.
