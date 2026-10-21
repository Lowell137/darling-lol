#!/usr/bin/env python3
"""Run the Riot client and keep everything a failure needs afterwards.

Launches scripts/run.sh with the Darling sysctl and IORegistry traces enabled, then
copies the client, game, darlingserver and trace logs into ~/darling-sessions/<start>/
and writes a summary that names client versions, anti-cheat state changes, VAN codes,
crashes and helper actions.

The collector never edits the logs it copies. Sessions where nothing happened still get
a directory, so a later failure can be compared against a quiet one.

Usage:
  tools/collect-riot-session.py            # start the client under the collector
  tools/collect-riot-session.py --collect-only START_EPOCH
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
GUEST = Path.home() / '.darling'


def guest_path(*parts):
    return GUEST.joinpath(*parts)


def read_prefix():
    config = ROOT / 'build' / 'config.json'
    try:
        return json.loads(config.read_text()).get('prefix', str(GUEST))
    except (OSError, ValueError):
        return str(GUEST)


def files_since(root, since):
    found = []
    if not root.is_dir():
        return found
    for path in root.rglob('*'):
        try:
            if path.is_file() and path.stat().st_mtime >= since:
                found.append(path)
        except OSError:
            continue
    return found


def grep(paths, pattern, limit=200):
    compiled = re.compile(pattern)
    hits = []
    for path in paths:
        try:
            with open(path, errors='replace') as handle:
                for line in handle:
                    if compiled.search(line):
                        hits.append(f'{path.name}: {line.rstrip()}')
                        if len(hits) >= limit:
                            return hits
        except OSError:
            continue
    return hits


def summarize(session, files, since):
    logs = [p for p in files if p.suffix == '.log' or p.name.endswith('.txt')]
    summary = []
    summary.append(f'# Darling session {session.name}')
    summary.append('')
    started = dt.datetime.fromtimestamp(since).strftime('%Y-%m-%d %H:%M:%S')
    summary.append(f'Started: {started}')
    summary.append('')
    riot_logs = [p for p in logs if 'Riot Client Logs' in str(p)]
    versions = sorted({m for p in riot_logs
                       for m in re.findall(r'(?:Application Version:|version:)\s*(\d+\.\d+\.\d+\.\d+)',
                                           p.read_text(errors='replace'))})
    summary.append('Client versions: ' + (', '.join(versions) if versions else 'not seen'))
    summary.append('')
    for title, pattern in (
        ('Anti-cheat state', r'MvgState|MvgST|MvgRC|MvgGCK|MvgInit|MvgRegister'),
        ('VAN / ban codes', r'VAN|TIME_BAN|UNSUPPORTED|suspension'),
        ('Crashes', r'LOLSIG|SIGSEGV|crashed|Segmentation|abort'),
        ('Helper', r'close-league-client-in-game'),
        ('TLS', r'handshake failed|net_error'),
    ):
        hits = grep(logs, pattern)
        summary.append(f'## {title} ({len(hits)} lines)')
        summary.extend(hits[-40:])
        summary.append('')
    return '\n'.join(summary) + '\n'


def collect(start_epoch):
    session = Path.home() / 'darling-sessions' / dt.datetime.fromtimestamp(start_epoch).strftime('%Y-%m-%dT%H-%M-%S')
    session.mkdir(parents=True, exist_ok=True)
    sources = [
        guest_path('Users', 'lowell', 'Library', 'Logs', 'Riot Games'),
        guest_path('Applications', 'League of Legends.app', 'Contents', 'LoL', 'Logs'),
        guest_path('private', 'var', 'log'),
        guest_path('private', 'tmp'),
    ]
    copied = []
    since = start_epoch - 5
    for source in sources:
        for path in files_since(source, since):
            try:
                relative = path.relative_to(GUEST)
            except ValueError:
                continue
            target = session / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(path, 'rb') as source:
                    size = os.fstat(source.fileno()).st_size
                    if size > 8 * 1024 * 1024:
                        source.seek(size - 4 * 1024 * 1024)
                        target = target.with_name(target.name + '.tail')
                        with open(target, 'wb') as sink:
                            shutil.copyfileobj(source, sink)
                    else:
                        shutil.copy2(path, target)
                copied.append(target)
            except OSError:
                continue
    summary = summarize(session, copied, start_epoch)
    (session / 'SUMMARY.md').write_text(summary)
    print(session)
    return session


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--collect-only', type=float, metavar='START_EPOCH',
                        help='skip launching; collect logs written since this epoch')
    args = parser.parse_args()

    if args.collect_only is not None:
        collect(args.collect_only)
        return 0

    start = time.time()
    env = dict(os.environ)
    env.setdefault('DARLING_SYSCTL_TRACE', '1')
    env.setdefault('DARLING_IOKIT_TRACE', '1')
    env.setdefault('RCLOL_CLOSE_CLIENT_IN_GAME', '1')
    print(f'collecting into ~/darling-sessions ({dt.datetime.fromtimestamp(start):%H:%M:%S}); '
          'close the client to finish', flush=True)
    process = subprocess.Popen([str(ROOT / 'scripts' / 'run.sh')], env=env)
    try:
        process.wait()
    except KeyboardInterrupt:
        pass
    time.sleep(2)
    collect(start)
    return 0


if __name__ == '__main__':
    sys.exit(main())
