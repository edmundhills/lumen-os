#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check the live system, the image the install ISO is packed from: it holds
# what the container-native ISO contract v0.1.0 asks for (ADR 0011), and what
# the live session and the installer need.
#
# Usage: bash check-live.sh LIVE_DIR INSTALLER_DIR
#
# The live stage of image/Containerfile runs this inside the image it is
# building, with the checkout's image/live and installer folders. Exits 0 when
# every check passes, 1 otherwise, which stops the build.

set -u

if (($# != 2)) || [[ ! -d $1 || ! -d $2 ]]; then
  printf 'Usage: %s LIVE_DIR INSTALLER_DIR\n' "${0##*/}" >&2
  exit 2
fi
readonly live=$1 installer=$2

# Checking the image must not change it (image/Containerfile).
export PYTHONDONTWRITEBYTECODE=1

# Where Titanoboa and image-builder read the ISO's settings. image-builder
# reads its new folder instead whenever that exists.
readonly ISO_CONFIG=/usr/lib/bootc-image-builder/iso.yaml
readonly NEW_CONFIG_DIR=/usr/lib/image-builder/bootc
# The programs the contract says the image must have, for image-builder,
# which builds the ISO with the image's own tools.
readonly ISO_TOOLS=(podman mksquashfs xorriso implantisomd5 grub2-mkimage python3)

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

# One kernel, which the contract requires, with an initramfs next to it that
# can boot from the ISO: dmsquash-live finds the USB by its label and mounts
# its squashfs, and dmsquash-live-autooverlay gives it a writable layer.
kernel() {
  local dirs=(/usr/lib/modules/*/) dir modules module status=0
  if ((${#dirs[@]} != 1)); then
    printf 'The image has %d kernels, not one: %s\n' "${#dirs[@]}" "${dirs[*]}"
    return 1
  fi
  dir=${dirs[0]}
  if [[ ! -s ${dir}vmlinuz ]]; then
    printf '%svmlinuz is missing\n' "$dir"
    return 1
  fi
  if [[ ! -s ${dir}initramfs.img ]]; then
    printf '%sinitramfs.img is missing\n' "$dir"
    return 1
  fi
  modules=$(lsinitrd --mod "${dir}initramfs.img") || return 1
  for module in dmsquash-live dmsquash-live-autooverlay; do
    if ! grep -qx -- "$module" <<<"$modules"; then
      printf 'The initramfs has no dracut module %s\n' "$module"
      status=1
    fi
  done
  return "$status"
}

# shim, its MOK manager and GRUB's EFI programs, for a hard disk and for a CD,
# are where the contract wants them: in /boot/efi/EFI/<vendor>, where the
# vendor is the one folder shim's package has besides BOOT.
efi_files() {
  local vendors=() dir name file status=0
  for dir in /usr/lib/efi/shim/*/EFI/*/; do
    name=$(basename -- "$dir")
    [[ $name == BOOT ]] || vendors+=("$name")
  done
  if ((${#vendors[@]} != 1)); then
    printf 'shim has %d vendor folders, not one: %s\n' "${#vendors[@]}" "${vendors[*]}"
    return 1
  fi
  for file in shimx64.efi mmx64.efi grubx64.efi gcdx64.efi; do
    if [[ ! -s /boot/efi/EFI/${vendors[0]}/$file ]]; then
      printf '/boot/efi/EFI/%s/%s is missing\n' "${vendors[0]}" "$file"
      status=1
    fi
  done
  return "$status"
}

# GRUB's modules for PCs that boot the old way (BIOS), with its CD boot image.
grub_bios() {
  local file status=0
  for file in cdboot.img iso9660.mod biosdisk.mod normal.mod linux.mod; do
    if [[ ! -s /usr/lib/grub/i386-pc/$file ]]; then
      printf '/usr/lib/grub/i386-pc/%s is missing\n' "$file"
      status=1
    fi
  done
  return "$status"
}

iso_tools() {
  local tool status=0
  for tool in "${ISO_TOOLS[@]}"; do
    if ! command -v -- "$tool" >/dev/null; then
      printf '%s is missing\n' "$tool"
      status=1
    fi
  done
  return "$status"
}

# iso.yaml is image/live's, in the place both tools read, and every boot entry
# finds the USB by the ISO's label, boots it live, uses the kernel and
# initramfs where the contract puts them, and leaves SELinux on.
iso_config() {
  if ! cmp -s -- "$live/iso.yaml" "$ISO_CONFIG"; then
    printf '%s is missing or differs from image/live/iso.yaml\n' "$ISO_CONFIG"
    return 1
  fi
  if [[ -e $NEW_CONFIG_DIR ]]; then
    printf '%s exists, so image-builder would ignore %s\n' "$NEW_CONFIG_DIR" "$ISO_CONFIG"
    return 1
  fi
  python3 - "$ISO_CONFIG" <<'EOF'
import re
import sys

import yaml

with open(sys.argv[1], encoding="utf-8") as f:
    config = yaml.safe_load(f)
problems = []
label = config.get("label")
# An ISO 9660 volume label has at most 32 characters. Letters, digits, _ and -
# also keep /dev/disk/by-label, where the initramfs looks, free of escapes.
if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", label):
    problems.append(f"the label {label!r} isn't 1 to 32 letters, digits, _ or -")
entries = (config.get("grub2") or {}).get("entries") or []
if not entries:
    problems.append("there are no boot entries")
for entry in entries:
    name = entry.get("name")
    if not name:
        problems.append(f"an entry has no name: {entry!r}")
    words = str(entry.get("linux", "")).split()
    if words[:1] != ["/images/pxeboot/vmlinuz"]:
        problems.append(f"{name}: the kernel isn't /images/pxeboot/vmlinuz")
    for want in (f"root=live:CDLABEL={label}", "rd.live.image"):
        if want not in words:
            problems.append(f"{name}: the kernel arguments have no {want}")
    for word in words:
        if word in ("enforcing=0", "selinux=0"):
            problems.append(f"{name}: {word} turns SELinux off")
    if entry.get("initrd") != "/images/pxeboot/initrd.img":
        problems.append(f"{name}: the initramfs isn't /images/pxeboot/initrd.img")
for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
EOF
}

# livesys sets up the live session at boot, with its Plasma settings.
livesys() {
  local unit state status=0
  if ! grep -qx 'livesys_session=kde' /etc/sysconfig/livesys; then
    printf '/etc/sysconfig/livesys does not say livesys_session=kde\n'
    status=1
  fi
  if [[ ! -f /usr/libexec/livesys/sessions.d/livesys-kde ]]; then
    printf "livesys has no Plasma session script\n"
    status=1
  fi
  for unit in livesys.service livesys-late.service; do
    state=$(systemctl is-enabled -- "$unit" 2>&1)
    if [[ $state != enabled ]]; then
      printf '%s is %s, not enabled\n' "$unit" "$state"
      status=1
    fi
  done
  return "$status"
}

# Anaconda's install profile is installer/anaconda/lumen.conf, and Anaconda's
# own loader picks it by the image's os-release and reads Lumen's storage
# defaults from it.
anaconda_profile() {
  local profile=/etc/anaconda/profile.d/lumen.conf
  if ! cmp -s -- "$installer/anaconda/lumen.conf" "$profile"; then
    printf '%s is missing or differs from installer/anaconda/lumen.conf\n' "$profile"
    return 1
  fi
  if [[ $(stat --format=%a -- "$profile") != 644 ]]; then
    printf '%s has mode %s, not 644\n' "$profile" "$(stat --format=%a -- "$profile")"
    return 1
  fi
  python3 - <<'EOF'
import sys

from pyanaconda.core.configuration.anaconda import AnacondaConfiguration
from pyanaconda.core.configuration.profile import ProfileLoader
from pyanaconda.core.configuration.storage import PartitioningScheme
from pyanaconda.core.util import get_os_release_value

loader = ProfileLoader()
loader.load_profiles("/etc/anaconda/profile.d")
profile = loader.detect_profile(get_os_release_value("ID"), get_os_release_value("VARIANT_ID"))
if profile != "lumen":
    print(f"Anaconda picks the profile {profile!r}, not 'lumen'")
    sys.exit(1)
conf = AnacondaConfiguration.from_defaults()
conf.set_from_profile(profile)
problems = []
# Anaconda reads the scheme as the number its kickstart code uses.
scheme = PartitioningScheme(conf.storage.default_scheme).name
if scheme != "BTRFS":
    problems.append(f"the default scheme is {scheme}, not BTRFS")
if conf.storage.btrfs_compression != "zstd:1":
    problems.append(f"Btrfs compression is {conf.storage.btrfs_compression!r}, not 'zstd:1'")
for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
EOF
}

# The installer installs the ISO's own copy of the Lumen image (step 1.8c):
# Anaconda's kickstart for the live session is installer/anaconda's, the
# kickstart parser Anaconda uses reads a bootc command from it that installs
# from container storage under the name the system then follows, and bootc,
# run from the live system, reads Lumen's setting that records the image as
# signed. bootc and skopeo copy the image out of container storage, which
# needs fuse-overlayfs on the live session's overlay root.
installer_kickstart() {
  local kickstart=/usr/share/anaconda/interactive-defaults.ks tool config status=0
  if ! cmp -s -- "$installer/anaconda/interactive-defaults.ks" "$kickstart"; then
    printf '%s is missing or differs from installer/anaconda/interactive-defaults.ks\n' "$kickstart"
    return 1
  fi
  for tool in bootc skopeo fuse-overlayfs; do
    if ! command -v -- "$tool" >/dev/null; then
      printf '%s is missing\n' "$tool"
      status=1
    fi
  done
  config=$(bootc install print-configuration --all) || {
    printf 'bootc install print-configuration failed\n'
    return 1
  }
  python3 - "$kickstart" "$config" <<'EOF' || status=1
import json
import sys

from pykickstart.parser import KickstartParser
from pykickstart.version import makeVersion

handler = makeVersion()
KickstartParser(handler).readKickstart(sys.argv[1])
problems = []
bootc = handler.bootc
if not bootc.seen:
    problems.append("the kickstart has no bootc command")
else:
    source, target = bootc.sourceImgRef or "", bootc.targetImgRef or ""
    if not source.startswith("containers-storage:"):
        problems.append(f"bootc installs from {source!r}, not from the ISO's container storage")
    elif source.removeprefix("containers-storage:") != target:
        problems.append(f"bootc installs {source!r} but the system then follows {target!r}")
for command in ("ostreecontainer", "ostreesetup", "liveimg", "url"):
    if getattr(handler, command).seen:
        problems.append(f"the kickstart also has {command}, another source")
if json.loads(sys.argv[2]).get("enforce-container-sigpolicy") is not True:
    problems.append(f"bootc, run from the live system, doesn't record the image as signed: {sys.argv[2]}")
for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
EOF
  return "$status"
}

# The browser Anaconda's Fedora profile shows WebUI in (webui_web_engine).
webui_browser() {
  if ! command -v slitherer >/dev/null; then
    printf 'slitherer, the browser WebUI runs in, is missing\n'
    return 1
  fi
}

# The first-run setup, which creates the first user on an installed system,
# doesn't start in the live session: Plasma Setup skips live boots, and
# livesys marks it done as well. Welcome (step 6.5) will need the same.
no_first_run_setup() {
  local status=0
  if ! systemctl cat plasma-setup.service | grep -qx 'ConditionKernelCommandLine=!rd.live.image'; then
    printf 'plasma-setup.service no longer skips live boots\n'
    status=1
  fi
  if ! grep -q 'plasma-setup-done' /usr/libexec/livesys/sessions.d/livesys-kde; then
    printf "livesys's Plasma script no longer marks Plasma Setup done\n"
    status=1
  fi
  return "$status"
}

# The build's ostree repository is gone, so no file has a second path that the
# SELinux policy labels differently (image/Containerfile).
no_ostree_repo() {
  local path status=0
  for path in /sysroot/ostree /ostree; do
    if [[ -e $path || -L $path ]]; then
      printf '%s is still here\n' "$path"
      status=1
    fi
  done
  return "$status"
}

# The live stage leaves SELinux enforcing, as the installed system has it.
selinux() {
  if ! grep -qx 'SELINUX=enforcing' /etc/selinux/config; then
    printf '/etc/selinux/config does not say SELINUX=enforcing\n'
    return 1
  fi
}

# No Python bytecode is stale, so no program writes new bytecode into the
# live session's /usr (image/live/bytecode.py).
bytecode() { python3 "$live/bytecode.py" check /; }

printf 'Lumen live system checks\n'
check "One kernel, with an initramfs that boots from the ISO" kernel
check "shim and GRUB's EFI programs are in /boot/efi" efi_files
check "GRUB's BIOS modules are in /usr/lib/grub/i386-pc" grub_bios
check "The tools image-builder packs the ISO with are here" iso_tools
check "iso.yaml names the label and boots live with SELinux on" iso_config
check "livesys sets up a Plasma live session" livesys
check "Anaconda uses Lumen's install profile" anaconda_profile
check "The installer installs the ISO's copy of the image, recorded as signed" installer_kickstart
check "WebUI's browser is here" webui_browser
check "The first-run setup doesn't start in the live session" no_first_run_setup
check "The build's ostree repository is gone" no_ostree_repo
check "SELinux is enforcing" selinux
check "Python's bytecode matches its source" bytecode

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
