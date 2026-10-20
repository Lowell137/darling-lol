#!/usr/bin/env python3
"""Check stale-session cleanup against fake processes; never signal a real process."""
import importlib.util
import os
from pathlib import Path
import tempfile
from unittest.mock import patch, Mock, MagicMock

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).with_name('ensure-darling-runtime.py'))
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)

with tempfile.TemporaryDirectory(prefix='darling-cleanup-check-') as folder:
    root = Path(folder)
    def process(pid, comm, argv):
        proc = root / str(pid)
        proc.mkdir()
        (proc / 'comm').write_text(comm + '\n')
        (proc / 'cmdline').write_bytes(b'\0'.join(arg.encode() for arg in argv) + b'\0')
        return proc
    browser = process(101, 'chrome_crashpad', ['/opt/google/chrome/chrome_crashpad_handler', '--annotation=riot'])
    riot = process(102, 'chrome_crashpad', ['/Applications/Riot Client.app/Contents/Frameworks/chrome_crashpad_handler'])
    launchd = process(103, 'launchd', ['/sbin/launchd'])
    (launchd / 'cmdline').write_bytes(b'/sbin/launchd' + b'\0' * 8)
    process(104, 'unrelated', ['/usr/bin/unrelated', '/sbin/launchd'])
    with patch.object(cleanup.os, 'kill') as kill:
        cleanup.stop_riot_crashpad(root)
        kill.assert_not_called()
        cleanup.stop_orphaned_launchd(root)
        kill.assert_not_called()
    assert not cleanup.any_server_running(root)
    process(105, 'darlingserver', ['darlingserver', '--prefix=another-prefix'])
    assert cleanup.any_server_running(root)
    hidden = MagicMock()
    hidden.name = '106'
    (hidden / 'comm').read_text.side_effect = PermissionError()
    fake_root = Mock()
    fake_root.iterdir.return_value = [hidden]
    assert cleanup.any_server_running(fake_root)
    # Foreign-owned Riot processes and buffers must survive even when no server runs.
    with patch.object(Path, 'stat', return_value=Mock(st_uid=os.getuid() + 1)), patch.object(cleanup.os, 'kill') as kill:
        cleanup.stop_riot_crashpad(root)
        cleanup.stop_orphaned_launchd(root)
        kill.assert_not_called()
    buffer = root / 'darling-buffer'
    buffer.write_text('stale')
    with patch.object(Path, 'stat', return_value=Mock(st_uid=os.getuid() + 1, st_mode=0o100600)):
        cleanup.remove_owned([buffer])
    assert buffer.exists()
    cleanup.remove_owned([buffer])
    assert not buffer.exists()
    # The entry point must preserve all sessions while ANY prefix has a server.
    with patch.object(cleanup, 'recover_marker'), patch.object(cleanup, 'any_server_running', return_value=True), \
         patch.object(cleanup, 'stop_riot_crashpad') as crashpad, \
         patch.object(cleanup, 'stop_orphaned_launchd') as orphan, patch.object(cleanup, 'remove_owned') as remove:
        cleanup.main()
        crashpad.assert_not_called()
        orphan.assert_not_called()
        remove.assert_not_called()
print('RUNTIME_CLEANUP_OFFLINE pass=1 browser_preserved=1 other_prefix_preserved=1 foreign_owner_preserved=1 hidden_process_preserved=1 orphan_preserved=1')
