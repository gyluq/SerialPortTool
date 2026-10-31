# SerialPortTool

A PySide6 serial port monitor: connect, watch, search, highlight, log.

The project is a rewrite against a written requirements document: the UI layout is
kept from the original tool, the implementation is new and layer-separated so that
almost all behaviour can be tested without a real serial port or a display.

## Features

- **Port discovery** — ports are polled in the background and refreshed in place;
  the current selection survives a hot-plug.
- **Connection settings** — port, baud rate (9600 … 921600), data bits,
  parity, stop bits, validated before opening.
- **Receive** — blocking reads on a worker thread, batched into the UI.
- **Send** — text (UTF-8) or HEX, optional trailing newline. All writes go
  through a queue owned by the worker thread, so the GUI thread never touches
  the port handle.
- **Display** — three message kinds (system / sent / received), millisecond
  timestamps on the first line of each chunk, escaped HTML so device output such
  as `<b>` is shown literally, not interpreted.
- **Highlighting** — custom rules, plain string or regex, per-rule colour and
  enable switch, applied live without reconnecting.
- **Search** — forward / backward with wraparound notice.
- **Pause** — stops rendering but keeps buffering; nothing is lost while paused.
- **Session log** — timestamped lines appended to `log/log_YYYYMMDD_HHMMSS.log`
  next to the application, flushed on every write.
- **Retention limit** — 100 KB … 10 MB or unlimited; oldest blocks are dropped
  at block boundaries so the remaining text keeps its colours and timestamps.
- **Persistence** — every connection and display setting plus all highlight
  rules are restored on the next start.

## Requirements

- Python 3.10+
- PySide6
- pyserial

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite runs headless (`QT_QPA_PLATFORM=offscreen`) and needs no hardware:
the serial port is replaced by a fake transport, settings are written to a
temporary ini file.

## Benchmark

```bash
python tools/bench_receive.py                       # all in-process scenarios
python tools/bench_receive.py --only stream --total-mb 8
python tools/bench_receive.py --only loss --limit 1MB
python tools/bench_receive.py --only loop --total-mb 4   # reader thread + driver buffer
```

Scenarios: `single` (largest payload per call), `stream` (sustained MB/s),
`loss` (sequence-number audit for holes), `pause` (paused-buffer cap), `memory`
(RSS per capacity setting), `send` (large outbound paste), `loop` (end-to-end
through the real reader thread).

## Architecture

```
main.py                    entry point
serial_tool/
├── core/                  pure Python, no Qt imports
│   ├── params.py          connection parameters, validation, label mapping
│   ├── codec.py           text encoding, HEX parse / format
│   ├── render.py          line -> HTML fragment (the single escaping point)
│   ├── highlight.py       rule model and matching engine (returns ranges)
│   ├── retention.py       decides how many leading blocks to drop
│   ├── counters.py        received / sent character counters
│   ├── config.py          config dataclass and dict serialisation
│   ├── logfile.py         log path naming and line writer
│   └── session.py         port listing, transport abstraction, write queue
├── ui/                    PySide6 shell
│   ├── main_window.py     layout, signal wiring, rendering
│   ├── highlighter.py     adapts core.highlight to QSyntaxHighlighter
│   ├── rules_dialog.py    rule editor
│   ├── settings_store.py  QSettings <-> core.config adapter
│   └── styles.py          stylesheet constants
└── tests/
```

The split exists for one reason: `core` decides *what* to show and *when*, `ui`
only draws it. Escaping, colours, retention boundaries and rule matching are all
asserted in tests without starting a window.

`core.session.SerialSession` accepts any object implementing the `Transport`
protocol (`is_open`, `read`, `write`, `close`), which is how the whole receive
and send path is tested against `tests.fakes.FakeTransport`.

## Packaging

### Standalone executable

```bash
pip install -r requirements-dev.txt
pyinstaller packaging.spec
```

`packaging.spec` bundles `icon.png`, embeds `icon.ico` and `version_info.txt`,
and excludes the Qt modules the app never imports. Output is a single
self-contained `dist/SerialPortTool.exe` (~43 MB); the target machine needs
nothing installed. On Linux/macOS the same spec produces `dist/SerialPortTool`.

### Windows installer

Requires [Inno Setup 6](https://jrsoftware.org/isdl.php)
(`winget install --id JRSoftware.InnoSetup -e`). Then run the whole chain —
tests, executable, installer — with one command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1
```

The result is `dist/SerialPortTool-1.0.0-setup.exe` (~44 MB). Run
`iscc installer\SerialPortTool.iss` alone to rebuild only the installer.

What the installer does:

| | |
|---|---|
| Install location | `%LOCALAPPDATA%\Programs\SerialPortTool` |
| Elevation | none — per-user install, no UAC prompt |
| Shortcuts | Start menu always, desktop optional |
| Uninstall | standard Windows entry; asks before deleting `log\` |

The per-user location is deliberate, not incidental: the app writes its
`log\` folder next to the executable, so it must not live under
`Program Files`, where a normal user cannot write.

Note for packagers: `app_base_dir()` in `core/config.py` resolves data paths
from `sys.executable` when frozen. A onefile build unpacks into a temporary
`_MEIxxxx` directory that is deleted on exit, so deriving the log path from
`__file__` would silently lose every recording.

## License

MIT — see `LICENSE`.
