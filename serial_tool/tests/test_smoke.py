import serial_tool


def test_package_importable():
    assert serial_tool.__version__ == "2.0.0"
