<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Versions

What Lumen builds on: the current Fedora release and the Kinoite image Lumen starts from, read with skopeo on 2026-10-27 (step 0.7). Step 1.2 pins `image/Containerfile` to a Kinoite digest, and from step 1.5b the base workflow moves that pin every week ([How the pins move](#how-the-pins-move)). The Containerfile is the source of truth: the `# Pinned:` line above its `FROM` line names the build in use, with its KWin, Plasma and Qt, and each bump's pull request lists what changed. The tables below are the reading of 2026-10-27; read them again when a new Fedora release or a Plasma feature release arrives.

## Base image

| What | Value |
| --- | --- |
| Fedora release | **44**, the current release (Bodhi lists it as `current`). Fedora 45 is in final freeze; its target release date is 2026-11-03 |
| Image | `quay.io/fedora-ostree-desktops/kinoite:44`, build `44.20261027.0`, made 2026-10-27 at 03:13 UTC |
| Digest to pin (the multi-architecture index) | `sha256:9f71aa8ed1520cde0d09514cc46c54d01d69af79948de17ea988155dfe0e5e18` |
| x86_64 image in that index | `sha256:76364fb3f569222e737584da13f18213b5917e90b9654a47dd0f409ef9c84dd3`: 257 layers, 2.9 GiB compressed |
| aarch64 image in that index | `sha256:379fe2167cf32ca544944cdfa6a36b50693343d5f62775e4ab0eb4c608f11bda` |

## Packages in the image

From the x86_64 image. The KWin and Plasma versions are the ones lumen-glass, the window decoration and lumen-shell must be built against ([architecture 9.4](architecture.md#94-matching-the-base-image-exactly)).

| Component | Version | Read from |
| --- | --- | --- |
| **KWin** | **6.7.5** | `kwin-common` and `kwin-libs` 6.7.5-1.fc44, built from the same source package as `kwin` |
| Plasma | 6.7.5 | `plasma-workspace` and `plasma-desktop` 6.7.5-1.fc44 |
| KDE Frameworks | 6.31.0 | `kf6-ktexteditor` and `kf6-kunitconversion` 6.31.0-1.fc44 |
| Qt | 6.11.2 | `qt6-qtbase` 6.11.2-3.fc44 |
| Linux kernel | 7.2.12 | `ostree.linux` label: 7.2.12-200.fc44 |
| Mesa | 26.2.5 | `mesa-dri-drivers` 26.2.5-1.fc44 |
| systemd | 259.10 | `systemd` 259.10-1.fc44 |
| bootc | 1.17.1 | `bootc` 1.17.1-1.fc44 |
| rpm-ostree | 2026.3 | `rpm-ostree` 2026.3-2.fc44 |
| Flatpak | 1.18.4 | `flatpak` 1.18.4-1.fc44 |
| Podman | 5.8.9 | `podman` 5.8.9-1.fc44 |

## Fedora 45

The Fedora 45 Kinoite build of the same day (`45.20261027.0`, a pre-release) has the same KWin and Plasma (6.7.5), Qt (6.11.2) and KDE Frameworks (6.31.0), with kernel 7.2.11. Moving to 45 therefore doesn't change what lumen-glass is built against. Fedora 44 is supported until 2027-06-02.

Step 1.2 read the versions again on 2026-10-27: Fedora 45 was still in final freeze and `kinoite:44` still pointed at the digest above, so `image/Containerfile` pins it. Once Bodhi lists Fedora 45 as current, the base workflow's next run moves the pin to `kinoite:45` (or run it by hand from the Actions tab), because the spec says to build on the current Fedora; the release train then decides when stable gets it (ADR 0004, Q14). On 2026-10-28 Bodhi still listed Fedora 45 as frozen. The lint container stays on Fedora 44 until someone moves it by hand.

## Things to know

- **A pinned digest stops working after about four weeks.** Every dated Kinoite build carries the label `quay.expires-after: 4w`, so quay.io deletes its tag four weeks after the build: on 2026-10-27 the oldest dated Fedora 44 tag was `44.20260930.0`. Once the moving `44` tag has moved on as well, no tag refers to the image, and quay.io can delete it, after which it can't be pulled by its digest. The pin must be bumped often, and old builds need their own copy of the base ([risks, watch list](risks.md#watch-list)). From step 1.5b the base workflow bumps the pin every week and copies each pinned base to ghcr.io ([ADR 0004](decisions/0004-phase-0-review.md), [How the pins move](#how-the-pins-move)).
- Fedora's own registry drops old digests too: `quay.io/fedora/fedora` deleted the lint container's pinned `fedora:44` within about a day of a newer build, and `registry.fedoraproject.org`, which the lint container now uses, keeps them longer but for an unknown time. The base workflow handles that pin the same way.
- Fedora's mirrors keep only the release-day build and the newest update of each package, so the `-devel` packages for an older pin may have to come from Koji ([architecture 9.4](architecture.md#94-matching-the-base-image-exactly)).
- Other pinned versions live next to the code that uses them: the lint container's base and tools in `tests/lint/Containerfile`, and the CI actions and tools in `.github/workflows/`.

## How the pins move

The base workflow (`.github/workflows/base.yml`, step 1.5b) keeps two pins current: Kinoite in `image/Containerfile` and the lint container's Fedora in `tests/lint/Containerfile`. `image/bump_bases.py` reads and rewrites them, and `image/copy-bases.sh` copies them.

- **Every Monday** at 05:17 UTC, or when run by hand from the Actions tab, it reads the newest build of each pinned tag with skopeo, and for Kinoite the newest Fedora release that Bodhi lists as current. If anything moved, it rewrites the `FROM` and `# Pinned:` lines, pushes the branch `bump-bases`, copies the new bases to ghcr.io, starts the lint and image workflows on the branch, and opens or updates a pull request that lists the old and new builds. It starts the workflows itself because a pull request a workflow opens starts no other workflow.
- **The owner reviews and merges** the pull request; its commit is the workflow's and has no sign-off ([CONTRIBUTING.md](../CONTRIBUTING.md#sign-off-every-commit-dco)). If the image build fails, for example because a new Fedora release dropped a package that `image/packages.toml` names, fix it on the branch: once a person has added a commit, the workflow leaves the pull request alone until it is merged or closed.
- **Every pinned base is copied** to `ghcr.io/edmundhills/<name>:<tag>-<first 12 digits of the digest>`, for example `kinoite:44-9f71aa8ed152`, with `skopeo copy --all --preserve-digests`, so the copy has the same digest. The bump copies its new bases straight away, because its pull request may wait longer than quay.io keeps them, and every merge to main that changes a pin, and every Monday run, copies whatever main pins. A Kinoite copy is about 5.8 GiB, for two architectures. The copies must be public.
- **CI pulls from the copies first.** The image and lint workflows write `/etc/containers/registries.conf.d/50-lumen-bases.conf` (`bump_bases.py mirrors`), which makes Podman pull each pinned base from its copy, by digest only, and from the original registry when the copy is missing. Checked with Ubuntu 24.04's Podman 4.9.3, which the runners use, on 2026-10-28.
- To build an old commit in WSL after quay.io has deleted its base, write the same file there: `python3 image/bump_bases.py mirrors ghcr.io/edmundhills image/Containerfile tests/lint/Containerfile | sudo tee /etc/containers/registries.conf.d/50-lumen-bases.conf`.
- GitHub turns off a public repository's scheduled workflows after 60 days with no activity in it. If that happens, turn the base workflow back on under Actions.

## How to read them again

In WSL or CI. skopeo reads the registry directly, so nothing is downloaded but metadata:

```bash
# Is Fedora 45 out yet? "current" means released; "frozen" means in final freeze
curl -fsS https://bodhi.fedoraproject.org/releases/F45 | python3 -m json.tool | grep '"state"'

# Digest, build and kernel of the newest Fedora 44 Kinoite
skopeo inspect --no-tags --format '{{.Digest}} {{index .Labels "org.opencontainers.image.version"}} {{index .Labels "ostree.linux"}}' docker://quay.io/fedora-ostree-desktops/kinoite:44

# Package versions: rpm-ostree names most layers after the package in them
skopeo inspect --config docker://quay.io/fedora-ostree-desktops/kinoite@sha256:<digest> | grep -oE '(kwin-common|plasma-workspace|qt6-qtbase|kf6-ktexteditor)-[0-9][^"]*'
```

Smaller packages share layers named only "N components", so a package missing from that list isn't necessarily missing from the image. To read any package's version, download the image (2.9 GiB) and ask rpm: `podman run --rm quay.io/fedora-ostree-desktops/kinoite@sha256:<digest> rpm -q kwin`.
