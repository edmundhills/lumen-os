<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0007. Re-chunk the image with rpm-ostree, against a download budget

- Status: **Proposed** (2026-10-28). Built in step 1.5c on the branch `claude/next-step-zfy63s`, but not yet run in CI, because GitHub refused the push. It becomes Accepted once a CI run has re-chunked the image, the checks below pass, and the budget is set from what the run measured.
- Deciders: lead engineer (Claude), at step 1.5c, which [ADR 0004](0004-phase-0-review.md) left the choice of tool to. The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

bootc updates a system by downloading the image layers it doesn't have yet ([risk 14](../risks.md#14-updates-download-too-much)). How much a Lumen update downloads today, measured on 2026-10-28 from the manifests of the four `dev` builds on ghcr.io:

- The image has 262 layers, about 3.0 GiB compressed: Kinoite's 257 and five from Lumen's build.
- A rebuild with no change to the image (`dev-44.20261028` to `.1`, a commit that changed only documents) downloads **113 MiB**. CI builds from scratch, so dnf runs again and writes a new 113 MiB layer with the same packages in it.
- A base bump (`.2` to `.3`, Kinoite 44.20261027.0 to 44.20261028.0) downloads **487 MiB** in 12 layers: 10 of Kinoite's, the dnf layer again, and the small layers after it.
- `.1` to `.2` downloaded **all 3,082 MiB**, with no change to the content. From `.2` on, Podman reused Kinoite's zstd-compressed layers from the copy on ghcr.io instead of compressing them again with gzip, so every layer got a new digest. How layers are compressed is part of what users download.

Three tools re-chunk a bootc image. Checked on 2026-10-28, in their source code where their documentation was silent:

1. **`rpm-ostree compose build-chunked-oci`**, Fedora's documented tool. It reads an image from Podman's storage and writes it again, with each package's files in that package's layer, packed into at most `--max-layers` layers. Since rpm-ostree 2026.2, `--previous-build` takes an earlier build and keeps its packing: each package stays in the layer it was in, and new packages go into a layer kept empty for them. It reads only the earlier build's manifest, where it recorded each layer's packages in the annotation `ostree.components`. It keeps the image's settings and labels (its `config`), and replaces or adds only `ostree.commit`, `ostree.final-diffid`, `ostree.bootable` and `containers.bootc` (rpm-ostree's `compose.rs`, and ostree-ext's `encapsulate.rs` in the bootc repository). Kinoite 44 ships rpm-ostree 2026.3, so it can run from the image itself, at exactly the base's version.
2. **chunkah** (`coreos/chunkah`, 0.7.1), meant to succeed it. It groups files by content, isn't tied to RPM or to bootc, and Fedora's `bootc-base-imagectl rechunk --chunkah` can use it. But it has no option to keep an earlier build's packing, its documentation says packing for bootable images "still needs tuning", it loses the image's labels unless they are passed back in, and Kinoite doesn't ship it, so it would be another image to pin and trust.
3. **`hhd-dev/rechunk`**, the GitHub Action Universal Blue uses. It wraps rpm-ostree's chunking with its own handling of the earlier build, from before rpm-ostree could do either itself. It is a third-party action with an image of its own to pin and trust.

What shaped the design:

- rpm-ostree stops with an error when the earlier build has a layer without `ostree.components`. Builds made by `podman build`, such as today's `dev`, have none, and neither does Kinoite. The first re-chunked build must start a fresh packing.
- rpm-ostree puts every file no package owns in one layer, together with the initramfs. Files that change with each build, such as the rpm database and caches that package scripts regenerate, would take the initramfs along every time. A file marked with the extended attribute `user.component` goes into a layer of its own instead. With Ubuntu's Podman 4.9.3, which the CI runners use, an attribute set in a `RUN` step stays on the file in the image and in its layer (checked on 2026-10-28).
- `/usr/lib/os-release` belongs to a Fedora package, and Lumen writes its build version into it, so that package's layer, and the other packages packed with it, would change with every build.
- rpm-ostree can write the image to Podman's storage or as an OCI layout, a folder of compressed layers. Pushing from Podman's storage compresses the layers again and may drop their annotations. The OCI layout can be pushed as it is.

## Decision

1. **The tool is `rpm-ostree compose build-chunked-oci`**, run from the built image itself by `image/rechunk.sh`. It writes an OCI layout with gzip-compressed layers, format version 2 (each layer lists its parent folders, which rpm-ostree's documentation recommends for reproducible layers), and at most 256 layers of packages, as many as Kinoite has.
2. **Each build keeps the packing of the newest build on ghcr.io**, `dev`, read by digest without logging in. While `dev` isn't re-chunked (`image/rechunk.py chunked`), the build packs afresh. That happens once, after this lands.
3. **Files that change on their own get their own layer.** `image/layer_hints.py` marks them with `user.component` in the `lumen` stage: the initramfs, which changes only with Kinoite's, and os-release, which changes with every build. More can be added to its list when a measurement shows the need.
4. **The re-chunked image is checked before anything uses it.** It must have the same labels and settings as the built image, apart from the new ostree commit, and the base image named in two labels, `org.opencontainers.image.base.name` and `.base.digest`, which Podman wrote as manifest annotations and re-chunking would otherwise drop. It must also pass `image/check-image.sh` and `bootc container lint` again.
5. **skopeo pushes the OCI layout unchanged** (`--preserve-digests`), so the digest CI measured and checked is the digest users get, and step 1.6 signs.
6. **Every CI run measures the update** from `dev` to the new build: the layers `dev` lacks, by size and the packages in them, on the run's summary page. Until there is a `stable` channel, `dev` is what users have; step 9.2 moves the comparison to `stable`.
7. **The download budget applies to builds on the same base image.** A build whose update from `dev` downloads more than `DOWNLOAD_BUDGET_MIB` (in `.github/workflows/build-image.yml`) fails, on pull requests as on `main`. When the base image changed, the size is reported but not held to the budget, because it is mostly Fedora's updates; the base workflow's weekly pull request shows it. The budget is **150 MiB for now**, a guess from the measurements above. Step 1.5c sets it from the first CI runs: the rebuild of an unchanged commit, plus room for a typical change.

## Consequences

- An update that changes a few packages downloads those packages' layers, the ostree commit layer (the metadata of every file and folder, 7 MiB on Kinoite), and the layers that change with every build. What the last ones weigh is what the first CI run measures.
- The first `dev` build after this lands downloads in full once, because none of its layers match the previous build's.
- Each CI run takes longer: re-chunking, copying the result into Podman's storage, and checking it again. The first run measures how much.
- The layers are gzip, not zstd as Kinoite's are, so Lumen's image doesn't share layers with Kinoite on ghcr.io. Users never had Kinoite's layers, so they download nothing more for it.
- A Fedora release upgrade or a change of rpm-ostree's packing still moves most packages, and that update is large. Raising `--max-layers` also starts a fresh packing.
- If rpm-ostree changes the labels it writes, the check fails and names the label, and someone decides whether to accept it (`ADDED` in `image/rechunk.py`).
- **Revisit** when Kinoite ships chunkah, or chunkah learns to keep an earlier build's packing, since Fedora is moving to it ([risk register, watch list](../risks.md#watch-list)).
