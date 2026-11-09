# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for the Flatpak apps Lumen comes with (steps 1.13 and 1.14a, ADRs
# 0024 and 0025): the preinstall list Flatpak reads, and the timer and service
# that run it. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import configparser
import unittest
from pathlib import Path

OVERLAY = Path(__file__).resolve().parent / "overlay"
PREINSTALL = OVERLAY / "usr/share/flatpak/preinstall.d/lumen.preinstall"
UNITS = OVERLAY / "usr/lib/systemd/system"
# The apps, all from Flathub's stable branch: Bottles for Windows programs, the
# browser and the video player.
APPS = ("com.usebottles.bottles", "org.mozilla.firefox", "org.kde.haruna")
# The runtime whose FFmpeg makes video thumbnails (step 1.14b), at a release of
# freedesktop-sdk: one a year, in August.
RUNTIME = "org.freedesktop.Platform"


def read(path, strict=True):
    """PATH as an INI file; systemd units may repeat a key, such as Documentation, so they aren't read strictly."""
    parser = configparser.ConfigParser(interpolation=None, strict=strict)
    parser.optionxform = str
    parser.read(path)
    return parser


class Preinstall(unittest.TestCase):
    def test_lists_the_apps(self):
        groups = read(PREINSTALL).sections()
        self.assertCountEqual(groups, [f"Flatpak Preinstall {ref}" for ref in (*APPS, RUNTIME)])

    def test_each_is_a_stable_app(self):
        parser = read(PREINSTALL)
        for app in APPS:
            with self.subTest(app):
                group = parser[f"Flatpak Preinstall {app}"]
                self.assertEqual(group["Branch"], "stable")
                self.assertNotIn("IsRuntime", group)
                self.assertNotIn("Install", group)


    def test_the_thumbnailers_runtime_is_a_yearly_release(self):
        group = read(PREINSTALL)[f"Flatpak Preinstall {RUNTIME}"]
        self.assertEqual(group["IsRuntime"], "true")
        self.assertRegex(group["Branch"], r"^[0-9]{2}\.08$")


class Units(unittest.TestCase):
    def test_the_service_skips_without_a_network(self):
        service = read(UNITS / "lumen-flatpak-preinstall.service", strict=False)
        self.assertTrue(service["Service"]["ExecCondition"].startswith("/usr/bin/nm-online "))
        self.assertEqual(service["Service"]["ExecStart"],
                         "/usr/bin/flatpak preinstall --system --assumeyes --noninteractive")

    def test_the_timer_waits_after_each_start(self):
        timer = read(UNITS / "lumen-flatpak-preinstall.timer", strict=False)
        self.assertEqual(timer["Timer"]["OnBootSec"], "2min")
        self.assertEqual(timer["Install"]["WantedBy"], "timers.target")


if __name__ == "__main__":
    unittest.main()
