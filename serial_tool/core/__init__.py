"""Core logic layer: no Qt dependency at all, fully covered by pytest.

Submodules are split by responsibility; tests import them by path to avoid
package-level side effects:

    from serial_tool.core.params import SerialParams
    from serial_tool.core.render import Line, render_line_html
"""
