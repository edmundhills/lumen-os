#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check the image: what image/overlay and the lumen stage of the Containerfile
# set up is in place.
#
# Usage: bash check-image.sh OVERLAY_DIR
#
# The lumen stage runs this inside the image it is building, with the
# checkout's image/overlay as OVERLAY_DIR, just before `bootc container lint`.
# Exits 0 when every check passes, 1 otherwise, which stops the build.

set -u

if (($# != 1)) || [[ ! -d $1 ]]; then
  printf 'Usage: %s OVERLAY_DIR\n' "${0##*/}" >&2
  exit 2
fi
readonly overlay=$1
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly here

# Checking the image must not change it: Python would write bytecode files for
# the modules it imports that have none (image/Containerfile).
export PYTHONDONTWRITEBYTECODE=1

# The timers the Containerfile masks.
readonly MASKED_UNITS=(
  rpm-ostreed-automatic.timer bootc-fetch-apply-updates.timer
  rpm-ostree-countme.timer
)

passes=0 failures=0

# check NAME FUNCTION: run one check, and show its output only if it fails.
check() {
  local name=$1 out
  if out=$("$2" 2>&1); then
    passes=$((passes + 1))
    printf '  PASS  %s\n' "$name"
  else
    failures=$((failures + 1))
    printf '  FAIL  %s\n' "$name"
    [[ -z $out ]] || printf '%s\n' "$out" | sed 's/^/        /'
  fi
}

# Every overlay file is in the image unchanged, owned by root, and writable
# only by root; programs in /usr/libexec are executable and nothing else is.
overlay_files() {
  local src dst rel mode want status=0
  while IFS= read -r -d '' src; do
    rel=${src#"$overlay"}
    dst=/${rel#/}
    if [[ ! -e $dst ]]; then
      printf '%s is missing\n' "$dst"
      status=1
      continue
    fi
    if [[ -f $src ]] && ! cmp -s -- "$src" "$dst"; then
      printf '%s differs from image/overlay%s\n' "$dst" "$rel"
      status=1
    fi
    mode=$(stat --format=%a -- "$dst")
    if [[ -d $dst ]]; then
      want=755
    elif [[ $dst == /usr/libexec/lumen-* ]]; then
      want=755
    else
      want=644
    fi
    if [[ $mode != "$want" ]]; then
      printf '%s has mode %s, not %s\n' "$dst" "$mode" "$want"
      status=1
    fi
    if [[ $(stat --format=%U:%G -- "$dst") != root:root ]]; then
      printf '%s is owned by %s, not root\n' "$dst" "$(stat --format=%U:%G -- "$dst")"
      status=1
    fi
  done < <(find "$overlay" -mindepth 1 -print0)
  return "$status"
}

# Every unit that Lumen's presets enable is enabled.
enabled_units() {
  local unit state status=0
  while read -r unit; do
    state=$(systemctl is-enabled -- "$unit" 2>&1)
    if [[ $state != enabled ]]; then
      printf '%s is %s; its preset enables it\n' "$unit" "$state"
      status=1
    fi
  done < <(sed -n 's/^enable[[:space:]]\+//p' "$overlay"/usr/lib/systemd/system-preset/*.preset)
  return "$status"
}

masked_units() {
  local unit state status=0
  for unit in "${MASKED_UNITS[@]}"; do
    state=$(systemctl is-enabled -- "$unit" 2>&1)
    if [[ $state != masked ]]; then
      printf '%s is %s, not masked\n' "$unit" "$state"
      status=1
    fi
  done
  return "$status"
}

# systemd accepts Lumen's own units, and the programs they start exist.
lumen_units() {
  local units=(/usr/lib/systemd/system/lumen-*) status=0 had_stamp=0
  # systemd-analyze leaves this file behind, and bootc container lint rejects
  # files in /run.
  local stamp=/run/systemd/systemd-units-load
  [[ -e ${units[0]} ]] || return 0
  [[ ! -e $stamp ]] || had_stamp=1
  systemd-analyze verify --man=no -- "${units[@]}" || status=$?
  ((had_stamp)) || rm -f -- "$stamp"
  return "$status"
}

# bootc install, and bootc-image-builder with it, puts the root on Btrfs.
btrfs_root() {
  local fs
  fs=$(bootc install print-configuration |
    python3 -c 'import json, sys; print(json.load(sys.stdin).get("root-fs-type"))') || return 1
  if [[ $fs != btrfs ]]; then
    printf 'bootc install would make a %s root, not Btrfs\n' "$fs"
    return 1
  fi
}

# SELinux is enforcing, and no kernel argument the image adds turns it off.
selinux() {
  local status=0
  if ! grep -qx 'SELINUX=enforcing' /etc/selinux/config; then
    printf '/etc/selinux/config does not say SELINUX=enforcing\n'
    status=1
  fi
  if grep -rEn '(^|[^[:alnum:]_])(selinux|enforcing)=0' /usr/lib/bootc/kargs.d /usr/lib/bootc/install 2>/dev/null; then
    printf 'a kernel argument above turns SELinux off\n'
    status=1
  fi
  return "$status"
}

# Discover is gone (image/packages.toml removes it), with nothing left to start it.
no_discover() {
  local status=0 left
  if left=$(rpm -qa 'plasma-discover*') && [[ -n $left ]]; then
    printf 'Discover packages are installed: %s\n' "$left"
    status=1
  fi
  if left=$(find /usr/share/applications /etc/xdg/autostart -name 'org.kde.discover*' -print) && [[ -n $left ]]; then
    printf 'Discover files are left: %s\n' "$left"
    status=1
  fi
  return "$status"
}

# Plasma starts new users with Lumen's global theme, and so with its layout.
# KDE reads its config directories in the order Fedora's
# /etc/xdg/plasma-workspace/env/env.sh sets, with an empty home folder.
global_theme() {
  local home theme status=0
  home=$(mktemp -d) || return 1
  theme=$(HOME=$home XDG_CONFIG_HOME=$home/config XDG_CACHE_HOME=$home/cache \
    XDG_CONFIG_DIRS=/etc/xdg:/usr/share/kde-settings/kde-profile/default/xdg \
    kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage)
  if [[ $theme != org.lumen.desktop ]]; then
    printf 'The default global theme is "%s", not org.lumen.desktop\n' "$theme"
    status=1
  fi
  if ! HOME=$home XDG_CACHE_HOME=$home/cache \
    kpackagetool6 --type Plasma/LookAndFeel --show org.lumen.desktop >/dev/null; then
    printf 'Plasma cannot load the org.lumen.desktop global theme\n'
    status=1
  fi
  rm -rf -- "$home"
  return "$status"
}

# os-release names Lumen and its build, still says it is like Fedora, and
# /etc/os-release leads to it (image/os-release.sh). An edition, such as the
# gaming one, adds VARIANT_ID, and its IMAGE_ID is lumen-<VARIANT_ID>.
os_release() {
  local fedora want status=0 line variant
  fedora=$(rpm --eval '%{fedora}') || return 1
  variant=$(sed -n 's/^VARIANT_ID=//p' /usr/lib/os-release)
  for want in 'ID=lumen' 'ID_LIKE=fedora' "IMAGE_ID=lumen${variant:+-$variant}" 'NAME="Lumen OS"'; do
    if ! grep -qxF -- "$want" /usr/lib/os-release; then
      printf '/usr/lib/os-release has no line %s\n' "$want"
      status=1
    fi
  done
  line=$(grep -E '^IMAGE_VERSION=' /usr/lib/os-release)
  if [[ ! $line =~ ^IMAGE_VERSION=${fedora}\.[0-9]{8}(\.[1-9][0-9]*)?$ ]]; then
    printf 'IMAGE_VERSION is not a build version for Fedora %s: %s\n' "$fedora" "${line:-missing}"
    status=1
  fi
  if ! cmp -s /etc/os-release /usr/lib/os-release; then
    printf '/etc/os-release is not the same file as /usr/lib/os-release\n'
    status=1
  fi
  return "$status"
}

# Images under Lumen's names are accepted only with Lumen's signature, as
# containers/image reads the settings in the image: no other file in
# registries.d undoes Lumen's, and the key is there (image/trust.py, ADR 0008).
trust_policy() {
  python3 "$here/trust.py" check /
}

# tuned-ppd's power modes are Lumen's own tuned profiles, each a Fedora
# profile that keeps tuned from running bootc, and tuned starts with Lumen's
# Balanced before tuned-ppd picks a mode: no other recommendation comes first,
# in the order tuned reads them (ADR 0013).
tuned_profiles() {
  python3 - <<'EOF'
import configparser
import os

problems = []
ppd = configparser.ConfigParser()
ppd.read("/etc/tuned/ppd.conf")
modes = dict(ppd["profiles"]) if ppd.has_section("profiles") else {}
battery = dict(ppd["battery"]) if ppd.has_section("battery") else {}
for mode in ("power-saver", "balanced", "performance"):
    if mode not in modes:
        problems.append(f"/etc/tuned/ppd.conf has no profile for the power mode {mode}")
for name in sorted(set(modes.values()) | set(battery.values())):
    path = f"/usr/lib/tuned/profiles/{name}/tuned.conf"
    profile = configparser.ConfigParser()
    if not name.startswith("lumen-") or not profile.read(path):
        problems.append(f"tuned-ppd maps a power mode to {name}, which is not one of Lumen's profiles in {path}")
        continue
    if os.path.exists(f"/etc/tuned/profiles/{name}"):
        problems.append(f"/etc/tuned/profiles/{name} takes the place of Lumen's profile")
    if profile.get("bootloader", "skip_grub_config", fallback="") != "True":
        problems.append(f"{path} doesn't set skip_grub_config=True, so tuned would run bootc")
    include = profile.get("main", "include", fallback="")
    if not os.path.isfile(f"/usr/lib/tuned/profiles/{include}/tuned.conf"):
        problems.append(f"{path} includes {include or 'nothing'}, which is not a profile")
if os.path.exists("/etc/tuned/recommend.conf"):
    problems.append("/etc/tuned/recommend.conf comes before Lumen's recommendation")
files = {}
for d in ("/usr/lib/tuned/recommend.d", "/etc/tuned/recommend.d"):
    for name in os.listdir(d) if os.path.isdir(d) else []:
        files[name] = os.path.join(d, name)
first = None
for name in sorted(files):
    config = configparser.ConfigParser(delimiters=("=",), inline_comment_prefixes=("#",), strict=False)
    config.read(files[name])
    if config.sections():
        first = (files[name], config.sections()[0], config.options(config.sections()[0]))
        break
if not first or first[1:] != ("lumen-balanced", []):
    problems.append(f"tuned's first recommendation is not lumen-balanced without conditions: {first}")
print("\n".join(problems))
raise SystemExit(1 if problems else 0)
EOF
}

# mcelog.service skips itself on AMD and Hygon processors, which mcelog
# refuses with an error (image/overlay/usr/lib/systemd/system/mcelog.service.d,
# docs/decisions/0017-boot-test.md): systemd sees the drop-in, and its
# condition, run on a stand-in /proc/cpuinfo, stops an AMD or Hygon processor
# and lets an Intel one through.
mcelog_on_amd() {
  if ! systemctl cat mcelog.service | grep -q '^ExecCondition=.*AuthenticAMD'; then
    printf "systemctl cat mcelog.service doesn't show Lumen's condition on the processor\n"
    return 1
  fi
  python3 - <<'EOF'
import shlex
import subprocess
import sys
import tempfile

dropin = "/usr/lib/systemd/system/mcelog.service.d/50-lumen-cpu.conf"
lines = [line for line in open(dropin, encoding="utf-8") if line.startswith("ExecCondition=")]
if len(lines) != 1:
    print(f"{dropin} has {len(lines)} ExecCondition lines, not one")
    sys.exit(1)
command = shlex.split(lines[0].removeprefix("ExecCondition="))
problems = []
for vendor, family, runs in (("AuthenticAMD", 25, False), ("HygonGenuine", 24, False), ("GenuineIntel", 6, True)):
    with tempfile.NamedTemporaryFile("w", suffix="-cpuinfo") as cpuinfo:
        cpuinfo.write(f"processor\t: 0\nvendor_id\t: {vendor}\ncpu family\t: {family}\n")
        cpuinfo.flush()
        status = subprocess.run([c.replace("/proc/cpuinfo", cpuinfo.name) for c in command]).returncode
    if (status == 0) != runs:
        problems.append(f"on a processor from {vendor}, the condition {'stops' if runs else 'lets through'} mcelog")
for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
EOF
}

# bootc install, and the installers and bootc-image-builder with it, records
# the image with its signatures checked (ostree-image-signed).
signed_installs() {
  local enforced
  enforced=$(bootc install print-configuration |
    python3 -c 'import json, sys; print(json.load(sys.stdin).get("enforce-container-sigpolicy"))') || return 1
  if [[ $enforced != True ]]; then
    printf 'bootc install would follow the image without checking its signatures (enforce-container-sigpolicy is %s)\n' \
      "$enforced"
    return 1
  fi
}

# KWin and the Plasma desktop are the same release: KDE releases them together,
# and lumen-glass is built against KWin (docs/architecture.md, section 9.4).
# The base stage installs from Fedora's mirrors, which carry only the newest
# builds, so a package it adds can pull in a new Plasma release while the
# pinned Kinoite keeps its KWin; on 2026-11-01 dnf moved plasma-workspace and
# 23 other Plasma packages to 6.8.2 with KWin still 6.7.5. A Plasma release
# arrives with the weekly bump of the Kinoite pin instead.
same_plasma_release() {
  local kwin workspace
  kwin=$(rpm --query --queryformat '%{VERSION}' kwin) || return 1
  workspace=$(rpm --query --queryformat '%{VERSION}' plasma-workspace) || return 1
  if [[ $kwin != "$workspace" ]]; then
    printf 'KWin is %s but plasma-workspace is %s: a package the image adds pulled in another Plasma release.\n' \
      "$kwin" "$workspace"
    printf 'Wait for the Kinoite pin to move to a build with Plasma %s (the base workflow), or pin what pulled it.\n' \
      "$workspace"
    return 1
  fi
}

printf 'Lumen image checks\n'
# Wine's ntsync driver loads at every start (step 1.13): a modules-load.d file
# names it, and the image's kernel has it.
ntsync() {
  local file=/usr/lib/modules-load.d/lumen-ntsync.conf dir status=0
  if ! grep -qx ntsync "$file"; then
    printf '%s does not name ntsync\n' "$file"
    status=1
  fi
  for dir in /usr/lib/modules/*/; do
    if ! find "$dir" -name 'ntsync.ko*' | grep -q . && ! grep -qs '/ntsync\.ko$' "$dir/modules.builtin"; then
      printf 'The kernel in %s has no ntsync module\n' "$dir"
      status=1
    fi
  done
  return "$status"
}

# Bottles comes on first boot (step 1.13): Flatpak can preinstall, the
# preinstall list names Bottles, Flathub becomes a system remote on first use,
# and Lumen's timer is the only unit that runs `flatpak preinstall`.
first_boot_apps() {
  local status=0 flathub=() others
  if ! flatpak preinstall --help >/dev/null 2>&1; then
    printf "Flatpak %s has no 'flatpak preinstall', which came in 1.17\n" "$(flatpak --version)"
    status=1
  fi
  if ! grep -qxF '[Flatpak Preinstall com.usebottles.bottles]' /usr/share/flatpak/preinstall.d/lumen.preinstall; then
    printf "/usr/share/flatpak/preinstall.d/lumen.preinstall doesn't name Bottles\n"
    status=1
  fi
  # A .flatpakrepo in a remotes.d folder becomes a remote when Flatpak first
  # runs; Flathub's must not be filtered.
  mapfile -t flathub < <(grep -lxF 'Url=https://dl.flathub.org/repo/' /usr/share/flatpak/remotes.d/*.flatpakrepo \
    /etc/flatpak/remotes.d/*.flatpakrepo 2>/dev/null)
  if ((${#flathub[@]} == 0)); then
    printf 'No remotes.d file sets up Flathub. The .flatpakrepo files in the image:\n'
    find /usr/share/flatpak /etc/flatpak -name '*.flatpakrepo' -exec grep -H -E '^(Title|Url|Filter)=' {} + 2>&1
    status=1
  elif grep -H '^Filter=' "${flathub[@]}"; then
    printf 'Flathub is filtered\n'
    status=1
  fi
  others=$(grep -rlsF 'flatpak preinstall' /usr/lib/systemd/system /usr/lib/systemd/user /etc/systemd |
    grep -v '/lumen-flatpak-preinstall\.service$')
  if [[ -n $others ]]; then
    printf 'Other units run flatpak preinstall too: %s\n' "$others"
    status=1
  fi
  return "$status"
}

# .exe and .msi files open in Bottles (step 1.13): for every type
# shared-mime-info gives them, Plasma's vendor list, as the lumen stage left
# it, puts Bottles first, and no list Plasma reads before it says otherwise
# (image/windows_apps.py).
windows_apps() {
  python3 "$here/windows_apps.py" check /
}

check "Overlay files are in place, owned and writable only by root" overlay_files
check "Units that Lumen's presets enable are enabled" enabled_units
check "Fedora's updaters and countme ping are masked" masked_units
check "Lumen's systemd units are valid" lumen_units
check "bootc installs to a Btrfs root" btrfs_root
check "SELinux is enforcing" selinux
check "Discover is removed" no_discover
check "Lumen's global theme (interim top bar) is the default" global_theme
check "os-release names Lumen and its build version" os_release
check "Only images Lumen signed are trusted under Lumen's names" trust_policy
check "Power modes use Lumen's tuned profiles, which don't run bootc" tuned_profiles
check "bootc install follows the image with its signatures checked" signed_installs
check "mcelog, which supports no recent AMD processor, skips itself on one" mcelog_on_amd
check "KWin and Plasma are the same release" same_plasma_release
check "Wine's ntsync driver loads at every start" ntsync
check "Bottles comes from Flathub after the first start, through flatpak preinstall" first_boot_apps
check ".exe and .msi files open in Bottles" windows_apps

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
