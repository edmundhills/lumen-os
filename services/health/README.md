<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# services/health

lumen-health (`org.lumen.Health1`) runs System Health: checks such as low disk space, failed services, an update left pending too long, the firewall turned off, a worn battery, a missing driver, disk errors, broken Flatpaks and an unsynced clock. Each gives a plain-English result and a Fix button. When Windows is on the same machine, it also runs the dual-boot checks.

- **Language:** Rust (zbus).
- **Runs as:** its own system user on the system bus, with polkit for fixes. Whether every check works without root is checked at step 5.8.
- **Ships as:** RPM `lumen-health`, built in the image's `build-rust` stage.
- **Steps:** 5.8 and 5.9; the dual-boot checks at 7.10.

Spec: [System Health checks](../../docs/spec.md#system-health-checks-each-with-a-plain-english-result-and-a-fix-button). Architecture: [lumen-health](../../docs/architecture.md#lumen-health-orglumenhealth1).
