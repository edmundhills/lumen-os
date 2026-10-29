# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Build recipes for Lumen OS. Run `just` to list them. Which ones work on a
# Windows PC in WSL and which run only in CI: docs/architecture.md, section 9.11.

set shell := ["bash", "-euo", "pipefail", "-c"]

lint_image := "localhost/lumen-lint"

# The lint and test tools run in a container built from tests/lint/Containerfile,
# so they give the same result in WSL and in CI. The container sees the
# checkout read-only and has no network.
lint_run := "podman run --rm --network=none --volume " + quote(justfile_directory() + ":/src:ro,z") + " --workdir /src"
lint_container := lint_run + " " + lint_image

# For the unit tests, ghcr.io is the container itself: image/test_signatures.py
# runs a registry there that stands in for it. LUMEN_LINT_CONTAINER tells the
# tests that need the container's own tools, such as syft, that they have them.
test_container := lint_run + " --add-host=ghcr.io:127.0.0.1 --env=LUMEN_SIGNATURE_TEST=1 --env=LUMEN_LINT_CONTAINER=1 " + lint_image

# List the recipes
default:
    @just --list

# Check licences, formatting and the links between documents
lint: _lint-image
    {{ lint_container }} bash tests/lint/run.sh

# Run the tests that work on this machine
test: _lint-image
    {{ lint_container }} bash tests/lint/selftest.sh
    {{ test_container }} python3 -m unittest discover --start-directory image

# Build the OS image with Podman. The first build downloads Kinoite (2.9 GiB)
build-image:
    version=$(python3 image/build_version.py image/Containerfile) \
    && podman build --file image/Containerfile --target lumen \
        --build-arg LUMEN_BUILD_VERSION="$version" \
        --build-arg LUMEN_COMMIT="$(git rev-parse HEAD)" \
        --tag localhost/lumen:dev .

# Build the install ISO
build-iso:
    @echo "Nothing to build yet: step 1.8 adds the ISO build, which runs in CI." >&2; exit 1

# Boot the OS image in a local VM
run-vm:
    @test -e /dev/kvm || { echo "This machine has no /dev/kvm, so it can't run VMs. The boot test runs in CI." >&2; exit 1; }
    @echo "Nothing to boot yet: step 1.9 adds the VM, using the qcow2 from step 1.8." >&2; exit 1

# Build the lint container, or reuse it if tests/lint/Containerfile hasn't changed
_lint-image:
    @podman image exists {{ lint_image }} || echo "Building the lint container. The first time takes a few minutes." >&2
    @podman build --quiet --tag {{ lint_image }} tests/lint >/dev/null
