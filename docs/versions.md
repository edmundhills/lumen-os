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

**Lumen has built on Fedora 45 since 2026-11-01**, when Bodhi listed it as current and the base workflow moved the pin (pull request #4). What the repository records about it, without a new reading of the registry:

| What | Value | Recorded by |
| --- | --- | --- |
| Pinned build | Kinoite `45.20261102.0`, built 2026-11-02, index digest `sha256:d54aee1a7232e0df3db47ccbd3b15df03c3dbe953df4f0c65b4a1297925f33ad` | `image/Containerfile`, the `# Pinned:` and `FROM` lines |
| **KWin**, Plasma | **6.8.2**, a feature release on from the 6.7.5 in the tables above | The same `# Pinned:` line |
| Qt | 6.11.2 | The same line |
| Linux kernel | 7.2.13-300.fc45 on `45.20261101.0` | The boot test of 2026-11-01 ([history](history/phase-1.md), step 1.10a) |
| Mesa | 26.2.5 | [ADR 0025](decisions/0025-codecs.md), read on 2026-11-08 |

- The tables above are still the Fedora 44 reading of 2026-10-27. The pre-release Fedora 45 build of that day had the same KWin and Plasma as Fedora 44 (6.7.5), but Plasma 6.8.2 reached both releases on 2026-11-01, so what lumen-glass must be built against did change with the move. Read the tables again from a machine that can reach quay.io ([How to read them again](#how-to-read-them-again)).
- That update also showed how the pin and Fedora's mirrors can drift apart: with Kinoite still pinned at Plasma 6.7.5, installing Lumen's packages pulled Plasma 6.8.2 packages in beside KWin 6.7.5. `image/check-image.sh` now fails a build whose KWin and Plasma are different releases, and the fix is a bump of the pin.
- `kcm-fcitx5` is left out of `image/packages.toml` until Fedora 45 has a build of it for Plasma 6.8 (2026-11-01).
- The lint container stays on Fedora 44 until someone moves it by hand. Fedora 44 is supported until 2027-06-02.

## Things to know

- **A pinned digest stops working after about four weeks.** Every dated Kinoite build carries the label `quay.expires-after: 4w`, so quay.io deletes its tag four weeks after the build: on 2026-10-27 the oldest dated Fedora 44 tag was `44.20260930.0`. Once the moving `44` tag has moved on as well, no tag refers to the image, and quay.io can delete it, after which it can't be pulled by its digest. The pin must be bumped often, and old builds need their own copy of the base ([risks, watch list](risks.md#watch-list)). From step 1.5b the base workflow bumps the pin every week and copies each pinned base to ghcr.io ([ADR 0004](decisions/0004-phase-0-review.md), [How the pins move](#how-the-pins-move)).
- Fedora's own registry drops old digests too: `quay.io/fedora/fedora` deleted the lint container's pinned `fedora:44` within about a day of a newer build, and `registry.fedoraproject.org`, which the lint container now uses, keeps them longer but for an unknown time. The base workflow handles that pin the same way.
- Fedora's mirrors keep only the release-day build and the newest update of each package, so the `-devel` packages for an older pin may have to come from Koji ([architecture 9.4](architecture.md#94-matching-the-base-image-exactly)).
- CI re-chunks the image with the base's own rpm-ostree ([ADR 0007](decisions/0007-rechunking.md)), which needs version 2026.2 or later for `--previous-build`. Kinoite 44 has 2026.3.
- Other pinned versions live next to the code that uses them: the lint container's base and tools in `tests/lint/Containerfile`, and the CI actions and tools in `.github/workflows/`. Among the tools is osbuild's image-builder, which makes the qcow2: the container `ghcr.io/osbuild/image-builder-cli` of release 88.0.0, by digest, in `build-image.yml` (since step 1.8a). It releases about once a week; move the pin by hand when a release fixes something Lumen needs, until Renovate does it (step 9.2). Its predecessor's container, `quay.io/centos-bootc/bootc-image-builder`, now runs the same tool on CentOS Stream 10 ([ADR 0011](decisions/0011-disk-images.md)).
- **cosign must stay on version 3** (3.1.4 since step 1.6, pinned in `tests/lint/Containerfile`, which CI's `sign` job reads too). Fedora 44's containers/image, and so bootc, reads only cosign's original signature format, which cosign 3 writes only with flags it has marked deprecated, and which cosign 4 will drop. Move on when containers/image reads Sigstore bundles ([ADR 0008](decisions/0008-image-signing.md)). syft (1.55.0) is pinned there too, and CI installs it from there.

## How the pins move

The base workflow (`.github/workflows/base.yml`, step 1.5b) keeps two pins current: Kinoite in `image/Containerfile` and the lint container's Fedora in `tests/lint/Containerfile`. `image/bump_bases.py` reads and rewrites them, and `image/copy-bases.sh` copies them.

- **Every Monday** at 05:17 UTC, or when run by hand from the Actions tab, it reads the newest build of each pinned tag with skopeo, and for Kinoite the newest Fedora release that Bodhi lists as current. If anything moved, it rewrites the `FROM` and `# Pinned:` lines, pushes the branch `bump-bases`, copies the new bases to ghcr.io, and opens or updates a pull request that lists the old and new builds.
- **The pull request's checks are its own lint and image runs.** GitHub made them for the first bump ([#1](https://github.com/edmundhills/lumen-os/pull/1), 2026-10-28) even though the workflow's token opened it, but held them for approval, because `github-actions[bot]` had no merged contribution yet. When that happens, press "Approve workflows to run" on the pull request. It held them again for #4 (2026-11-01) and #7 (2026-11-09), after #1 had been merged, so expect to press it for every bump. The owner merged #1 without approving them; GitHub then ended the held runs as failed, with no jobs, and the merge's own runs on main were green. If GitHub makes no runs at all, the job starts lint and image on the branch itself, but those runs don't show on the pull request; look for them under Actions.
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
