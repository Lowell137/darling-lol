# Nix setup

The experimental Nix package provides a rootless build and launch environment
for x86_64 Linux. It supplies the dependencies, not a prebuilt Darling runtime
or game files. Initial setup builds Darling in a writable per-user workspace.

## Prerequisites

Enable Nix flakes and configure subordinate UID/GID ranges for your user. On
NixOS, add this to your system configuration and rebuild:

```nix
users.users.<name>.autoSubUidGidRange = true;
```

On other Linux distributions, [install Nix using the official instructions](https://nixos.org/download/).
You do not need to install NixOS. If you already use `nix-shell`, Nix is installed.
Enable the modern CLI and flakes in `~/.config/nix/nix.conf`:

```ini
experimental-features = nix-command flakes
```

Alternatively, enable them for an individual command:

```sh
nix --extra-experimental-features 'nix-command flakes' run github:lucannez64/darling-lol
```

The rootless launcher requires unprivileged user namespaces, subordinate UID/GID
ranges, and working `newuidmap`/`newgidmap` helpers. If these are already configured
on your distribution, no additional host setup is needed.

Run setup in an interactive terminal and allow roughly 40–50 GB for the runtime
build.

## Install and launch

Run the flake directly from GitHub; no local checkout is needed:

```sh
nix run github:lucannez64/darling-lol
```

On first launch, setup prompts to build Darling and install the Riot client.
To explicitly open the installer, including for another region:

```sh
nix run github:lucannez64/darling-lol#installer
```

Setup prompts before building. Subsequent launches reuse a compatible runtime;
they do not automatically rebuild it. If the package is installed in your
profile or system configuration, the equivalent commands are
`darling-lol --installer` and `darling-lol`. The desktop entry opens a terminal
for prompts and session output.

Keep the terminal open while clients are running and until cleanup completes.
Default and installer sessions wait for clients to exit, then shut Darling down
in the same namespace. Crash handlers do not count as clients, because they do
not exit on their own under Darling. A failed shutdown is retried without
discarding that namespace.

To end a session while clients are still running, press Ctrl+C in its terminal,
close the terminal, or run `darling-lol --stop` from anywhere. Each of these
makes the session shut Darling down and exit. If the session does not exit
within 30 seconds, `darling-lol --stop` kills the prefix's `darlingserver`
itself. It also stops a server that outlived its session.

## Install permanently

`nix run` does not add commands to your profile or install a desktop menu entry.
It does reuse downloaded store paths and the persistent Darling workspace.
For commands on your `PATH` and desktop-menu access, install the package using
one of the following methods.

### User profile (NixOS or other Linux distributions)

```sh
nix profile add github:lucannez64/darling-lol#default
# Older Nix/Lix versions without `profile add`:
# nix profile install github:lucannez64/darling-lol#default
```

Then launch from your application menu or terminal:

```sh
darling-lol
# Explicit setup or runtime shell:
darling-lol --installer
darling-lol-shell
```

The application menu entry is `Darling Launcher`, and `darling-launcher` is an
alias for `darling-lol` for scripts that prefer the neutral name.

If the desktop entry does not appear, ensure your desktop session includes
`~/.nix-profile/share` in `XDG_DATA_DIRS`, then log out and back in. Non-NixOS
systems may need this desktop-session integration after installing Nix.

To upgrade, find the package's name with `nix profile list`, then run
`nix profile upgrade <name>`. Close the clients first; after upgrading, run
`darling-lol --update` to rebuild the mutable runtime when required.

### NixOS system configuration

In your system flake, add the input and pass it to your NixOS modules:

```nix
inputs.darling-lol.url = "github:lucannez64/darling-lol";

outputs = inputs@{ nixpkgs, ... }: {
  nixosConfigurations.<hostname> = nixpkgs.lib.nixosSystem {
    system = "x86_64-linux";
    specialArgs = { inherit inputs; };
    modules = [ ./configuration.nix ];
  };
};
```

Merge these entries into your existing flake rather than replacing its outputs.
In `configuration.nix`, add the package and subordinate-ID configuration:

```nix
{ inputs, pkgs, ... }:
{
  environment.systemPackages = [
    inputs.darling-lol.packages.${pkgs.stdenv.hostPlatform.system}.default
  ];
  users.users.<name>.autoSubUidGidRange = true;
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
}
```

Apply with `sudo nixos-rebuild switch --flake .#<hostname>`. The launcher and
desktop entry are then installed system-wide; each user still has a separate
workspace and prefix. Start `darling-lol` as your normal user, not with sudo.

To upgrade, update the input with `nix flake update darling-lol`, rebuild your
system, and run `darling-lol --update` after closing the clients.

## Update

Close League and both Riot clients and wait for the launcher to finish cleanup.
Then run the updated flake and rebuild the runtime:

```sh
nix run --refresh github:lucannez64/darling-lol -- --update
# Installed package: darling-lol --update
```

This rebuilds incrementally, installs the base runtime into the user-owned
workspace, and refreshes the per-prefix overlays. No `sudo` is needed.

## Local checkout and scripts

You can also launch the flake directly from an already checked-out repository:

```sh
cd /path/to/darling-lol
nix run .
```

Or clone it first:

```sh
git clone https://github.com/lucannez64/darling-lol.git
cd darling-lol
nix run .
```

The same checkout also provides installer and update commands:

```sh
nix run .#installer
# After updating the checkout:
nix run . -- --update
```

These commands work on NixOS and other Linux distributions with Nix installed.
Use `nix run` for this flake rather than `nix-shell`: the launcher sets up the
rootless namespace in addition to supplying dependencies. `nix develop` is for
development tools only; use `nix run .#shell` for an actual runtime shell.

To run a repository script inside the rootless FHS environment, pass its command
after `--`. Commands run from the managed workspace, using the tools copied from
the selected flake:

```sh
nix run github:lucannez64/darling-lol -- python3 scripts/validate.py
# Equivalent from a local checkout:
nix run . -- python3 scripts/validate.py
```

Use the supported installer/update commands for maintenance. Arbitrary script
commands do not get the default launcher's automatic client-session cleanup; if
a script starts Darling, shut it down in the same namespace before returning.
For multiple commands, use an interactive runtime shell:

## Runtime shell

```sh
nix run github:lucannez64/darling-lol#shell
# Local checkout: nix run .#shell
# Installed package: darling-lol-shell
```

Use the launcher-provided shell rather than entering the raw FHS environment.
If you start Darling manually in this shell, run `darling shutdown` there
before exiting. A separately launched shell cannot reconnect to an existing
Darling namespace; `darling-lol --stop` can still stop it.

### Text fonts

The FHS environment bundles Liberation and DejaVu text fonts and uses its own
fontconfig configuration and standard aliases. It does not depend on fonts in
the host's `/usr/share/fonts`, which the FHS environment replaces. Fonts in your
user font directories remain available. This also prevents an icon-only user
font inventory from becoming the only fallback for ordinary text.

The FHS environment selects the packaged fontconfig configuration and clears
inherited `FONTCONFIG_PATH` and `FONTCONFIG_SYSROOT` overrides. Clearing the
sysroot prevents it from redirecting the packaged configuration and font paths.
Custom XDG font/configuration directories and legacy
`~/.fonts` remain supported, including paths with spaces. The host configuration
and user font files are not modified.

To check font availability without starting Darling or Riot:

```sh
nix run .#default -- fc-match sans-serif
nix run .#default -- fc-match Arial
```

These should select DejaVu Sans and Liberation Sans respectively. The standalone
`nix build .#checks.x86_64-linux.fonts` check verifies generic and common Windows
font aliases with both an empty home directory and icon-only user fonts. This
checks font availability; CAPTCHA text rendering still needs manual verification
in Riot's UI.

## Files and operational limits

- Workspace: `${XDG_DATA_HOME:-$HOME/.local/share}/darling-lol`.
- Default guest prefix: `$HOME/.darling`. The prefix holds the installed
  clients and game, about 40 GB. To keep it on another drive, close the clients
  and run `darling-lol --set-prefix /mnt/games/league`. This moves an existing
  prefix there and saves the path for later launches. Across filesystems it
  copies first and removes the old prefix only after the copy completes. If the
  path already holds a Darling prefix, it switches to it and moves nothing. The
  path must not contain commas or colons (overlayfs uses them as separators).
  Across filesystems the target must support `user.*` extended attributes (ext4,
  btrfs, xfs; not NTFS or exFAT), which is checked before copying and again on
  the finished copy. The new path is saved before the old prefix is deleted.
  The next launch sets up the runtime in the new prefix.
- Explicit `DPREFIX` and `RIOT_GUEST_HOME` overrides take precedence over saved
  configuration, so clear stale overrides before switching installations.
- Package upgrades refresh managed tools and remove previously tracked obsolete
  files. Builds, the installed runtime, guest prefixes, and unmanaged files are
  preserved. Edit the source checkout rather than copied workspace tools.
- One active session is supported per workspace. A workspace lock and live
  prefix marker prevent concurrent launches; the launcher does not kill an
  existing session or reconnect across namespaces. Inspect an unexpected live
  marker rather than deleting it to force a launch.
- Readiness records in `build/nix-ready/` validate the selected prefix, guest,
  package, base runtime, and required overlays. A new prefix can reuse a
  compatible base runtime; failed setup invalidates readiness.
- Keep `build/nix-gcroots/` while using the workspace. Mutable compiled binaries
  can reference Nix-store libraries, so these roots retain the package closures
  they need. Remove them only when discarding the dependent build outputs.

The launcher uses subordinate-ID user namespaces before entering the FHS
environment. Mount privileges are scoped to that namespace, not host root;
workspace and prefix files retain the Linux user's ownership. The setup does
not install a host setuid binary or require a privileged runtime installation.

Darling compilation still happens outside Nix derivations and uses the host CPU;
the resulting runtime is not a portable, binary-cacheable Nix package. The
FFmpeg dependency is pinned to 8.x because the generated AV wrappers require
its library ABI.
