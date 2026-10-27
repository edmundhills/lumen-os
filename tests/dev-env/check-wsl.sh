#!/usr/bin/env bash
# Check that a WSL 2 + Fedora machine is ready for Lumen OS development.
#
# Usage: bash tests/dev-env/check-wsl.sh [--offline]
#   --offline  skip the checks that need the network (test container, GitHub sign-in)
#
# Exits 0 when every required check passes (warnings are allowed), 1 otherwise.
# Setup guide: docs/dev-setup-windows.md

set -u

readonly MIN_FREE_GB=100
readonly MIN_MEM_GIB=7 # WSL gets half the host RAM by default: a 16 GB PC gives about 7.7 GiB
readonly TEST_IMAGE=quay.io/podman/hello:latest

offline=0
for arg in "$@"; do
  case $arg in
    --offline) offline=1 ;;
    -h | --help)
      sed -n '2,8s/^# \{0,1\}//p' "$0"
      exit 0
      ;;
    *)
      printf 'Unknown option: %s (try --help)\n' "$arg" >&2
      exit 2
      ;;
  esac
done

if [[ -t 1 ]]; then
  c_pass=$'\e[32m' c_warn=$'\e[33m' c_fail=$'\e[31m' c_dim=$'\e[2m' c_bold=$'\e[1m' c_off=$'\e[0m'
else
  c_pass='' c_warn='' c_fail='' c_dim='' c_bold='' c_off=''
fi

passes=0 warnings=0 failures=0

section() { printf '\n%s%s%s\n' "$c_bold" "$1" "$c_off"; }
pass() {
  passes=$((passes + 1))
  printf '  %sPASS%s  %s\n' "$c_pass" "$c_off" "$1"
}
skip() { printf '  %sSKIP%s  %s\n' "$c_dim" "$c_off" "$1"; }
# warn/fail MESSAGE [FIX]
warn() {
  warnings=$((warnings + 1))
  report "$c_warn" WARN "$@"
}
fail() {
  failures=$((failures + 1))
  report "$c_fail" FAIL "$@"
}
report() {
  printf '  %s%s%s  %s\n' "$1" "$2" "$c_off" "$3"
  if [[ -n ${4:-} ]]; then
    printf '        %sFix: %s%s\n' "$c_dim" "$4" "$c_off"
  fi
}

have() { command -v -- "$1" >/dev/null 2>&1; }

# Free space in whole GB (rounded down) on the filesystem that holds PATH; empty if unknown.
free_gb() {
  local mib
  mib=$(df -BM --output=avail -- "$1" 2>/dev/null | tail -n 1 | tr -dc '0-9')
  [[ -n $mib ]] && printf '%d\n' $((mib / 1024))
}

# Windows folder that holds this distribution's virtual disk, e.g. D:\WSL\FedoraLinux-43.
windows_base_path() {
  local ps=powershell.exe
  have "$ps" || ps=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
  [[ -x $ps ]] || have "$ps" || return 1
  "$ps" -NoProfile -NonInteractive -Command \
    "(Get-ChildItem HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Lxss | Get-ItemProperty | Where-Object DistributionName -eq '$1').BasePath" \
    2>/dev/null | tr -d '\r' | head -n 1
}

# check_tool COMMAND PACKAGE LEVEL PURPOSE, where LEVEL is fail (required) or warn (recommended).
check_tool() {
  local cmd=$1 pkg=$2 level=$3 purpose=$4 path version
  if ! path=$(command -v -- "$cmd"); then
    "$level" "$cmd is not installed ($purpose)" "sudo dnf install -y $pkg"
    return
  fi
  if [[ $path == /mnt/* ]]; then
    "$level" "$cmd is the Windows copy ($path), not a Fedora one" "sudo dnf install -y $pkg"
    return
  fi
  version=$("$cmd" --version 2>/dev/null | head -n 1)
  pass "$cmd: ${version:-installed}"
}

printf '%sLumen OS developer environment check (WSL 2 + Fedora)%s\n' "$c_bold" "$c_off"

section "System"

kernel=$(uname -r)
if [[ $kernel == *microsoft-standard-WSL2* ]]; then
  pass "Running in WSL 2 (kernel $kernel)"
elif [[ $kernel == *[Mm]icrosoft* ]]; then
  fail "Running in WSL 1, which cannot run containers" \
    "In PowerShell: wsl --set-version ${WSL_DISTRO_NAME:-<distribution>} 2"
else
  fail "Not running inside WSL 2 (kernel $kernel)" \
    "Run this script inside the Fedora WSL distribution (docs/dev-setup-windows.md, step 2)"
fi

if [[ -r /etc/os-release ]]; then
  os_id=$(. /etc/os-release && printf '%s' "${ID:-}")
  os_name=$(. /etc/os-release && printf '%s' "${PRETTY_NAME:-${NAME:-unknown}}")
else
  os_id='' os_name=unknown
fi
if [[ $os_id == fedora ]]; then
  pass "Distribution: $os_name"
else
  fail "Distribution is $os_name, not Fedora" \
    "Install Fedora (docs/dev-setup-windows.md, step 2) and run this script inside it"
fi

if [[ $(cat /proc/1/comm 2>/dev/null) == systemd ]]; then
  pass "systemd is running"
else
  fail "systemd is not running" \
    "Add a [boot] section with systemd=true to /etc/wsl.conf, then run 'wsl --shutdown' in PowerShell"
fi

if [[ $EUID -eq 0 ]]; then
  fail "Running as root" "Run the script as your normal user, without sudo"
else
  pass "Running as normal user $(id -un)"
fi

section "Tools"

check_tool git git fail "version control"
check_tool podman podman fail "builds the OS image"
check_tool just just fail "runs the project's build recipes"
check_tool gh gh fail "talks to GitHub and CI"
check_tool skopeo skopeo warn "reads image digests without pulling the image"
check_tool jq jq warn "reads JSON in scripts"
check_tool qemu-system-x86_64 qemu-system-x86-core warn "runs test VMs"

section "Podman"

if ! have podman; then
  skip "podman is not installed"
elif err=$(podman info 2>&1 >/dev/null); then
  driver=$(podman info --format '{{.Store.GraphDriverName}}' 2>/dev/null) || driver=unknown
  cgroups=$(podman info --format '{{.Host.CgroupsVersion}}' 2>/dev/null) || cgroups=unknown
  pass "podman works (storage driver: $driver, cgroups: $cgroups)"
  if [[ $driver != overlay ]]; then
    warn "podman uses the '$driver' storage driver, which is slow and wastes disk" \
      "Remove any 'driver' line from ~/.config/containers/storage.conf, then run 'podman system reset' (this deletes local images)"
  fi
  if [[ $cgroups != v2 ]]; then
    warn "cgroups $cgroups in use; podman needs cgroups v2 to limit container resources" \
      "Add kernelCommandLine=cgroup_no_v1=all under [wsl2] in %UserProfile%\\.wslconfig, then run 'wsl --shutdown'"
  fi
  if ((offline)); then
    skip "Test container (--offline)"
  elif out=$(timeout 300 podman run --rm --network=none "$TEST_IMAGE" 2>&1); then
    pass "podman can pull and run a container ($TEST_IMAGE)"
  else
    fail "podman could not pull or run $TEST_IMAGE: $(printf '%s\n' "$out" | tail -n 1)" \
      "Check the network connection, then run: podman run --rm $TEST_IMAGE"
  fi
else
  fail "podman does not work: $(printf '%s\n' "$err" | tail -n 1)" "Run 'podman info' to see the full error"
fi

section "GitHub"

if ! have gh; then
  skip "gh is not installed"
elif ((offline)); then
  if gh auth token --hostname github.com >/dev/null 2>&1; then
    pass "gh has a saved GitHub sign-in (not verified: --offline)"
  else
    fail "gh is not signed in to GitHub" "gh auth login   (choose GitHub.com, HTTPS, then 'Login with a web browser')"
  fi
elif out=$(gh auth status --hostname github.com 2>&1); then
  account=$(printf '%s\n' "$out" | sed -n -E 's/.*Logged in to github\.com (account|as) ([^ ]+).*/\2/p' | head -n 1)
  pass "gh is signed in to GitHub${account:+ as $account}"
else
  fail "gh is not signed in to GitHub" "gh auth login   (choose GitHub.com, HTTPS, then 'Login with a web browser')"
fi

if ! have git; then
  skip "git is not installed"
else
  if git config --get-regexp '^credential\.' 2>/dev/null | grep -q 'gh auth git-credential'; then
    pass "git signs in to GitHub through gh"
  else
    warn "git in WSL has no GitHub sign-in, so 'git push' from WSL will fail" "gh auth setup-git"
  fi

  script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  if repo=$(git -C "$script_dir" rev-parse --show-toplevel 2>&1); then
    name=$(git -C "$repo" config user.name)
    email=$(git -C "$repo" config user.email)
    noreply_fix="git config --global user.email '<id>+<username>@users.noreply.github.com'  (GitHub > Settings > Emails)"
    if [[ -z $name ]]; then
      fail "git has no author name set" "git config --global user.name 'Your Name'"
    elif [[ -z $email ]]; then
      fail "git has no commit email set" "$noreply_fix"
    elif [[ $email != *@users.noreply.github.com ]]; then
      fail "Commits would use an email that is not your GitHub no-reply address" "$noreply_fix"
    else
      pass "Commits in this checkout use a GitHub no-reply email"
    fi
  elif [[ $repo == *"dubious ownership"* ]]; then
    fail "git refuses to use this checkout (dubious ownership)" \
      "git config --global --add safe.directory '$(cd -- "$script_dir/../.." && pwd)'"
  else
    skip "Not inside a git checkout, so the commit email was not checked"
  fi
fi

section "Disk and memory"

linux_free=$(free_gb "$HOME")
host_free='' host_drive=''
if [[ -n ${WSL_DISTRO_NAME:-} ]]; then
  base=$(windows_base_path "$WSL_DISTRO_NAME")
  base=${base#'\\?\'}
  if [[ $base =~ ^([A-Za-z]): ]]; then
    host_drive=${BASH_REMATCH[1]^^}
    host_free=$(free_gb "/mnt/${host_drive,,}")
  fi
fi

disk_fix="Free up space, or move Fedora to a bigger drive (docs/dev-setup-windows.md, 'Not enough disk space')"
if [[ -z $linux_free ]]; then
  fail "Could not read the free space inside WSL" "Run 'df -h ~' to see why"
elif [[ -n $host_free ]]; then
  summary="$host_free GB free on drive $host_drive: (it holds the WSL disk), $linux_free GB free inside WSL"
  if ((host_free >= MIN_FREE_GB && linux_free >= MIN_FREE_GB)); then
    pass "$summary"
  else
    fail "$summary; need $MIN_FREE_GB GB" "$disk_fix"
  fi
elif ((linux_free >= MIN_FREE_GB)); then
  warn "$linux_free GB free inside WSL, but could not check the Windows drive that holds the WSL disk" \
    "Make sure that drive has $MIN_FREE_GB GB free (docs/dev-setup-windows.md, step 2)"
else
  fail "$linux_free GB free inside WSL; need $MIN_FREE_GB GB" "$disk_fix"
fi

mem_kib=$(grep -m 1 '^MemTotal:' /proc/meminfo 2>/dev/null | tr -dc '0-9')
mem_tenths=$((${mem_kib:-0} * 10 / 1048576))
mem_gib="$((mem_tenths / 10)).$((mem_tenths % 10))"
cpus=$(nproc 2>/dev/null || echo '?')
if ((${mem_kib:-0} >= MIN_MEM_GIB * 1048576)); then
  pass "WSL has $mem_gib GiB of memory and $cpus CPU threads"
else
  warn "WSL has only $mem_gib GiB of memory; local builds may run out" \
    "Raise memory= in %UserProfile%\\.wslconfig (docs/dev-setup-windows.md, step 3), then run 'wsl --shutdown'"
fi

section "Virtualization"

kvm_fix="Turn on SVM (AMD) or VT-x (Intel) in the firmware settings and make sure %UserProfile%\\.wslconfig does not set nestedVirtualization=false; then run 'wsl --shutdown'"
if [[ ! -e /dev/kvm ]]; then
  warn "Nested virtualization is off (/dev/kvm is missing): local test VMs will not run, but CI boot tests still will" \
    "$kvm_fix"
elif [[ ! -r /dev/kvm || ! -w /dev/kvm ]]; then
  warn "/dev/kvm exists but your user cannot open it" \
    "sudo usermod -aG kvm $(id -un), then run 'wsl --shutdown' in PowerShell and reopen Fedora"
elif ! have qemu-system-x86_64; then
  warn "/dev/kvm is present but untested, because qemu is not installed" "sudo dnf install -y qemu-system-x86-core"
elif out=$(printf 'info kvm\nquit\n' |
  timeout 30 qemu-system-x86_64 -machine none,accel=kvm -nodefaults -display none -S -monitor stdio 2>&1) &&
  grep -q 'kvm support: enabled' <<<"$out"; then
  pass "Nested virtualization works (qemu started with KVM)"
else
  reason=$(printf '%s\n' "$out" | grep -m 1 'qemu-system-x86_64:' || printf '%s\n' "$out" | tail -n 1)
  warn "qemu could not use KVM: $reason" "$kvm_fix"
fi

printf '\nPassed: %d   Warnings: %d   Failed: %d\n' "$passes" "$warnings" "$failures"
if ((failures)); then
  printf '%sNot ready.%s Fix each FAIL above (docs/dev-setup-windows.md), then run this script again.\n' "$c_fail" "$c_off"
  exit 1
fi
if ((warnings)); then
  printf '%sReady.%s Every required check passed; the warnings are worth fixing but do not block work.\n' "$c_pass" "$c_off"
else
  printf '%sReady.%s Every check passed.\n' "$c_pass" "$c_off"
fi
exit 0
