<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Developer setup on Windows 11 Home

Lumen OS is built with Linux tools. On Windows 11 Home they run in **WSL 2** (Windows Subsystem for Linux) with **Fedora**. Heavy work, like building the full OS image and the ISO, runs in GitHub Actions. The local machine is for editing, linting, small builds and, if nested virtualization works, test VMs.

You do steps 1–5 once. Step 6 checks the result.

## This machine (checked 2026-10-27)

| What | Found | OK? |
|---|---|---|
| Windows | Windows 11 Home, build 26200 | ✅ WSL 2 is supported |
| CPU | AMD Ryzen 7 5800X, virtualization on in firmware | ✅ |
| Memory | 16 GB | ✅ meets the spec; WSL gets half by default |
| Free disk | C: 99.9 GB, D: 178 GB | ⚠️ C: is just under the 100 GB the spec asks for, so Fedora goes on **D:** |
| WSL | not installed | step 1 |
| git (Windows) | installed | ✅ |

## 1. Install WSL (needs admin, once)

1. Open **PowerShell as administrator**: Start menu → type `PowerShell` → **Run as administrator**.
2. Run:

   ```powershell
   wsl --install --no-distribution
   ```

3. Restart Windows when it asks.
4. After the restart, open a normal (not admin) PowerShell and run:

   ```powershell
   wsl --update
   wsl --version
   ```

   The first line should say `WSL version: 2.` something.

## 2. Install Fedora on the D: drive

1. See which Fedora versions WSL offers:

   ```powershell
   wsl --list --online
   ```

   Pick the highest `FedoraLinux-NN` in the list. The commands below use `FedoraLinux-44`; put your number in its place.

2. Install it on D: (C: doesn't have 100 GB free):

   ```powershell
   New-Item -ItemType Directory -Force D:\WSL
   wsl --install FedoraLinux-44 --location D:\WSL\FedoraLinux-44
   ```

3. Fedora opens and asks for a **username**. Use a short lowercase name, for example `edmund`. Fedora creates the user without a password and lets it use `sudo` without one.
4. Give your user a password (recommended):

   ```bash
   sudo passwd $USER
   ```

5. Back in PowerShell, make Fedora the default, so plain `wsl` opens it:

   ```powershell
   wsl --set-default FedoraLinux-44
   ```

To open Fedora later: Start menu → **FedoraLinux-44**, or type `wsl` in PowerShell.

## 3. Optional: give WSL more memory

WSL uses half your RAM by default (about 8 GB here). That is enough to start. If local builds run out of memory later, create or edit `%UserProfile%\.wslconfig` (for example `C:\Users\edmun\.wslconfig`) in Notepad:

```ini
[wsl2]
memory=10GB
```

Then run `wsl --shutdown` in PowerShell and reopen Fedora.

Leave `nestedVirtualization` out of this file or set it to `true`. Windows 11 turns it on by default, and the test VMs need it.

## 4. Install the tools (inside Fedora)

```bash
sudo dnf upgrade --refresh -y
sudo dnf install -y git podman just gh skopeo jq qemu-system-x86-core
```

| Tool | Why we need it | Required? |
|---|---|---|
| git | Version control | yes |
| podman | Builds and runs the OS image (a container image) | yes |
| just | Runs the project's build recipes (`just lint`, `just build-image`, …) | yes |
| gh | GitHub CLI: sign-in, CI runs, releases | yes |
| skopeo | Reads image digests from a registry without pulling the whole image | recommended |
| jq | Reads JSON in scripts | recommended |
| qemu-system-x86-core | Runs test VMs; the check script uses it to test nested virtualization | recommended |

All of these come from Fedora's own repositories; no extra repositories are needed.

## 5. Sign in to GitHub (inside Fedora)

1. Run:

   ```bash
   gh auth login
   ```

   Choose **GitHub.com** → **HTTPS** → **Yes** (authenticate Git) → **Login with a web browser**. It shows a one-time code; open the link in your Windows browser, sign in and enter the code. WSL has no password keyring, so gh may say it saved the sign-in "in plain text": that is normal here and the file is only readable by your user.
2. Let git use that sign-in:

   ```bash
   gh auth setup-git
   ```

3. Commits must use your **GitHub no-reply email**, never your personal one. The Windows checkout already has it set in `.git/config`. If you ever clone the repo inside WSL, set it globally there too (find the address under GitHub → Settings → Emails):

   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "<id>+<username>@users.noreply.github.com"
   ```

## 6. Run the check

From Fedora:

```bash
cd "/mnt/c/Users/edmun/Downloads/Lumen OS"
bash tests/dev-env/check-wsl.sh
```

Or straight from PowerShell:

```powershell
wsl --cd "C:\Users\edmun\Downloads\Lumen OS" -- bash tests/dev-env/check-wsl.sh
```

Each line is **PASS**, **WARN** (worth fixing, doesn't block work) or **FAIL** (must fix), and each problem comes with a **Fix:** line. The script ends with "Ready." and exit code 0 when nothing failed. Add `--offline` to skip the checks that need the network.

What it checks:

| Area | Checks | Level |
|---|---|---|
| System | Running in WSL 2; distribution is Fedora; systemd is running; not run as root | required |
| Tools | git, podman, just, gh are Fedora programs, not Windows ones | required |
| | skopeo, jq, qemu | recommended |
| Podman | `podman info` works; a test container (`quay.io/podman/hello`) pulls and runs | required |
| | overlay storage driver, cgroups v2 | recommended |
| GitHub | gh is signed in; this checkout commits with a GitHub no-reply email | required |
| | git uses gh to sign in | recommended |
| Disk | 100 GB free both inside WSL and on the Windows drive that holds the WSL disk | required |
| Memory | WSL has at least 7 GiB | recommended |
| Virtualization | `/dev/kvm` exists, your user can open it, and qemu starts with KVM | recommended: without it local VMs won't run, but CI boot tests still do |

## Lint and test the repository

From the checkout, in Fedora:

```bash
just lint
just test
```

`just lint` checks licences, formatting and the links between documents; `just test` runs the tests that work on this PC. Both run their tools in a container (`tests/lint/Containerfile`), so nothing else needs installing, and WSL gets the same results as CI. The first run downloads Fedora and the tools and builds the container, which takes a few minutes and about 420 MB of disk; after that each run takes a few seconds. Run `just` to list the other recipes.

## Where the code lives

There is one checkout: the Windows folder `C:\Users\edmun\Downloads\Lumen OS`, which Claude Code works in. Inside Fedora the same folder is `/mnt/c/Users/edmun/Downloads/Lumen OS`. The path has a space, so always put it in quotes.

- Files under `/mnt/c` are slower for Linux tools than WSL's own disk. That's fine for editing, linting and small builds; the big image builds run in CI.
- Container images and build caches live on WSL's own disk, which step 2 put on D:.
- Don't run git in the same checkout from Windows and from WSL at the same time.
- The repo sets `core.filemode=false` and LF line endings (`.gitattributes`), so the two sides don't see each other's files as changed.

## Running Linux commands from Windows

Claude Code runs on Windows and reaches the Linux tools through `wsl.exe`:

```powershell
wsl -d FedoraLinux-44 --cd "C:\Users\edmun\Downloads\Lumen OS" -- just lint
```

- Set `$env:WSL_UTF8 = '1'` first, or `wsl.exe`'s own messages come out as UTF-16 with spaces between the letters.
- From Git Bash, put `MSYS_NO_PATHCONV=1` in front of the command, or Git Bash rewrites Linux paths such as `/mnt/c/...` into Windows paths before WSL sees them.
- After `--`, `wsl.exe` hands the command line to your login shell first, which expands any `$variable` in it. To pass a script through unchanged, use `--exec bash -c '...'` instead.

## Troubleshooting

**`WslRegisterDistribution failed` with error `0x80370102`.** Virtualization is off. Restart into the firmware (BIOS/UEFI) settings and turn on **SVM Mode** (AMD) or **Intel VT-x**, then run `wsl --install --no-distribution` as administrator again.

**Not enough disk space.** Free some space on the drive, or move Fedora to a bigger drive. In PowerShell:

```powershell
wsl --shutdown
wsl --manage FedoraLinux-44 --move D:\WSL\FedoraLinux-44
```

If your WSL version doesn't know `--manage`, run `wsl --update` first.

**`/dev/kvm` is missing.** Check that virtualization is on in the firmware (see above), and that `%UserProfile%\.wslconfig` doesn't contain `nestedVirtualization=false`. Then `wsl --shutdown` and reopen Fedora.

**podman says "potentially insufficient UIDs or GIDs".** Your user has no subordinate ID range. Run:

```bash
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER
podman system migrate
```

**VirtualBox is slow or won't start a VM.** With WSL 2 installed, VirtualBox 7 runs on top of Windows' hypervisor. It works, but more slowly. That only matters for the Phase 1 install test.
