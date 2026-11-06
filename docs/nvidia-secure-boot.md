<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# NVIDIA's driver and Secure Boot: enrolling Lumen's key

Lumen's NVIDIA edition (`lumen-nvidia`, and `lumen-gaming-nvidia` from step 1.12b) carries NVIDIA's driver for GeForce 16 and 20 cards and newer (Turing and later). With Secure Boot on, your computer only runs a driver signed by a key it trusts. Lumen signs NVIDIA's driver with its own key, so you tell your computer once to trust that key. This is called enrolling a MOK (Machine Owner Key). It takes about two minutes and one restart.

Until the key is enrolled, Lumen uses the open nouveau driver instead: the desktop works, but games and apps that need NVIDIA's driver run slowly or not at all. Nothing breaks if you do this later.

Settings > Drivers & Hardware will do the first step for you and explain the rest (Phase 5). Until then, follow the steps below. They are what step 1.11c's boot test and ADRs [0021](decisions/0021-module-signing-key.md) and [0022](decisions/0022-nvidia-edition.md) describe.

## Enrol the key

1. Open Konsole and run:

   ```bash
   sudo mokutil --import /usr/share/pki/lumen/module-signing.der
   ```

   Type your password for `sudo`. Then mokutil asks for a one-time password, twice. Choose something short that you can type on the next screen; you need it only once, at the next restart, and it isn't your account password.
2. Restart the computer. Before Lumen starts, a blue screen says "Perform MOK management". Press any key within 10 seconds; if you miss it, Lumen starts as before, and you can begin again at step 1.
3. Choose **Enroll MOK**. To check the key first, choose **View key 0**: it should say "Lumen OS kernel module signing". Then choose **Continue**, then **Yes**.
4. Type the one-time password from step 1 and press Enter. You have three tries; if all three fail, begin again at step 1.
5. Choose **Reboot**.

## Check that it worked

After the restart, in Konsole:

```bash
mokutil --test-key /usr/share/pki/lumen/module-signing.der
cat /proc/driver/nvidia/version
```

The first says the key "is already enrolled". The second shows NVIDIA's driver version; if it says "No such file or directory", the driver isn't loaded yet: check that the card is Turing or newer, and that the first command says the key is enrolled.

## Check that the key is Lumen's

Anyone could make a key with the same name. Before step 3, you can compare its fingerprint with the one Lumen publishes in [ADR 0021](decisions/0021-module-signing-key.md), "Follow-up":

```bash
openssl x509 -inform DER -in /usr/share/pki/lumen/module-signing.der -noout -fingerprint -sha256
```

The key comes with the image, which Lumen signs, and bootc checks that signature before it installs an update, so a key in `/usr/share/pki/lumen` is Lumen's unless the image was tampered with on your own computer.

## Remove the key

If you leave the NVIDIA edition, or Lumen announces a new key, remove the old one:

```bash
sudo mokutil --delete /usr/share/pki/lumen/module-signing.der
```

Choose a one-time password again, restart, and at the blue screen choose **Delete MOK**, **Yes**, and type the password.

## With Secure Boot off

The driver loads without the key. Lumen keeps Secure Boot on and the kernel locked down (spec, "Spec: security model"), so turn Secure Boot off only if you know why you need to.
