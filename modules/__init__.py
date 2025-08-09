"""
Serial Port Tool - 模块包

此包提供了串口监控工具的所有核心功能模块。

便捷导入方式:
    from modules import SerialPortTool, apply_stylesheet
    
或者单独导入:
    from modules.main_window import SerialPortTool
    from modules.styles import apply_stylesheet
    from modules.threads import SerialPortMonitor, SerialWorker
    from modules.highlighting import HighlightRule, TextHighlighter
"""

# 主要组件导入
from .main_window import SerialPortTool
from .styles import apply_stylesheet, get_application_stylesheet
from .threads import SerialPortMonitor, SerialWorker
from .highlighting import HighlightRule, TextHighlighter, HighlightRulesDialog, RuleEditDialog

# 便捷导入的公共接口
__all__ = [
    # 主要组件
    'SerialPortTool',
    'apply_stylesheet',
    'get_application_stylesheet',
    
    # 线程模块
    'SerialPortMonitor',
    'SerialWorker',
    
    # 高亮模块
    'HighlightRule',
    'TextHighlighter',
    'HighlightRulesDialog',
    'RuleEditDialog',
]

# 版本信息
__version__ = '1.0.0'
__author__ = 'Serial Port Tool Team'
__description__ = 'PySide6-based serial port monitoring tool'