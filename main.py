import sys
import serial.tools.list_ports
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from modules import SerialPortTool, apply_stylesheet


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    icon_path = Path(__file__).parent / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # 应用样式
    apply_stylesheet(app)
    
    # 创建并显示主窗口
    window = SerialPortTool()
    window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__": 
    main()
