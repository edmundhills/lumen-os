# Lumen OS architecture

Status: part 1 of 2, draft for the owner's review (2026-10-27), written against the spec as amended by [ADR 0001](decisions/0001-compete-with-windows.md). Part 1 covers the components and how they talk to each other. Part 2 (build flow and dependency graph) is step 0.2.

[docs/spec.md](spec.md) is the source of truth. This document turns it into concrete names, paths and interfaces. Where the spec leaves something open, this document proposes an answer and marks it **Proposed**. Each proposal gets an ADR in `docs/decisions/` when the step that builds it starts. Where the spec looks technically wrong, it is marked ⚠️ and listed in [section 8](#8-spec-problems-and-open-questions).

The interface sketches below (methods, properties, signals) show intent, not the final API. The step that builds each part fixes its exact shape.

## 1. The big picture

![Lumen OS stack: 6 layers](images/architecture.png)

| Layer | Contents | Made by |
| --- | --- | --- |
| Apps | Settings, Store, Welcome, Backup, hardware report, "Open Windows app"; Flatpak apps, including Bottles for Windows apps | Lumen; Flathub |
| Shell | lumen-shell (Plasma shell package `org.lumen.desktop`) | Lumen, on Plasma backends |
| Compositor | KWin 6 + the lumen-glass effect | KDE + Lumen |
| Services | lumen-updated, lumen-health, lumen-hwd, lumen-settingsd, lumen-backupd | Lumen |
| Base image | systemd, SELinux, NetworkManager, PipeWire, Flatpak, bootc; read-only `/usr` | Fedora (Kinoite) |
| Kernel and firmware | Linux, Mesa, firmware, Secure Boot, LUKS2 + TPM2 | Fedora |

Three things cut across the layers: the **design tokens** (one `tokens.json`, exported at build time to every toolkit and to the glass shader), the **`lumen` CLI** (it calls the same D-Bus services as the GUI) and the **compatibility database** (one signed file of Windows app ratings, read offline through the `lumen-compat` crate by the Store, the "Open Windows app" dialog, Welcome and the CLI).

Three rules shape every interface in this document:

1. **One owner per job.** Each piece of state has exactly one owner. Only lumen-updated runs bootc; only lumen-settingsd writes `~/.config/lumen/`. Everything else asks the owner over D-Bus.
2. **The GUI and the CLI share one path.** Anything the Settings app can do, `lumen` does with the same D-Bus call, so they can never disagree (spec, "lumen CLI and services").
3. **Reuse upstream interfaces.** Where KDE or freedesktop.org already has a D-Bus API or Wayland protocol, Lumen uses it instead of inventing one.

## 2. Conventions

### D-Bus

- Bus name, object path and interface share one versioned name, freedesktop.org style: bus name `org.lumen.Updates1`, object path `/org/lumen/Updates1`, interface `org.lumen.Updates1`. A breaking change gets a new version (`Updates2`); the old one stays for one Fedora release.
- **Proposed:** the interface XML files are the contract and live in `services/interfaces/` (step 5.1). Rust services implement them with zbus, the CLI uses a shared Rust crate, and the Qt apps generate their proxies from the same XML with `qdbusxml2cpp`.
- Services are D-Bus activated (started on first call) and run as systemd units with `Type=dbus`.
- Errors are named D-Bus errors (`org.lumen.Error.NotAuthorized`, `.Busy`, `.InvalidValue` and so on) carrying a plain-English, translated message that the GUI can show as it is.
- **Proposed:** long jobs return at once with a job object path, send `Progress` signals and end with `Finished(success, message)`.
- Lumen's D-Bus APIs are for Lumen components only. Flatpak apps can't reach them (Flatpak filters the buses); they get Lumen's look and settings through portals.
- System services never call into a user session. They emit signals, and session components (mostly the shell) listen and react. Session components call system services, never the other way round.

### Privilege

- Every privileged call on a system service is checked with polkit. Action IDs are `org.lumen.<service>.<action>`, for example `org.lumen.updates.rollback`. The default is `auth_admin_keep`: the admin password, remembered for 5 minutes (polkit's own timeout, which is what the spec asks for). Read-only calls need no password.
- Session services run as the user, need no polkit and can only touch that user's data.
- Units use systemd hardening (`NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, `PrivateTmp`, syscall filters), loosened only where a tool needs it. For example, bootc has to write `/sysroot` and `/boot`. The per-service template is part of step 5.1.

### Files

| Path | Writable | Owner | Contents |
| --- | --- | --- | --- |
| `/usr/bin/lumen` | No | image | The CLI |
| `/usr/libexec/lumen-*` | No | image | Service binaries |
| `/usr/share/lumen/` | No | image | Data that ships with the image: `tokens/tokens.json`, `settings/schema.toml`, `hardware.json`, `app-aliases.json`, `compat/windows-apps.json` |
| Image defaults for `/etc` | No | image | ⚠️ The spec says `/usr/etc`, which `bootc container lint` rejects. Decided at step 1.3 |
| `/etc/lumen/` | Yes | system services | **Proposed:** machine-wide Lumen settings (see [Q7](#8-spec-problems-and-open-questions)) |
| `/var/lib/lumen/` | Yes | system services | `glass-tier`, `updates/` (history, held versions), `health/` (logs), `compat/` (newer signed compatibility database) |
| `~/.config/lumen/*.toml` | Yes | lumen-settingsd | The user's Lumen settings |
| `~/.local/state/lumen/` | Yes | session services | Per-user state, such as backup results |

### App IDs

Lumen's apps use `org.lumen.Settings`, `org.lumen.Store`, `org.lumen.Welcome`, `org.lumen.Backup`, `org.lumen.HardwareReport` and `org.lumen.WindowsApp`. On Wayland the app ID is how KWin and the dock match a window to its app, so it must equal the desktop file name.

## 3. Component catalogue

| Component | Repo folder | Language | Runs as | Ships as |
| --- | --- | --- | --- | --- |
| Base image | `image/` | Containerfile, TOML | n/a | OCI image `ghcr.io/<org>/lumen:<channel>` and variants |
| lumen-glass | `glass/` | C++, GLSL | Inside `kwin_wayland` (user session) | RPM, built in a Containerfile stage |
| Design tokens and exporters | `design/tokens/` | JSON plus exporters | Build time only | Files in the image |
| lumen-shell | `shell/` | QML, C++ QML plugins, KWin scripts (JS) | Inside `plasmashell` (user session) | RPM, built in a Containerfile stage |
| lumen-updated | `services/updated` | Rust | System, root | RPM |
| lumen-health | `services/health` | Rust | System | RPM |
| lumen-hwd | `services/hwd` | Rust | System | RPM |
| lumen-settingsd | `services/settingsd` | Rust | User session | RPM |
| lumen-backupd | `services/backupd` | Rust | User session | RPM |
| `lumen` CLI | `cli/` | Rust | User | RPM |
| Settings | `apps/settings` | C++/QML | User | RPM |
| Store | `apps/store` | C++/QML | User | RPM |
| Welcome | `apps/welcome` | C++/QML | First-boot session, then user | RPM |
| Backup | `apps/backup` | C++/QML | User | RPM |
| "Open Windows app" dialog | `apps/windows-app` | C++/QML | User | RPM |
| Hardware report | Not in the CLAUDE.md layout yet; **Proposed** `apps/hwreport` | C++/QML | Live session | RPM |
| Compatibility database | `compat/` | JSON, JSON schema | Data | `/usr/share/lumen/compat/`, refreshed by lumen-updated |
| lumen-compat | `compat/` | Rust library | Inside its callers | RPM |
| Lumen Setup for Windows | `windows-setup/` | C++/Qt (fork of Fedora Media Writer) | Windows | Code-signed Windows program, built in CI |
| Installer | `installer/` | Kickstart, theme | Install media | Part of the ISO |
| Hardware database | `hardware/hardware.json` | JSON | Data | `/usr/share/lumen/hardware.json` |

Lumen's own apps ship as RPMs in the image, not as Flatpaks. They are part of the OS: they need the system services and must match the image version, like KDE's System Settings does today. Third-party apps are Flatpaks only, including Bottles, which runs Windows apps.

Where each RPM gets built (COPR, CI or a Containerfile stage) is part 2.

## 4. Components

### 4.1 Base image

Kinoite pinned by digest, managed by bootc. Lumen adds packages from `image/packages.toml`, the overlay and systemd presets.

Some stock parts compete with a Lumen owner, so the image turns them off:

| Upstream part | Why it goes | Replaced by |
| --- | --- | --- |
| Discover and its update notifier | A second app store and update prompt | Store and lumen-updated |
| `rpm-ostreed-automatic.timer`, `bootc-fetch-apply-updates.timer` (masked) | Second updaters. The bootc one applies updates and reboots without asking | lumen-updated |
| `rpm-ostree-countme.timer` (masked) | Sends a weekly anonymous count to Fedora; the spec says no telemetry | Nothing |
| KWin's `blur` and `contrast` effects | lumen-glass serves the same Wayland global (`org_kde_kwin_blur_manager`). Two effects can't both own it | lumen-glass |
| Stock Plasma panels and default plasmoids | Spec | lumen-shell |

Talks to: the image registry (`ghcr.io`) through bootc, with signatures checked against `/etc/containers/policy.json` and the sigstore settings in `/etc/containers/registries.d/` (step 1.7).

### 4.2 lumen-glass (compositor effect)

A KWin effect plugin loaded by `kwin_wayland` in the user's session. Built against that image's exact KWin (CLAUDE.md build rule).

**Offers**

- Wayland:
  - `org_kde_kwin_blur_manager`: the blur region, inherited from the stock blur effect. Qt apps reach it with `KWindowEffects::enableBlurBehind`.
  - `lumen_glass_manager_v1`: **Proposed** small Lumen protocol that lets a surface name its glass role (`bar`, `dock`, `menu`, `popover`, `notification`, `sidebar`, `titlebar`). See [Q6](#8-spec-problems-and-open-questions).
  - `ext_background_effect_manager_v1`: later, once KWin supports it (spec).
- D-Bus, **Proposed**: `org.lumen.Glass1` on the session bus, owned by the KWin process, path `/org/lumen/Glass1`.
  - Properties: `ActiveTier`, `BenchmarkTier`, `TierReason` (for example "Battery saver is on").
  - Method: `Reload()` re-reads tokens and settings (mainly for tests).
  - Signal: `TierChanged(tier, reason)`.
  - The Settings Appearance page and the session tests read the effective tier here.

**Uses**

- `/usr/share/lumen/tokens/tokens.json`: glass presets per role, spring presets.
- `/var/lib/lumen/glass-tier`: the first-boot benchmark result.
- `org.lumen.Settings1` `Changed` signal for `appearance.*`, `glass.*` and `accessibility.*` keys: theme, accent, tier override, Reduce Transparency, Reduce Motion.
- The power profile on the system bus (`org.freedesktop.UPower.PowerProfiles`, `ActiveProfile`), to drop a tier in power-saver mode.

**How a window gets its role**

1. The role the client set through `lumen_glass_manager_v1`. Lumen's shell and apps always set one.
2. Otherwise, from the window type KWin already knows: menus get `menu`, applet popups and OSDs get `popover`, notifications get `notification`, anything else that asked for blur gets `sidebar`.
3. The title bar area gets `titlebar` directly, because the window decoration also runs inside KWin.
4. A window that asks for nothing gets rounded corners and a soft shadow only (spec).

**How the tier is chosen.** The effective tier is the lowest of:

- the benchmark result, or the user's override `glass.tier` if it isn't `auto`;
- one tier lower while the power profile is power-saver;
- Solid when Reduce Transparency is on, the session is remote, or KWin is rendering in software.

Reduce Motion turns off morphing and spring animations whatever the tier.

**Benchmark, Proposed** (decided at step 3.11): a system oneshot, `lumen-glass-benchmark.service`, runs before the first login, and again when the GPU changes. It renders the 8-surface test scene off-screen on the GPU's render node, at the main display's native resolution, with the same shaders, and writes `/var/lib/lumen/glass-tier`. This keeps the result in system state, where the spec puts it, and out of the user's first session.

### 4.3 Design tokens

`design/tokens/tokens.json` (checked by a JSON schema) is exported during the image build:

| Output | Installed at | Read by |
| --- | --- | --- |
| QML module `org.lumen.style` | Qt's QML import path | lumen-shell, Lumen apps |
| `tokens.json` itself | `/usr/share/lumen/tokens/` | lumen-glass, lumen-settingsd |
| KDE colour schemes | `/usr/share/color-schemes/` | Qt and KDE apps (through `kdeglobals`) |
| Kvantum theme | `/usr/share/Kvantum/Lumen/` | Qt apps |
| GTK 4 / libadwaita CSS | A template in `/usr/share/lumen/gtk-4.0/`; lumen-settingsd writes the user's copy to `~/.config/gtk-4.0/gtk.css` | GTK 4 apps |
| GTK 3 theme | `/usr/share/themes/Lumen/` | GTK 3 apps |
| Icon and cursor theme config | `/usr/share/icons/` | All apps |
| Window decoration (KDecoration plugin) and global theme `org.lumen.desktop` | KWin's decoration plugin path, `/usr/share/plasma/look-and-feel/` | KWin, Plasma |

Accent and light/dark are user choices, so they are applied at run time by lumen-settingsd ([flow 5.1](#51-changing-a-setting)).

Flatpak apps can't see host theme files. They get light/dark, accent and contrast from the Settings portal (`org.freedesktop.appearance`, served by xdg-desktop-portal-kde from `kdeglobals`). Full theming inside Flatpaks needs more: GTK 3 Flatpaks need the theme as a Flatpak extension (`org.gtk.Gtk3theme.Lumen`), and GTK 4 Flatpaks only see `~/.config/gtk-4.0` with a filesystem override. This goes in the risk register (step 0.3); Phase 2 decides how far to go.

### 4.4 lumen-shell

`plasmashell` loads the shell package `org.lumen.desktop` (how it is selected is step 4.1). The UI is QML; small C++ QML plugins do what QML can't.

| Part | Talks to |
| --- | --- |
| Top bar | Tray (StatusNotifierItem, `org.kde.StatusNotifierWatcher`), NetworkManager, PipeWire (through plasma-pa), UPower, MPRIS (`org.mpris.MediaPlayer2.*`), AccountsService |
| Camera, mic and location indicators | PipeWire streams; GeoClue2 (`org.freedesktop.GeoClue2`, `InUse`). A program that opens `/dev/video*` directly, bypassing PipeWire, isn't seen: goes in the risk register |
| Dock | TaskManager library (Wayland `org_kde_plasma_window_management`), KService for pins, KActivities for recent files, launcher API (`com.canonical.Unity.LauncherEntry`) for progress and badges |
| Command palette | KRunner library in-process, plus D-Bus runners (`org.kde.krunner1`); Baloo for files; a Lumen runner for Settings pages (deep links) |
| Quick settings | NetworkManager, BlueZ (BluezQt), power profiles, KWin Night Light (`org.kde.KWin.NightLight`), PowerDevil for brightness (`org.kde.Solid.PowerManagement`), plasma-pa, lumen-settingsd (dark mode) |
| Notification centre, focus modes | Plasma's notification server (it owns `org.freedesktop.Notifications`); focus-mode settings in lumen-settingsd |
| Overview, tiling, auto-tile | KWin Overview effect (restyled), KWin custom tiles, KWin script `lumen-autotile` (configured through `kwinrc`) |
| Lock screen, login screen, OSDs | KScreenLocker theme, SDDM theme, Plasma OSD service (`org.kde.osdService`) |
| Shortcuts | KGlobalAccel (`org.kde.kglobalaccel`); Super on its own is a KWin modifier-only shortcut |
| Glass | `lumen_glass_manager_v1` to set each surface's role; `org.lumen.style` for tokens |

**Proposed: the shell is the session-side listener for the system services.** System services can't post desktop notifications (that API lives on each user's session bus), and the shell already runs in every session. So the shell watches `org.lumen.Updates1` for `UpdateReady` and shows the spec's single "Update ready" notification with Restart Now, Tonight and Later. It does the same for Health problems and failed backups. If the shell isn't running, the Settings app shows the same state when it opens.

**Proposed: the shell reads its own settings** (dock size, auto-hide, hot corners, top bar options) from lumen-settingsd (`dock.*`, `shell.*`) and reacts to `Changed`, rather than keeping them only in Plasma's applet config files. That way `lumen settings` can change them.

### 4.5 Services

| Service | Bus | Runs as | Started by | State |
| --- | --- | --- | --- | --- |
| lumen-updated | system | root | D-Bus activation, `lumen-updated.timer` | `/var/lib/lumen/updates/` |
| lumen-health | system | own system user, plus polkit for fixes | D-Bus activation | `/var/lib/lumen/health/` |
| lumen-hwd | system | own system user, plus polkit for changes | D-Bus activation | none |
| lumen-settingsd | session | user | D-Bus activation | `~/.config/lumen/` |
| lumen-backupd | session | user | D-Bus activation, user timers | `~/.local/state/lumen/backup/` |

Whether lumen-health and lumen-hwd can really run as their own unprivileged users, or need root for some reads and fixes, is checked at steps 5.8 to 5.10.

#### lumen-updated: `org.lumen.Updates1`

Owns OS image updates (bootc), Flatpaks in the system installation, firmware, compatibility database refreshes, rollback, the post-boot health check and the update history.

- **Uses:** the `bootc` command (`status --json`, `upgrade --check`, `upgrade`, `rollback`, `switch`; bootc has no D-Bus API); libflatpak; fwupd (`org.freedesktop.fwupd`); NetworkManager (`Metered`, state changes); UPower (`OnBattery`, charge level); systemd (`org.freedesktop.systemd1`); logind (`org.freedesktop.login1`) for restarts.
- **Started by:** the timer every 6 hours, and a NetworkManager "connected" signal when the last check is over 24 hours old.
- **Sketch:**
  - Properties: `State`, `LastCheck`, `Channel`, `AutoUpdate`, `Staged` (version and contents), `PendingSince`.
  - Methods: `Check()`, `Apply()`, `ScheduleRestart(when)` (now, tonight or later), `ListHistory()`, `Rollback()`, `SwitchTo(version)`, `SwitchVariant(variant)`, `SetChannel(channel)`, `InstallFirmware(devices)`.
  - Signals: `UpdateReady(version, needsRestart)`, `BootHealthResult(ok, details)`.
- **History:** bootc keeps only the booted, staged and rollback deployments, but Settings > Updates > History lists every installed version. So lumen-updated keeps its own log in `/var/lib/lumen/updates/`.
- **Proposed: compatibility database refresh.** lumen-updated downloads the newer database, checks its signature, and only then replaces `/var/lib/lumen/compat/windows-apps.json`. Readers trust that file because only lumen-updated (root) can write it, so they never verify, download or look anything up online. Where the file is published is decided at step 7.3.
- **Proposed: going back to an older version** needs CI to keep immutable dated tags (for example `stable-20261027`) next to the moving `stable` tag (release train, step 9.1). After a user goes back, the version they left is "held" so the next check doesn't offer it straight away; the hold lifts when a newer version appears.
- **Low priority:** downloads run in a transient unit with idle CPU and I/O scheduling.
- **Post-boot health check:** ⚠️ see [Q3](#8-spec-problems-and-open-questions).

#### lumen-health: `org.lumen.Health1`

| Check | Reads from |
| --- | --- |
| Disk below 10% free | Free space on `/`, `/var`, `/home` |
| Failed systemd units | `org.freedesktop.systemd1` |
| Update pending more than 14 days | `org.lumen.Updates1` `PendingSince` |
| Firewall off | firewalld (`org.fedoraproject.FirewallD1`) |
| Battery health below 80% | UPower (full charge against design capacity) |
| Missing driver or firmware | `org.lumen.Hardware1`, fwupd |
| SMART or NVMe disk errors | UDisks2 (`org.freedesktop.UDisks2`) |
| Broken Flatpak or permissions | `flatpak repair --dry-run` |
| Backup not run in 7 days | `org.lumen.Backup1` (per user, see below) |
| Time not synced | timedated (`org.freedesktop.timedate1`, `NTPSynchronized`) |
| Windows Fast Startup left the Windows drive locked | The Windows partition's hibernation state (UDisks2) |
| Clock differs from Windows | timedated (`LocalRTC`) and the Windows clock setting, read from the Windows drive |
| Lumen boot entry missing | EFI boot entries and boot order (EFI variables) |
| Firmware lacks the Microsoft UEFI CA 2023 | `org.lumen.Hardware1` |

The last four are the dual-boot checks (step 7.10); they only run when a Windows install is present.

- **Sketch:** `RunChecks()` returns a list of (check, status, plain-English message, fix); `ApplyFix(fix)`; `Reset(mode)` for "Reset Lumen" (keep files or erase everything; how "erase everything" works on a bootc system is worked out at step 5.22); property `LastResults`; signal `ResultsChanged`.
- **Proposed: per-user checks run in the session.** Two checks are about one user's things: backup age, and caches and rootless containers in the storage cleaner. A system service can't see a user's session bus or (with `ProtectHome`) their home folder. So lumen-health runs the system checks, and the Settings app and `lumen health` add the per-user ones from lumen-backupd and the user's own disk use.

#### lumen-hwd: `org.lumen.Hardware1`

- **Uses:** sysfs and the hwdata ID lists (what `lspci` and `lsusb` read), fwupd, EFI variables (Secure Boot state, and the `db` certificate list for the Microsoft UEFI CA 2023 check), the TPM (`/sys/class/tpm`), fprintd (`net.reactivated.Fprint`), NetworkManager (Wi-Fi), V4L2 (webcam), ALSA (audio devices), `/sys/power` (sleep support), UPower.
- **Compares with** `/usr/share/lumen/hardware.json`: known good, known issues with workarounds, known broken.
- **Sketch:** `Report()` returns JSON with the same schema as `lumen hw report --json`; `DriverStatus()`; `SwitchToNvidiaImage()` explains MOK enrolment, then calls `org.lumen.Updates1.SwitchVariant("nvidia")`, because only lumen-updated runs bootc. Signal: `DevicesChanged`.
- Also runs in the live session for the hardware report. ⚠️ See [Q4](#8-spec-problems-and-open-questions).

#### lumen-settingsd: `org.lumen.Settings1`

- **Stores** `~/.config/lumen/<namespace>.toml`: the key `appearance.theme` is `theme` in `appearance.toml`.
- **Proposed: a schema** in `/usr/share/lumen/settings/schema.toml` gives each key its type, default, allowed values and owner. Unknown keys are refused, so a typo fails loudly. Defaults come from the schema, so the files hold only what the user changed.
- **Sketch:** `Get(key)`, `Set(key, value)`, `List(prefix)`, `Reset(key)`, `Export()`, `Import(toml)`; signal `Changed(key, value)`.
- Writes are atomic (temporary file, then rename). A file watch notices hand edits and emits `Changed`, so "every setting is also a config file" works in both directions.
- **Bridges.** Some keys must also reach upstream settings stores:

| Lumen key | Also applied to |
| --- | --- |
| `appearance.theme`, `appearance.accent` | KDE colour scheme and accent in `kdeglobals` (xdg-desktop-portal-kde then tells Flatpak and GTK apps); regenerates `~/.config/gtk-4.0/gtk.css`; GTK 3 settings |
| `accessibility.reduce_motion` | KDE animation speed, GTK `gtk-enable-animations` |
| `dock.*`, `shell.*`, `glass.*` | Nothing: Lumen components read them directly |
| `updates.*` | Forwarded to `org.lumen.Updates1` (machine-wide, see [Q7](#8-spec-problems-and-open-questions)) |

Settings that already have an upstream owner (Wi-Fi networks, displays, Bluetooth pairings) stay with that owner, and the Settings app talks to it directly. Whether `lumen settings` should also wrap them is [Q9](#8-spec-problems-and-open-questions).

#### lumen-backupd: `org.lumen.Backup1`

- Runs restic as the user, so a backup holds what that user can read.
- **Destinations:** external drives (mounted through UDisks2), SMB/NFS shares, S3-compatible storage (restic supports S3 natively). How shares are reached without root is decided at step 6.8.
- **Secrets:** repository passwords live in the Secret Service (`org.freedesktop.secrets`, provided by KWallet), never in config files.
- **Settings:** schedule, retention and exclusions are `backup.*` keys in lumen-settingsd. The destination list and secrets belong to lumen-backupd.
- **Schedules:** systemd user timers that call lumen-backupd.
- **Sketch:** `ListDestinations()`, `AddDestination(...)`, `RunNow(destination)`, `ListSnapshots(destination)`, `Restore(snapshot, paths, target)`; property `LastSuccess`; signals `JobProgress`, `JobFinished`.

"Previous versions" in Files is a separate thing: it reads snapper's hourly `/home` snapshots, not restic (step 6.9).

### 4.6 `lumen` CLI

`/usr/bin/lumen`, Rust with clap. Each command maps straight onto D-Bus calls:

| Command | Calls |
| --- | --- |
| `lumen update`, `lumen rollback` | `org.lumen.Updates1` |
| `lumen settings` | `org.lumen.Settings1` |
| `lumen health` | `org.lumen.Health1`, plus `org.lumen.Backup1` for the per-user checks |
| `lumen hw report` | `org.lumen.Hardware1` |
| `lumen app install / remove / list / search` | libflatpak and `app-aliases.json`, the same as the Store (see 4.7) |
| `lumen app check <file>`, `lumen app list --windows` | lumen-compat and Bottles, the same as the "Open Windows app" dialog (see 4.9) |
| `lumen dev enable` | toolbox and distrobox as the user; turning on SSH goes through `org.freedesktop.systemd1` and firewalld, under polkit |
| `lumen backup` | `org.lumen.Backup1` |
| `lumen glass tier` | `org.lumen.Settings1`, key `glass.tier` (lumen-glass reacts to the change) |

- `--json` prints the same structures the D-Bus calls return. Tests use it to check that the GUI and CLI agree.
- Completions for bash, zsh and fish are generated by clap and installed in the standard paths.
- Calls allow interactive authorisation, so polkit can ask for the password. Without a graphical session (over SSH), `lumen` starts polkit's text agent, `pkttyagent`.

### 4.7 Apps

| App | Talks to |
| --- | --- |
| Settings | lumen-settingsd, all system services, `org.lumen.Glass1`, KDE settings backends (KScreen, plasma-nm, BlueZ, plasma-pa, PowerDevil), AccountsService, firewalld, the Flatpak permission store, Bottles (Apps → Windows apps), Plasma's remote desktop server KRdp ("Get help from a friend", ⚠️ [Q5](#8-spec-problems-and-open-questions)). Opens on deep links `lumen-settings://<page>[/<section>]` (a URL scheme handler in its desktop file); the palette and Health fixes use them |
| Store | libflatpak (system installation; Flatpak's own system helper does the privileged part under polkit), AppStream metadata, Flathub, `app-aliases.json`, lumen-compat (ratings next to Windows-name searches, the Windows alternatives collection, anti-cheat status). Installs websites as apps ([Q11](#8-spec-problems-and-open-questions)) |
| Welcome | First-boot part: localed (`org.freedesktop.locale1`), NetworkManager, AccountsService, TPM2 enrolment (see [Q8](#8-spec-problems-and-open-questions)). User part: lumen-settingsd, the Store backend, UDisks2 (import drive; unlocks a BitLocker drive with its recovery key), lumen-compat ("Your Windows apps"), lumen-backupd (offer backup when a second drive exists) |
| Backup | lumen-backupd |
| Hardware report | lumen-hwd |
| "Open Windows app" | lumen-compat, Bottles (see 4.9) |

There is no Lumen app daemon. Flatpak's system helper already is the service, so the Store and `lumen app` stay in step by both using libflatpak and the same alias file. Once an app is installed, lumen-updated keeps it up to date.

### 4.8 Installer

Anaconda from bootc-image-builder's `anaconda-iso`, with Lumen's kickstart and theme from `installer/`. bootc-image-builder adds the `ostreecontainer` kickstart command that writes the image to disk. After install, the system must track `ghcr.io/<org>/lumen:<channel>` and enforce the signature policy from its first update. "Install alongside Windows" uses free space made from inside Windows and never resizes a BitLocker volume (spec). ⚠️ See [Q4](#8-spec-problems-and-open-questions) for what this ISO can't do.

### 4.9 Windows apps and switching

**Compatibility database.** `compat/windows-apps.json` (checked against its JSON schema in CI, published under ODbL 1.0). It ships in the image at `/usr/share/lumen/compat/`, and lumen-updated keeps a newer signed copy in `/var/lib/lumen/compat/` between image updates. Readers use whichever copy is newer. A lookup never touches the network.

**lumen-compat.** A Rust crate that identifies a file (PE version info, installer type, SHA-256, Steam App ID) and looks it up. The spec makes it the only lookup path for the Store, the dialog, Welcome and the CLI, so they can't disagree. The CLI links it directly. **Proposed:** the C++ apps call it through a small C interface rather than through a daemon. A lookup is a local file read, so a service would only add a moving part ([Q10](#8-spec-problems-and-open-questions)).

**"Open Windows app" dialog** (`org.lumen.WindowsApp`):

- It is the default app for `.exe` and `.msi` files. Until it ships (step 7.5), those files open in Bottles directly (step 1.13).
- It reads the file through lumen-compat and shows the rating, the reason, alternatives and anti-cheat status.
- Install creates the app's own bottle with its recipe and runs the installer, by driving Bottles through its command-line tool (`bottles-cli`, run inside the Bottles Flatpak). The installer file reaches the sandbox through the document portal, so Bottles' permissions never widen. Whether `bottles-cli` can apply every recipe field (dependencies, DLL overrides, environment variables) is checked at step 7.5.
- Nothing installs until the user presses a button (spec).

**Bottles** (Flathub) runs each Windows app in its own bottle inside its Flatpak sandbox, with Bottles' default permissions (no home folder beyond Downloads). Settings → Apps → Windows apps and `lumen app list --windows` list the bottles; removing an app deletes its bottle. Games use Steam with Proton, Heroic or Lutris instead.

**Lumen Setup for Windows** runs on Windows before Lumen is on the machine, so it shares data with Lumen, not D-Bus:

- `hardware.json`, the same file lumen-hwd uses. **Proposed:** the matching rules live in one Rust crate that both lumen-hwd and Setup link, for the same reason as lumen-compat ([Q10](#8-spec-problems-and-open-questions)).
- Windows' own tools and APIs for BitLocker, Fast Startup, Secure Boot and the UEFI CA 2023 check, shrinking the Windows partition and setting the Windows clock to UTC. Every change to Windows has its own confirm button (spec).
- Lumen's release files: it downloads the ISO with its checksum and signature over HTTPS, verifies them and writes the USB drive.

## 5. Key flows

### 5.1 Changing a setting

1. The user turns on dark mode in Quick settings or in Settings, or runs `lumen settings set appearance.theme dark`. All three call `org.lumen.Settings1.Set("appearance.theme", "dark")`.
2. lumen-settingsd checks the value against the schema and writes `~/.config/lumen/appearance.toml`.
3. The bridge applies the KDE colour scheme. xdg-desktop-portal-kde reports the new `color-scheme` to Flatpak and GTK apps; lumen-settingsd regenerates the GTK 4 CSS.
4. lumen-settingsd emits `Changed`. lumen-glass flips its tint direction; the shell and Lumen apps restyle. Nothing polls.

### 5.2 Update, restart and recovery

1. The timer (or a reconnect after more than 24 hours) starts lumen-updated.
2. It checks the OS image (`bootc upgrade --check`), then Flatpaks, then firmware.
3. On a metered network, or on battery below 20%, it waits.
4. It downloads at idle priority. bootc checks the image signature against `/etc/containers/policy.json` and stages it. Flatpaks of apps that aren't running are applied; firmware waits for consent.
5. It emits `UpdateReady`. The shell shows one notification: Restart Now, Tonight, Later.
6. After the restart, the post-boot health check runs. If it fails twice, the boot loader falls back to the previous deployment and Settings explains what happened. ⚠️ [Q3](#8-spec-problems-and-open-questions).
7. Later, Settings > Updates > History calls `ListHistory()`; "Go back to this version" calls `Rollback()` or `SwitchTo(version)`, and the version left behind is held.

### 5.3 Installing an app

1. The user searches for "Word" in the Store, or runs `lumen app search word`.
2. Both look the name up in `app-aliases.json` and the AppStream data, and suggest LibreOffice and OnlyOffice.
3. The install goes through libflatpak into the system installation; Flatpak's system helper checks polkit.
4. The app's desktop file appears; the dock and palette pick it up through KService.
5. lumen-updated keeps it up to date from then on.

### 5.4 Opening a Windows program

1. The user double-clicks `setup.exe`. The "Open Windows app" dialog opens, because it is the default app for `.exe` files.
2. lumen-compat identifies the file and looks it up in the local database. No network request is made.
3. The dialog shows the rating, the reason, alternatives and, for games, anti-cheat status.
4. When the user presses Install (or Try it for an untested app), the dialog creates a bottle with the app's recipe and runs the installer inside it through Bottles.
5. The app appears in the app menu and runs in its own bottle inside the Bottles sandbox. Removing it deletes the bottle.

## 6. Interface index

### 6.1 D-Bus services Lumen provides

| Name | Bus | Process | Used by |
| --- | --- | --- | --- |
| `org.lumen.Updates1` | system | lumen-updated | Settings, CLI, shell, lumen-health, lumen-hwd, lumen-settingsd |
| `org.lumen.Health1` | system | lumen-health | Settings, CLI, shell |
| `org.lumen.Hardware1` | system | lumen-hwd | Settings, CLI, hardware report, lumen-health |
| `org.lumen.Settings1` | session | lumen-settingsd | Settings, CLI, shell, lumen-glass, lumen-backupd, Welcome |
| `org.lumen.Backup1` | session | lumen-backupd | Backup app, Settings, CLI, shell, Welcome |
| `org.lumen.Glass1` (**Proposed**) | session | `kwin_wayland` (lumen-glass) | Settings, session tests |

Lumen services call each other in one direction only: lumen-health and lumen-hwd call lumen-updated, and lumen-updated calls no other Lumen service. Part 2 draws this as a graph. The Windows-app parts add no D-Bus service: lumen-compat is a library.

### 6.2 Upstream D-Bus services Lumen uses

| Name | Bus | Used by |
| --- | --- | --- |
| `org.freedesktop.systemd1`, `org.freedesktop.login1` | system | lumen-updated, lumen-health, CLI |
| `org.freedesktop.NetworkManager` | system | lumen-updated, shell, Settings, Welcome |
| `org.freedesktop.UPower`, `org.freedesktop.UPower.PowerProfiles` | system | lumen-updated, lumen-health, lumen-glass, shell, Settings |
| `org.freedesktop.fwupd` | system | lumen-updated, lumen-health, lumen-hwd |
| `org.freedesktop.UDisks2` | system | lumen-health, lumen-backupd, Welcome |
| `org.fedoraproject.FirewallD1` | system | lumen-health, Settings, CLI |
| `org.freedesktop.Accounts` | system | Settings, Welcome, shell |
| `org.freedesktop.timedate1`, `org.freedesktop.locale1` | system | lumen-health, Welcome |
| `org.freedesktop.GeoClue2` | system | shell |
| `net.reactivated.Fprint` | system | lumen-hwd, Settings, Welcome |
| `org.freedesktop.Flatpak.SystemHelper` (through libflatpak) | system | Store, CLI, lumen-updated |
| `org.freedesktop.Notifications` | session | shell (serves it), apps |
| `org.freedesktop.secrets` | session | lumen-backupd |
| `org.freedesktop.portal.*` | session | Flatpak apps; the "Open Windows app" dialog (document portal) |
| `org.kde.KWin`, `org.kde.KWin.NightLight`, `org.kde.kglobalaccel`, `org.kde.krunner1`, `org.kde.osdService`, `org.kde.Solid.PowerManagement` | session | shell, Settings |
| `org.kde.StatusNotifierWatcher`, `org.mpris.MediaPlayer2.*`, `com.canonical.Unity.LauncherEntry` | session | shell |

### 6.3 Wayland protocols

| Protocol | Served by | Used by |
| --- | --- | --- |
| `org_kde_kwin_blur_manager` | lumen-glass | shell, Qt apps (`KWindowEffects`) |
| `lumen_glass_manager_v1` (**Proposed**) | lumen-glass | shell, Lumen apps |
| `ext_background_effect_manager_v1` (later) | lumen-glass | Any toolkit that adopts it |
| `org_kde_plasma_shell`, layer shell | KWin | shell (LayerShellQt) |
| `org_kde_plasma_window_management` | KWin | shell (TaskManager) |
| Standard protocols (xdg-shell, fractional scale, screencast through portals) | KWin | All apps |

### 6.4 Connections that leave the machine

| Where to | Protocol | Who | Notes |
| --- | --- | --- | --- |
| `ghcr.io` | OCI registry over HTTPS, cosign signatures | bootc, through lumen-updated | Verified before staging |
| Flathub | HTTPS, signed by Flathub | Flatpak, through the Store and lumen-updated | Metadata fetched anonymously (spec) |
| LVFS | HTTPS, signed metadata | fwupd, through lumen-updated | Firmware waits for consent |
| Compatibility database | HTTPS, signed file | lumen-updated | The same file for everyone. Lookups stay on the machine, so nothing reveals which app a user installs |
| Lumen release files | HTTPS, checksums and signatures | Lumen Setup for Windows | Verified before writing the USB drive |
| Backup destinations | Local disk, SMB, NFS, S3 over HTTPS | restic, through lumen-backupd | Encrypted before it leaves the machine |
| Remote help | RDP | KRdp | Off until the user starts a session; ⚠️ [Q5](#8-spec-problems-and-open-questions) |
| NetworkManager connectivity check | HTTP to Fedora's check URL | NetworkManager | Needed for captive portals. Keep Fedora's or host our own: step 8.2 |
| Crash reports | HTTPS to KDE's crash tracker | DrKonqi | Off unless the user opts in at Welcome |
| Telemetry | None | n/a | `rpm-ostree-countme` masked; KDE's user feedback stays off |

## 7. Trust boundaries

- **Flatpak apps** run in the Flatpak sandbox and get only portals and the permissions they declare. They can't reach Lumen's D-Bus services.
- **Windows programs** run under Wine inside the Bottles Flatpak sandbox, one bottle per app, with no access to the home folder by default.
- **Session components** (shell, apps, CLI, lumen-settingsd, lumen-backupd, lumen-glass inside KWin) run as the user. They ask system services for privileged work; polkit decides.
- **System services** run hardened. Only lumen-updated runs as root. They never call into a user's session.
- **The image** is read-only and signed. Nothing at run time can change `/usr`; changes arrive only as a new signed image.

## 8. Spec problems and open questions

### ⚠️ Spec is technically wrong

| # | Spec says | Problem | Proposal | Affects |
| --- | --- | --- | --- | --- |
| Q1 | GTK apps get glass "via our small GTK module" (lumen-glass spec; step 3.14) | GTK 4 dropped general-purpose loadable modules, so a module can't load into GTK 4 apps at all. Flatpak apps can't load modules from the host either, and the spec makes Flatpak the only way to install apps. In practice the module would only reach GTK 3 apps that ship in the image | Our GTK CSS makes headerbars and sidebars translucent, and lumen-glass puts glass behind the whole window for opted-in GTK app IDs (only the translucent parts show it). A GTK 3 module stays optional for host apps | Step 3.14, Phase 2 visual test |
| Q2 | The package manifest includes both `power-profiles-daemon` and `tuned-ppd` | They can't be installed together. Both provide `ppd-service` and conflict on it (checked in the Fedora 44 repos). Fedora has been moving its desktops to tuned-ppd since Fedora 41 | Keep `tuned-ppd`, drop `power-profiles-daemon`. Both serve the same D-Bus API, so nothing else changes. Confirm which one Kinoite ships at step 1.1 | Steps 1.1, 1.3 |
| Q3 | After an update, the health check must see "shell started" within 2 minutes, and two failures roll back | The shell only starts when someone logs in. After a "Tonight" restart nobody does, so every good update would fail the check and roll back | Mark the boot good on system checks only: SDDM up, network up, no failed critical units. Check the shell at the first login after an update; if it fails, offer to go back instead of doing it automatically. Look at greenboot (Fedora's boot health checks with GRUB fallback) before writing our own | Step 5.6 |
| Q4 | The hardware report runs on the live USB, and the installer is Anaconda WebUI from `anaconda-iso` | bootc-image-builder's `anaconda-iso` boots straight into Anaconda, with no live desktop, so there's nowhere to run the hardware report app. By default it is also an unattended installer that wipes the first disk; interactive choices need a partial kickstart. Which Anaconda UI it uses must be checked | Check at step 1.8. Lumen Setup for Windows already runs the hardware check from Windows (step 7.9), which covers people coming from Windows. For everyone else: a live ISO built from our image (for example Universal Blue's Titanoboa), or drop the live report | Steps 1.8, 6.10, 6.12 |
| Q5 | "Get help from a friend": Plasma remote desktop behind a one-time code (step 5.22a) | KRdp is a plain RDP server with no relay. A friend on another network can't reach it unless the user forwards a port on their router. Windows' Quick Assist works because Microsoft runs a relay | For v0.1, say plainly that it works on the same network. For help across the internet, either Lumen runs a relay (a server to pay for and keep private), or the Store offers RustDesk, which has its own relay network. Your decision | Step 5.22a |

Already known and tracked elsewhere: `/usr/etc` (step 1.3). ADR 0001 fixed suspend-then-hibernate and BitLocker resizing in the spec.

### Open design questions

| # | Question | Proposal | Decide at |
| --- | --- | --- | --- |
| Q6 | The spec sets the glass role "by a window property or shell role". Wayland has no window properties, so how does a surface name its role? | A small Lumen Wayland protocol, `lumen_glass_manager_v1`, served by lumen-glass the same way the stock blur effect serves its protocol. Windows that don't use it get a role from their window type (section 4.2) | Step 3.8 |
| Q7 | The spec keeps all settings in `~/.config/lumen/`, but some are machine-wide: update channel, automatic updates, firewall. Whose file wins when two users differ? | lumen-settingsd stays the one front door. Machine-wide keys are forwarded to the system service that owns them and stored in `/etc/lumen/`; changing them asks for the admin password | Step 5.2 |
| Q8 | Welcome creates the account and enrols the TPM before any user exists. Both need root. Who does it? | Welcome's first part runs in a first-boot session as a locked-down system user, as GNOME Initial Setup does. It creates the account through AccountsService, and enrols the TPM through a polkit-guarded method on `org.lumen.Hardware1`. First check whether KDE's own first-run project (plasma-setup) is ready to reuse | Steps 6.5, 6.6 |
| Q9 | "Every setting is also a config file and a CLI command." Does `lumen settings` also cover settings owned upstream (Wi-Fi, displays, Bluetooth)? | Not in v0.1. Those already have config files and CLIs (`nmcli`, `kscreen-doctor`, `bluetoothctl`); the Advanced section of each Settings page shows the matching command | Step 5.2 |
| Q10 | lumen-compat is Rust, but the Store, the dialog and Welcome are C++, and Lumen Setup for Windows (C++ on Windows) needs the same `hardware.json` rules as lumen-hwd. How do they share code? | Each shared Rust crate gets a small C interface (generated with cbindgen) that the C++ programs link, on Linux and on Windows. No extra daemon | Steps 7.4, 7.9 |
| Q11 | The Store installs websites as apps. What runs them? | Use the user's browser where it can open a site in its own app window (Chromium-based browsers can; Firefox on Linux can't), else GNOME Web, a Flatpak with web apps built in. Create the launchers through the dynamic launcher portal, after checking that xdg-desktop-portal-kde implements it | Step 7.7 |

## Part 2

Build flow and the dependency graph: step 0.2.
