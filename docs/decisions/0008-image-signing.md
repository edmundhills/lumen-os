<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0008. Sign images with a cosign key, attach a syft SBOM, and trust Lumen's images only with that signature

- Status: **Accepted** (2026-10-29), at steps 1.6 and 1.7. The first signed build on main is still to come; [Follow-up](#follow-up) records it.
- Deciders: lead engineer (Claude). The owner makes the key ([How the key is made and kept](#how-the-key-is-made-and-kept)) and reviews this at the Phase 1 acceptance (step 1.17).

## Context

The spec signs the images with cosign, has bootc check the signatures before it stages an update (policy in `/etc/containers/policy.json`), publishes an SBOM made with syft, and asks Phase 1 to "configure /etc/containers/policy.json so the system only accepts our signed images". The architecture ([9.7](../architecture.md#97-versions-tags-and-keys)) keeps the image key in a GitHub secret that only `main` can use, and ships its public half in the image.

What the tools do, checked on 2026-10-29 in their source code at the versions named, and by running them:

- **Kinoite 44 trusts every image.** Its `/etc/containers/policy.json` (from containers-common 0.67.2) accepts any image by default, it ships no signing keys, and its `registries.d` only names Red Hat's signature servers. Fedora signs Kinoite on quay.io itself with a cosign key, but configures nothing to check it.
- **Where the tools look.** Fedora 44's skopeo 1.22.3 and Podman 5.8.9 use containers/image 5.39.3, which reads `policy.json` and `registries.d` from `/etc/containers` only, or from the user's `~/.config/containers` when that exists. Fallbacks in `/usr/share` arrive in containers/image 5.40.
- **bootc pulls through containers/image.** bootc 1.17.1 opens every image through skopeo's image proxy, which applies `policy.json` on every pull, whatever transport the deployment records. The transport adds one check: `ostree-image-signed` refuses a policy whose default accepts any image. `bootc upgrade` keeps the recorded transport; `bootc switch` without `--enforce-container-sigpolicy` records `ostree-unverified-registry`; `bootc install` records the signed one when its install config says `enforce-container-sigpolicy = true` (bootc 1.15.2 and later). Anaconda's `ostreecontainer` command always records the unverified one.
- **The only signature format containers/image reads** is cosign's original one: a simple signing payload in an OCI manifest under the tag `sha256-<digest>.sig`, in the image's own repository, and only for registries that `registries.d` marks `use-sigstore-attachments: true`. It can't read the Sigstore bundle format or OCI referrers; container-libs issue #388 asks for that and is open. A cosign signature names only the repository, so the policy must use `matchRepository`: the default identity rule refuses it, by tag and by digest.
- **cosign 3 writes the other format by default.** cosign 3.1.4, the newest (2026-10-20), writes a Sigstore bundle, which on a registry without the referrers API, such as ghcr.io, goes under the tag `sha256-<digest>`. containers/image never sees it and says "A signature was required, but no signature exists" (rpm-ostree issue #5509). `--new-bundle-format=false` writes the old format, and cosign accepts it only together with `--use-signing-config=false`. Both are deprecated, and the cosign 3.1.1 notes say cosign 4 removes deprecated flags. Universal Blue's Aurora and Bazzite sign this way with cosign 3.1.
- **The public transparency log.** By default cosign also records each signature in Sigstore's public log, Rekor v1. containers/image ignores the log unless the policy names a Rekor key. Rekor stores attestations only up to a size limit, and cosign's own help discourages relying on it to store them.
- **Keyless signing** would sign with a short-lived certificate for the workflow's GitHub identity, so there would be no key to keep. containers/image can check such certificates only against an e-mail address (its `fulcio` requirement needs `subjectEmail`), and GitHub's workflow certificates carry a URI instead. It would also need Fulcio's and Rekor's keys in the image, and Sigstore rotates them.
- **One policy file for every tool.** Podman, Toolbx and distrobox read the same `policy.json`. Toolbx's Fedora image (`registry.fedoraproject.org/fedora-toolbox:44`) is unsigned, so a policy that refused unsigned images from other registries would stop Toolbx and distrobox. Refusing local transports such as `containers-storage:` and `oci:` would stop `bootc install` from Podman, bootc-image-builder and Anaconda. Universal Blue's policy and Fedora's own instructions for signed Kinoite keep both open.
- **GitHub.** A free public repository can have environments with secrets and a deployment branch rule. A called workflow gets an environment's secrets only when its caller passes them by name, and an empty string otherwise. `environment: {deployment: false}` uses an environment without recording a deployment (since 2026-03-19). ghcr.io has no referrers API; the anonymous pull token reads `.sig` tags.
- **syft 1.55.0** reads Lumen's rpm database at `/usr/share/rpm/rpmdb.sqlite`, where rpm-ostree keeps it, from an OCI layout (`oci-dir:`), and writes SPDX 2.3 JSON. By default it also records every file the packages own, which for the image's 470,000 files makes an SBOM of hundreds of megabytes; `SYFT_FILE_METADATA_SELECTION=none` leaves only the packages.

## Decision

1. **One cosign key pair, kept in a GitHub environment.** The owner makes it on their own machine, with the cosign from the lint container and no network: an ECDSA P-256 key, encrypted with a password. The private key and its password are the secrets `COSIGN_PRIVATE_KEY` and `COSIGN_PASSWORD` of the environment `image-signing`, which only `main` may use, with an offline backup. The public key ships in the image as `/usr/share/pki/containers/lumen.pub`, in `/usr` so that it always comes with the image, even where someone edited `/etc/containers/policy.json`. Keyless signing is out until containers/image can check a GitHub workflow identity.
2. **Signatures in the format bootc reads.** `image/sign.sh` signs with `--new-bundle-format=false --use-signing-config=false --tlog-upload=false`, and attaches the SBOM as an `spdxjson` attestation the same way (tag `sha256-<digest>.att`). It doesn't pass `--yes`: with no log cosign never asks, so a setting that sent a signature to the public log would stop CI at cosign's question. cosign is pinned once, in `tests/lint/Containerfile`, and CI installs the same version from there.
3. **No transparency log.** The key in the image is what systems trust, and containers/image doesn't look at the log. Leaving it out removes a public service from the signing path and keeps a several-megabyte SBOM out of a public, permanent log. Checks with cosign therefore say `--insecure-ignore-tlog=true`. Revisit together with the bundle format.
4. **CI signs in a job of its own, and `dev` moves last.** In `.github/workflows/build-image.yml`:
   - Every build makes the SBOM from the re-chunked layout, checks that it lists exactly the image's RPM packages (`image/sbom.py`), and keeps it with the run for 30 days.
   - Builds of main push the tags that never move (`dev-<version>`, `sha-<commit>`).
   - The `sign` job opens the `image-signing` environment on a runner of its own, so the key never reaches the runner that ran dnf and rpm-ostree. It checks that the image's trust policy refuses the unsigned digest, signs it and attaches the SBOM, checks both with the public key from the image (`image/sign.sh verify`) and checks that the trust policy now accepts the image. Only then does it move `dev`, so a system that follows `dev` never meets an unsigned image.
5. **The trust policy names Lumen's images.** `/etc/containers/policy.json`:
   - rejects by default, so bootc's signed transport accepts it;
   - requires a `sigstoreSigned` signature by `lumen.pub`, with `matchRepository`, for each of Lumen's four repositories: `ghcr.io/edmundhills/lumen`, `lumen-nvidia`, `lumen-gaming` and `lumen-gaming-nvidia`. They are listed one by one rather than as `ghcr.io/edmundhills`, which would also cover the unsigned copies of the base images;
   - accepts other registries' images, and every local transport (`containers-storage`, `dir`, `docker-archive`, `docker-daemon`, `oci`, `oci-archive`, `sif`, `tarball`), as Fedora does.

   `/etc/containers/registries.d/lumen.yaml` turns on `use-sigstore-attachments` for the same four. This is how Lumen reads "only accepts our signed images": an image under Lumen's name is accepted only with Lumen's signature. Read literally for every image, it would stop Toolbx and distrobox, which the spec requires.
6. **Installs check signatures from the start.** `/usr/lib/bootc/install/20-lumen.toml` sets `enforce-container-sigpolicy = true`, so `bootc install`, bootc-image-builder and Anaconda's `bootc` kickstart command record `ostree-image-signed`.
7. **The SBOM** is syft 1.55.0's SPDX JSON, packages only, made from the layout that is pushed.
8. **Tests.** `image/trust.py` checks the policy, the key and `registries.d` in `just lint` and in the image (`check-image.sh`, which also checks the install setting). `image/test_signatures.py` runs a registry inside the lint container that answers for ghcr.io, signs test images with `image/sign.sh` and the pinned cosign, and pulls them with Fedora 44's skopeo and the overlay's settings: signed images are accepted by tag, by digest and after a tag moves; unsigned ones, other keys and a signature made for another variant are refused; other registries and local transports are unaffected. `image/sbom.py` has unit tests too.

## Consequences

- The owner makes the key and the environment once, before this reaches main. Until then the `sign` job fails, `dev` stays where it is, and the dated and `sha-` tags of that build are unsigned, which Lumen systems refuse. After a failed `sign` job, fix the cause and use "Re-run failed jobs": a new run would find the commit already pushed.
- Each signed build adds two tags to the package on ghcr.io, `sha256-<digest>.sig` and `.att`, which GitHub counts as versions. When step 9.1 deletes old `dev` builds, it must delete their signature tags too, or they pile up.
- The `sign` job downloads the whole image once more, about 3 GiB, for skopeo's check: about a minute.
- A signature holds for its repository, not for a tag. Someone who controlled the registry could offer an older signed build under a newer tag, or a `dev` build as `stable`. Step 9.1 should decide whether channels need their own identity or key.
- Anything that switches images must pass `--enforce-container-sigpolicy`, or bootc records the unverified transport: `lumen-updated`'s `SwitchTo` and `SwitchVariant` (Phase 5). If the install media at step 1.8 uses Anaconda's `ostreecontainer` command, its `%post` must switch to the signed transport, as Bazzite's does (`bootc switch --mutate-in-place --enforce-container-sigpolicy`).
- bootc merges `/etc` on every update, so a system whose `/etc/containers/policy.json` was edited keeps its own copy, and root's `~/.config/containers/policy.json` replaces it entirely. A Health check (steps 5.8 and 5.9) should notice either.
- **Replacing the key:** keep the file name. Ship the new key alongside the old one (`keyPaths`) in an image signed with the old key, sign with the new key once systems have that image, then drop the old key. Systems with an edited policy miss the change, hence the Health check. A lost key with no backup would leave every installed system unable to verify updates, hence the offline backup.
- cosign must stay on version 3 until containers/image reads Sigstore bundles. If cosign 3 stops getting fixes first, skopeo can sign instead (`skopeo copy --sign-by-sigstore-private-key`), writing the same format with containers/image's own code, and cosign only attaches the SBOM.
- **Revisit** when container-libs #388 lands in Fedora, which allows bundles and perhaps the log; and at step 8.2, whether CI should check Fedora's signature on each new Kinoite base before the base workflow pins it.

## How the key is made and kept

The owner does this once, in WSL and on GitHub. The private key and its password never go into the repository or to Claude.

1. In WSL, from the project folder, make sure the lint container is current (`just lint` builds it), then make the key in a folder of its own, with no network:

   ```bash
   mkdir -p ~/lumen-signing-key && chmod 700 ~/lumen-signing-key
   podman run --rm -it --network=none --volume ~/lumen-signing-key:/keys:Z --workdir /keys localhost/lumen-lint cosign generate-key-pair
   ```

   cosign asks for a password twice. Choose a long one and keep it in your password manager. It writes `cosign.key` (the private key, encrypted with the password) and `cosign.pub`.
2. On GitHub, open the repository's **Settings > Environments > New environment**, name it `image-signing`, and press **Configure environment**. Under **Deployment branches and tags**, choose **Selected branches and tags**, press **Add deployment branch or tag rule**, keep **Branch**, enter `main` and press **Add rule**. Under **Environment secrets**, press **Add environment secret** twice: `COSIGN_PRIVATE_KEY` with the whole of `cosign.key` (`cat ~/lumen-signing-key/cosign.key` prints it, from the `BEGIN` line to the `END` line), and `COSIGN_PASSWORD` with the password.
3. Copy the public key into the image: `cp ~/lumen-signing-key/cosign.pub image/overlay/usr/share/pki/containers/lumen.pub`, and commit it.
4. Copy `cosign.key` to an offline backup, such as a USB drive kept somewhere safe, with the password in your password manager. Then delete it from WSL: `rm ~/lumen-signing-key/cosign.key`.

## Follow-up

- 2026-10-29, the SBOM: in main's run for `2a7107c`, syft scanning the re-chunked layout with its default cataloguers ran for 3 minutes, then GitHub's runner received a shutdown signal. On the owner's PC the same full scan of the image needed about 7.6 GB of memory. `image/sbom.sh` now runs syft on the mounted image, reading only the rpm database (`--override-default-catalogers rpm-db-cataloger`). The rpm database lists every package, which is what decision 7 needs. syft is pinned in `tests/lint/Containerfile`, and CI installs it from there. `image/test_sbom.py` runs `sbom.sh` on the lint container's own files and checks the SBOM against `rpm --query --all`: 192 packages, with syft's one record of the database file. syft also lists the keys rpm trusts, as packages named `gpg-pubkey`, so `sbom.py` leaves those out on both sides.
- 2026-10-29: tested in WSL, not yet in CI. The first push from here is the first signed build; record here what its `sign` job did.
- 2026-10-29, the key: on the owner's instruction, Claude made it in the owner's WSL with the lint container's cosign 3.1.4 and no network, as step 1 says, with a random 33-byte password written to `~/lumen-signing-key/password` rather than typed. Neither the private key nor the password was shown. Claude checked that the password opens the key and that the key's public half is `cosign.pub`, which is now `lumen.pub`. The owner created the `image-signing` environment, limited to the branch `main`, and added the two secrets; Claude checked that they are there, by name. The offline backup and deleting the WSL copies (step 4) are the owner's.
