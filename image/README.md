<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# image

The Lumen OS image: an OCI container image built `FROM` Fedora Kinoite and managed by bootc. It is the whole operating system, and it updates as one piece.

| Path | What it is | Step |
| --- | --- | --- |
| `packages.toml` | The package manifest: the Fedora packages Lumen keeps from Kinoite, adds and removes, by the areas of the spec's manifest | 1.1 |
| `packages.py` | Checks the manifest (`just lint`) and applies it in the `base` stage. It stops the build if the manifest doesn't match Kinoite, or if dnf removes a package the manifest doesn't list. `test_packages.py` holds its unit tests (`just test`) | 1.1 |
| `Containerfile` | The multi-stage build. Phase 1 has `base` (Kinoite plus the manifest), `lumen` (the image users get, ending with `bootc container lint`) and `live` (the live system the install ISO boots, built with `just build-live`); `devel`, the build stages and the variants come with their steps | 1.2, 1.8b |
| `overlay/` | Files copied into the image as they are: vendor defaults in `/usr/lib` and `/usr/share`, and the image's `/etc` only where a setting can live nowhere else. Never `/usr/etc` (ADR 0002) | 1.3 |
| `check-image.sh` | Checks the built image: the overlay's files and their modes, the units Lumen turns on and masks, Lumen's units valid, a Btrfs root for `bootc install`, SELinux enforcing, Discover gone, Lumen's global theme the default, os-release, the trust policy, and installs that check signatures. The `lumen` stage runs it before `bootc container lint`, and `rechunk.sh` runs both again on the re-chunked image | 1.3, 1.4, 1.5a, 1.7 |
| `build_version.py` | Works out the build version, `<Fedora release>.<build date>` with `.1`, `.2` for further builds on the same day ([architecture 9.7](../docs/architecture.md#97-versions-tags-and-keys)), for `just build-image` and CI. `test_build_version.py` holds its unit tests | 1.5a |
| `os-release.sh` | Writes Lumen's `/usr/lib/os-release` in the `lumen` stage: `ID=lumen`, `ID_LIKE=fedora`, the product version as `VERSION_ID` and the build version as `IMAGE_VERSION`. It stops the build if the product version has more than one dot, which image-builder can't read ([ADR 0011](../docs/decisions/0011-disk-images.md)); `test_os_release.py` tests that. The stage also sets the image labels, among them `org.opencontainers.image.version` | 1.5a, 1.8a |
| `bump_bases.py` | Reads and moves the pinned base images: lists them with the names of their copies on ghcr.io, writes the Podman settings that make CI pull them from those copies, and moves each pin to its newest build, and Kinoite to a new Fedora release once Bodhi lists it as current ([versions](../docs/versions.md#how-the-pins-move)). `test_bump_bases.py` holds its unit tests | 1.5b |
| `copy-bases.sh` | Copies each pinned base to ghcr.io with its digest, and checks that anyone can pull the copy. `test_copy_bases.py` tests it with a stand-in for skopeo | 1.5b |
| `rechunk.sh` | Re-chunks a built image with rpm-ostree, run from the image itself, keeping an earlier build's packing, so an update downloads only the layers whose packages changed. Then checks the result: the same labels and settings, `check-image.sh` and `bootc container lint` ([ADR 0007](../docs/decisions/0007-rechunking.md)). CI runs it after every build | 1.5c |
| `rechunk.py` | Tells whether a build is re-chunked, compares the labels before and after, and measures what an update between two builds downloads, against the budget. `test_rechunk.py` holds its unit tests | 1.5c |
| `layer_hints.py` | Marks the files that change on their own, so re-chunking gives them layers of their own: what the package step writes afresh on every build, os-release, and the overlay's files. The `lumen` stage runs it. `test_layer_hints.py` holds its unit tests | 1.5c |
| `sbom.sh` | Makes the image's SBOM with syft, from the mounted image's rpm database, as SPDX JSON. CI runs it on every build | 1.6 |
| `sbom.py` | Checks that SBOM: it must list exactly the image's RPM packages. `test_sbom.py` holds its unit tests, and runs `sbom.sh` with the pinned syft on the lint container's own files | 1.6 |
| `sign.sh` | Signs a pushed image with cosign, in the format bootc reads, attaches its SBOM as a signed attestation, and checks both with the public key ([ADR 0008](../docs/decisions/0008-image-signing.md)). CI's `sign` job runs it for builds of main | 1.6 |
| `trust.py` | Checks the trust settings: images under Lumen's names need Lumen's signature, other images are as on Fedora, the key is a public key, and `registries.d` says where the signatures are. `just lint` runs it on the overlay, and `check-image.sh` in the image. `test_trust.py` holds its unit tests | 1.7 |
| `test_signatures.py` | Tests the trust settings end to end in the lint container: a registry there stands in for ghcr.io, `sign.sh` signs test images with the pinned cosign, and Fedora's skopeo must accept Lumen's images only with Lumen's signature (`just test`) | 1.6, 1.7 |
| `check-disk.sh` | Checks a disk that image-builder made from the image, such as the qcow2 for the boot test, read-only: a GPT disk with an EFI system partition, `/boot` and a Btrfs root; shim and GRUB; one boot entry; and a deployment that follows `ghcr.io/<owner>/lumen:dev` with the signed transport, at the build's version ([ADR 0011](../docs/decisions/0011-disk-images.md)). CI runs it on every build's qcow2 | 1.8a |
| `disk.py` | The checks `check-disk.sh` runs on the partition table and the mounted partitions. `test_disk.py` holds its unit tests | 1.8a |
| `live/packages.toml` | The packages the `live` stage adds for the live session and the installer: dracut's live modules, livesys, Anaconda WebUI and its browser, GRUB's CD boot program, and the tools image-builder packs an ISO with. `packages.py` applies it as it applies `packages.toml`, and `just lint` checks it | 1.8b |
| `live/iso.yaml` | The ISO's label and boot menu, in the format of the container-native ISO contract ([ADR 0011](../docs/decisions/0011-disk-images.md)). The `live` stage installs it as `/usr/lib/bootc-image-builder/iso.yaml`, where Titanoboa and image-builder both read it | 1.8b |
| `live/check-live.sh` | Checks the built live system against the contract: one kernel with a live initramfs, shim and GRUB in `/boot/efi`, GRUB's BIOS modules, the ISO tools, `iso.yaml` (every entry boots live, with SELinux on), livesys's Plasma session, Anaconda picking Lumen's profile, WebUI's browser, and no first-run setup in the live session. The `live` stage runs it last | 1.8b |
| `test_home_snapshots.py` | Unit tests for the snapshots of `/home`: the setup script's choices, with stand-ins for `stat`, `snapper` and `restorecon`, and the template's limits against the spec (`just test`) | 1.4 |

What the overlay sets up so far:

| Path in the image | What it does | Step |
| --- | --- | --- |
| `/usr/lib/systemd/system-preset/40-lumen.preset` | Turns on firewalld, `fwupd-refresh.timer`, snapper's timers, tuned and tuned-ppd. The build applies it, and so does systemd on a new machine's first boot. The Containerfile also masks Fedora's own updaters and its countme ping | 1.3 |
| `/usr/share/plasma/look-and-feel/org.lumen.desktop/` | Lumen's interim global theme: Fedora's look, with an interim 32 px top bar (app menu, open windows, system tray, clock) in place of Kinoite's stock panel. Step 2.11 replaces the theme, step 4.2 the bar | 1.3 |
| `/etc/xdg/kdeglobals` | Makes that theme the default. KDE reads system-wide defaults only from its config folders, and `/etc/xdg` is the first | 1.3 |
| `/usr/lib/systemd/system/lumen-home-snapshots.service`, `/usr/libexec/lumen-home-snapshots` | On the first boot, makes snapper's `home` config for `/var/home` (where `/home` points) from Lumen's template, if `/var/home` is a Btrfs subvolume. Otherwise it says why there are no snapshots and exits without failing. It runs at each boot until the config exists | 1.4 |
| `/usr/share/snapper/config-templates/lumen-home` | The snapshot settings: 24 hourly, 7 daily and 4 weekly (spec, "Snapshots and backup"); everything else is snapper's default | 1.4 |
| `/usr/lib/bootc/install/20-lumen.toml` | `bootc install`, and image-builder with it, make a Btrfs root, and record the image so that its signatures are checked from the first update (`enforce-container-sigpolicy`; image-builder's qcow2 records `ostree-image-signed`, checked at step 1.8a). Compression is a mount option the installer sets ([`installer/anaconda/lumen.conf`](../installer/anaconda/lumen.conf)); bootc has no setting for it, so disks `bootc install` makes by itself aren't compressed, though image-builder's are ([ADR 0011](../docs/decisions/0011-disk-images.md)) | 1.4, 1.7, 1.8a |
| `/etc/containers/policy.json` | The trust policy: images from Lumen's four repositories on ghcr.io need Lumen's signature; other registries' images and local transports are accepted as on Fedora; anything else is refused ([ADR 0008](../docs/decisions/0008-image-signing.md)). JSON has no comments, so the ADR explains it | 1.7 |
| `/etc/containers/registries.d/lumen.yaml` | Tells containers/image to look for cosign's signatures (`sha256-<digest>.sig`) in Lumen's repositories | 1.7 |
| `/usr/share/pki/containers/lumen.pub` | The public half of the key CI signs with. The owner makes the key ([ADR 0008](../docs/decisions/0008-image-signing.md#how-the-key-is-made-and-kept)) | 1.6 |

- Kinoite is pinned by digest. Every Lumen package that links KWin or Plasma is built in a stage of this Containerfile against that exact base (CLAUDE.md, "Critical build rule"). The base workflow (`.github/workflows/base.yml`) moves the pin every week through a pull request and keeps a copy of each pinned base on ghcr.io. Leave the `# Pinned:` line above the `FROM` line in place: the workflow rewrites it.
- Everything in `overlay/` lands in the image's root folder, so `overlay/` holds only files meant for the image, and no README.
- The build copies the overlay with modes it sets itself: 0644 for files and 0755 for new folders, and 0755 for Lumen's programs in `/usr/libexec`. A Windows checkout seen from WSL shows every file as 0777, and the image must not inherit that.
- Variants: `lumen` (the default), `lumen-gaming` (step 1.10), `lumen-nvidia` (step 1.11) and `lumen-gaming-nvidia` (step 1.12, ADR 0004).

Spec: [image build and layout](../docs/spec.md#spec-image-build-and-layout). Architecture: [4.1 Base image](../docs/architecture.md#41-base-image), [9.3 Inside the image build](../docs/architecture.md#93-inside-the-image-build), [9.5 Variants](../docs/architecture.md#95-variants).
