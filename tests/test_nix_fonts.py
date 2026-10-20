import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def extract_fhs_profile(flake_text: str) -> str:
    """Extract the FHS shell profile, substituting inert paths for Nix values."""
    match = re.search(r"profile\s*=\s*''(.*?)'';", flake_text, re.DOTALL)
    if not match:
        raise ValueError("Could not find profile in flake.nix")
    raw_profile = match.group(1)
    # Nix multi-line strings: (?<!'')\$\{...\} is interpolation, ''$ is escaped $
    profile_script = re.sub(r"(?<!'')\$\{([^}]+)\}", r"/nix/store/mock-\1", raw_profile)
    profile_script = profile_script.replace("''$", "$")
    return profile_script

class NixFontsConfigTest(unittest.TestCase):
    """Check packaged font configuration and isolation from host overrides."""

    def test_flake_font_configuration(self):
        """Require bundled text fonts, user font support, and ordered sanitization."""
        flake_text = (REPO_ROOT / "flake.nix").read_text(encoding="utf-8")

        # Flake must bundle both font families in darlingFontsConf
        self.assertIn("pkgs.liberation_ttf", flake_text)
        self.assertIn("pkgs.dejavu_fonts", flake_text)

        # makeFontsConf includes store fontconfig config directory
        self.assertIn('"${pkgs.fontconfig.out}/etc/fonts/conf.d"', flake_text)

        # Legacy ~/.fonts XML fragment included in darlingFontsConf
        self.assertIn("<dir>~/.fonts</dir>", flake_text)

        # FHS profile unsets foreign/sysroot fontconfig vars before exporting package FONTCONFIG_FILE
        self.assertIn("unset FONTCONFIG_PATH FONTCONFIG_SYSROOT", flake_text)
        self.assertIn("export FONTCONFIG_FILE=${darlingFontsConf}", flake_text)

        unset_pos = flake_text.index("unset FONTCONFIG_PATH FONTCONFIG_SYSROOT")
        export_pos = flake_text.index("export FONTCONFIG_FILE=${darlingFontsConf}")
        self.assertLess(unset_pos, export_pos, "unset must happen before export FONTCONFIG_FILE")

    def test_fhs_profile_hostile_environment_sanitization(self):
        """Clear hostile fontconfig overrides while preserving user XDG settings."""
        flake_text = (REPO_ROOT / "flake.nix").read_text(encoding="utf-8")
        profile_script = extract_fhs_profile(flake_text)

        hostile_envs = [
            {
                "FONTCONFIG_SYSROOT": "/not/a/real/host/sysroot",
                "FONTCONFIG_PATH": "/foreign/host/etc/fonts",
            },
            {
                "FONTCONFIG_SYSROOT": "",
                "FONTCONFIG_PATH": "/foreign/host/etc/fonts",
            },
        ]

        for hostile_font_env in hostile_envs:
            with self.subTest(hostile_font_env=hostile_font_env):
                test_env = dict(hostile_font_env)
                test_env.update({
                    "HOME": "/tmp/mock-home",
                    "XDG_DATA_HOME": "/tmp/mock-xdg data with spaces",
                    "XDG_CONFIG_HOME": "/tmp/mock-xdg config with spaces",
                    "UNRELATED_USER_VAR": "preserve_this_value",
                    "PATH": os.environ.get("PATH", "/bin:/usr/bin"),
                })

                dump_cmd = (
                    f"{profile_script}\n"
                    f'"{sys.executable}" -c \'import os, json; print(json.dumps(dict(os.environ)))\''
                )

                proc = subprocess.run(
                    ["bash", "-c", dump_cmd],
                    env=test_env,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                resulting_env = json.loads(proc.stdout)

                self.assertNotIn("FONTCONFIG_SYSROOT", resulting_env)
                self.assertNotIn("FONTCONFIG_PATH", resulting_env)
                self.assertEqual(
                    resulting_env.get("FONTCONFIG_FILE"),
                    "/nix/store/mock-darlingFontsConf",
                )
                self.assertEqual(resulting_env.get("XDG_DATA_HOME"), "/tmp/mock-xdg data with spaces")
                self.assertEqual(resulting_env.get("XDG_CONFIG_HOME"), "/tmp/mock-xdg config with spaces")
                self.assertEqual(resulting_env.get("UNRELATED_USER_VAR"), "preserve_this_value")

if __name__ == "__main__":
    unittest.main()
