<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0021. Sign out-of-tree kernel modules with Lumen's own key, which users enrol as a MOK

- Status: **Accepted** (2026-11-01), at step 1.11a.
- Deciders: lead engineer (Claude). The owner makes the key ([How the key is made and kept](#how-the-key-is-made-and-kept)) and reviews this at the Phase 1 acceptance (step 1.17).

## Context

The spec's `lumen-nvidia` image has NVIDIA's "proprietary driver as signed kmod, built with akmods in CI", and its security model says "NVIDIA and other out-of-tree kmods signed with our key, enrolled via MOK on first boot; kernel lockdown stays on". Facts, read on 2026-11-01:

- **Under Secure Boot the kernel loads only signed modules.** Lumen's kernel runs locked down (`integrity`, ADR 0001's follow-up), and it trusts Fedora's own key and the keys the user has enrolled as MOKs, Machine Owner Keys, which shim's MokManager asks the user to confirm at the next start. NVIDIA's modules are built outside Fedora, so Lumen must sign them with a key of its own.
- **A leaked key is a kernel-level risk** (risk 7): anyone holding it can sign modules that every machine with it enrolled will load. Replacing it means every user enrols the new one.
- **Universal Blue's signed-akmods pipeline** (`ublue-os/akmods` at `6d6d70c`), which the risk register names as prior art, uses self-signed RSA 4096 certificates with SHA-256, critical `CA:FALSE` and the key usage Digital Signature, valid for about 100 years, which Fedora's kernels accept once enrolled. Its pull-request builds sign with a committed test key when the real one is absent, and during a change of key it signs each module with both keys (`openssl cms` with two signers, then the kernel's `sign-file -s`).
- **The kernel ignores a certificate's dates** when it checks a module's signature, so a short validity only makes users enrol again.
- **GitHub environments** keep secrets for the jobs of one branch, as `image-signing` does for the image key (ADR 0008).

## Decision

1. **One RSA 4096 key**, with a self-signed X.509 v3 certificate for `O=Lumen OS, CN=Lumen OS kernel module signing`, SHA-256, critical `CA:FALSE`, key usage Digital Signature, valid 100 years: Universal Blue's profile. The owner makes it once with `image/nvidia/make-module-key.sh`, which runs openssl in the lint container with no network; openssl encrypts the private key with a password the owner chooses.
2. **The key stays with the owner and in one GitHub environment.** The environment `module-signing`, limited to the branch `main`, holds the encrypted key (`MODULE_SIGNING_KEY`) and its password (`MODULE_SIGNING_PASSWORD`); the owner keeps an offline backup, and nothing else has it. It is separate from `image-signing`, so each key opens only for the job that uses it.
3. **The certificate is public and in the repository**, as `image/nvidia/module-signing.der`. `image/nvidia/module_key.py` checks its profile, and `image/test_module_key.py` checks the committed one in `just test`.
4. **Only main signs with it** (architecture 9.1, rule 5). Builds of other branches and pull requests sign the same way with a throwaway key made in the build, so the signing path is tested on every build, and their images are never published (step 1.11b).
5. **Signing happens apart from the build of the modules.** Step 1.11b builds NVIDIA's modules with akmods without the key, then signs them with the kernel's `sign-file` in a step of their own, which gets the key as a build secret that no layer keeps. NVIDIA's build scripts never see the key.
6. **Changing the key**, planned or after a leak: make a new key the same way; sign modules with both keys for a while, as Universal Blue does, and ship both certificates; have lumen-hwd ask users to enrol the new one (Phase 5) and, after a leak, to remove the old one (`mokutil --delete`); then sign with the new key only. Write down here what was done.

## Consequences

- NVIDIA's modules load on Lumen only once the user has enrolled Lumen's certificate; lumen-hwd explains that before switching (steps 1.12 and 5.10).
- The key is a long-lived secret with kernel-level reach. Its safety rests on the owner's backup and on the environment's branch rule; the steps below and risk 7 say how to keep it.
- Until the owner makes the key, builds of `main` can't publish an NVIDIA image (step 1.11c). Everything else, and every branch build, goes on.

## How the key is made and kept

The owner does this once, in WSL and on GitHub. The private key and its password never go into the repository or to Claude.

1. In WSL, in the project folder, check out a commit that has this step (`git fetch origin` and `git checkout claude/progress-next-step-cvyy8f`, or `main` once that branch is merged). Make sure the lint container is current (`just lint` builds it). Then:

   ```bash
   bash image/nvidia/make-module-key.sh ~/lumen-module-key
   ```

   openssl asks for a PEM pass phrase twice. Choose a long one and keep it in your password manager. The script writes `module-signing.key` (the private key, encrypted with the pass phrase) and `module-signing.der` (the certificate) to `~/lumen-module-key`, checks the certificate and prints its SHA-256 fingerprint. Note the fingerprint.
2. On GitHub, open the repository's **Settings > Environments > New environment**, name it `module-signing`, and press **Configure environment**. Under **Deployment branches and tags**, choose **Selected branches and tags**, press **Add deployment branch or tag rule**, keep **Branch**, enter `main` and press **Add rule**. Under **Environment secrets**, press **Add environment secret** twice: `MODULE_SIGNING_KEY` with the whole of `module-signing.key` (`cat ~/lumen-module-key/module-signing.key` prints it, from the `BEGIN` line to the `END` line), and `MODULE_SIGNING_PASSWORD` with the pass phrase.
3. Put the certificate in the repository: `cp ~/lumen-module-key/module-signing.der image/nvidia/module-signing.der`, commit it with your sign-off (`git commit -s`) and push it to the branch you checked out. Or tell Claude its fingerprint and paste the output of `base64 -w0 ~/lumen-module-key/module-signing.der`; Claude then commits it and checks that the fingerprint matches.
4. Copy `module-signing.key` to an offline backup, such as the USB drive that holds the image key, with the pass phrase in your password manager. Then delete it from WSL: `rm ~/lumen-module-key/module-signing.key`.

## Follow-up

- 2026-11-01: `make-module-key.sh`'s profile tried in a cloud session with a throwaway key: `module_key.py` accepts it, and rejects a 2048-bit key, a CA, a non-critical constraint, another name and a key only for encipherment (`image/test_module_key.py`).
