# SerialPortTool

A production-ready PySide6-based serial port monitoring tool with modern GUI interface.

## Features

- **Real-time Monitoring**: Automatic serial port detection and monitoring
- **Flexible Configuration**: Customizable baud rate, data bits, parity, and stop bits
- **Data Logging**: Timestamped data recording with automatic file creation
- **Text Highlighting**: Regex-powered custom text highlighting rules
- **Search & Filter**: Full-text search in received data
- **Settings Persistence**: Cross-platform settings storage with QSettings
- **Pause/Resume**: Display pause without disconnecting
- **Cross-platform**: Windows, Linux, and macOS support
- **Modern UI**: Menu bar, status bar with real-time statistics
- **Professional Design**: Clean, responsive interface

## Quick Start

### Requirements
- Python 3.8+
- PySide6
- pyserial

### Installation
```bash
pip install -r requirements.txt
```

### Basic Usage
```bash
python main.py
```

## Architecture

The codebase follows clean architecture principles:
- **main.py**: Application entry point with icon support
- **modules/**: Modular design with focused responsibilities
- **Total**: ~1,476 lines across well-organized modules

### Core Components
- **SerialPortMonitor**: Background thread for port detection
- **SerialWorker**: Thread-safe serial communication handler
- **TextHighlighter**: Syntax highlighting with regex support
- **HighlightRulesDialog**: Rule management interface

## Packaging

### Single Executable
```bash
pyinstaller --onefile --windowed --icon=icon.png --name=SerialPortTool main.py
```

### Output
- Windows: `dist/SerialPortTool.exe`
- Linux/macOS: `dist/SerialPortTool`

### Advanced Options
```bash
# Cross-platform packaging
pyinstaller --onefile --icon=icon.png main.py  # Linux/macOS
pyinstaller --onefile --windowed --icon=icon.icns main.py  # macOS
```

## Development

### Project Structure
```
serial_port/
├── main.py              # Entry point
├── modules/
│   ├── __init__.py
│   ├── main_window.py   # GUI logic
│   ├── threads.py       # Serial operations
│   ├── highlighting.py  # Text highlighting
│   └── styles.py        # UI styling
├── icon.png            # Application icon
├── requirements.txt    # Dependencies
├── README.md          # This file
└── packaging.spec     # Build configuration
```

### Development Setup
```bash
git clone <repository>
cd serial_port
pip install -r requirements.txt
python main.py
```

### Code Quality
- PEP 8 compliant
- Type annotations
- Single responsibility principle
- Clean module boundaries

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Create Pull Request

## License

MIT License - see LICENSE file for details.

## Support

For issues or questions, please open an issue on the GitHub repository.