<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# apps/hwreport

The hardware report (`org.lumen.HardwareReport`) shows, before someone installs Lumen, how well their computer will work. It opens when the install USB's live session starts. It lists each device (graphics, Wi-Fi, fingerprint reader, webcam, audio, sleep, firmware and Secure Boot) as green, amber or red, with a plain-English reason and any workaround. After install it suggests the NVIDIA driver or the gaming edition where they fit.

- **Language:** C++ and QML (Qt 6).
- **Talks to:** lumen-hwd (`org.lumen.Hardware1`), which gathers the facts and compares them with `hardware/hardware.json`.
- **Ships as:** RPM `lumen-hwreport`, built in the image's `build-apps` stage.
- **Steps:** 6.11 and 6.12. If step 1.8b or 1.8c had to fall back to `anaconda-iso`, there is no live session to run in, and the owner decides about it first (ADR 0002).

Spec: [Hardware report (live USB)](../../docs/spec.md#hardware-report-live-usb). Architecture: [4.7 Apps](../../docs/architecture.md#47-apps).
