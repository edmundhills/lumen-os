<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# services/hwd

lumen-hwd (`org.lumen.Hardware1`) knows the machine's hardware. It reports each device and its driver status, compares them with the [hardware database](../../hardware/), and offers to move a machine with an NVIDIA card to the NVIDIA image (through lumen-updated). It also runs in the install USB's live session for the hardware report.

- **Language:** Rust (zbus).
- **Runs as:** its own system user on the system bus, with polkit for changes. Whether every read works without root is checked at step 5.10.
- **Ships as:** RPM `lumen-hwd`, built in the image's `build-rust` stage.
- **Steps:** 5.10; comparing with the hardware database at 6.11.

Spec: [Hardware report (live USB)](../../docs/spec.md#hardware-report-live-usb). Architecture: [lumen-hwd](../../docs/architecture.md#lumen-hwd-orglumenhardware1).
