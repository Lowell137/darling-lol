# Scope and compliance guidance

This project is an unofficial compatibility layer for running the macOS League of Legends
client on Linux through Darling. It is not affiliated with, endorsed by, or sponsored by Riot
Games, Inc.

## Scope

- The project is about compatibility: making the client run, render and behave correctly on
  Linux.
- It does not aim to circumvent DRM, anti-cheat, licensing, telemetry, or other platform
  security controls, and it does not distribute a game client, game assets, or account data.
- Do not describe or present the project as a tool for evading detection, preventing bans,
  bypassing DRM, or defeating anti-cheat. Do not promise that an account will not be banned.

## Terminology

Prefer accurate compatibility language:

| Prefer | Avoid |
|---|---|
| compatibility issue, client check, platform identity | detection vector, stealth, evasion, bypass |
| hardware/platform reporting | spoofing, telemetry leak |
| runtime/launcher fix | anti-cheat bypass |

Technical facts can be described precisely without framing the work as evasion. If a change
touches a client check or a platform identity, say what it does and why it is needed for
compatibility.

## Assets and third-party material

- Do not add or link third-party game assets: logos, icons, fonts, screenshots, gameplay
  audio/video, client files, game data, or account data.
- Project icons and artwork must be original. Forks must use their own name and icon; see the
  trademark notice in `README.md` and `NOTICE.md`.
- Do not commit local prefixes, logs, tokens, captures, or compiled client/runtime binaries.

## Pull requests and issues

- Describe the compatibility problem and the fix. Avoid "stealth", "spoof", "evade",
  "undetectable", or "unbannable" framing.
- Maintainers may ask for wording changes before merging. This is about keeping the project's
  scope accurate, not about hiding technical details.
- Contributions that add third-party assets or present the project as a DRM/anti-cheat
  circumvention tool are out of scope for this repository.

## Note

This document describes project scope and review expectations. It is not legal advice.
