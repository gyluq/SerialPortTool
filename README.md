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

```bash
pyinstaller --onefile --windowed --icon=icon.png --name=SerialPortTool main.py
```

## License

MIT — see `LICENSE`.
