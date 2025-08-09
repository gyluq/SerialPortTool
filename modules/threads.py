import serial
import serial.tools.list_ports
from serial import SerialException
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition
from typing import Optional, List, Dict, Any
from collections import deque
import time


class SerialPortMonitor(QThread):
    ports_changed = Signal(list)

    def __init__(self):
        super().__init__()
        self.running = True
        self.previous_ports = set()

    def run(self):
        while self.running:
            current_ports = {port.device for port in serial.tools.list_ports.comports()}
            if current_ports != self.previous_ports:
                ports_info = []
                for port_info in serial.tools.list_ports.comports():
                    ports_info.append(
                        {
                            "device": port_info.device,
                            "description": port_info.description or "Unknown",
                            "hwid": port_info.hwid or "Unknown",
                        }
                    )
                self.ports_changed.emit(ports_info)
                self.previous_ports = current_ports
            self.msleep(1000)

    def stop(self):
        self.running = False
        self.wait()


class SerialWorker(QThread):
    data_received = Signal(bytes)
    connection_lost = Signal()

    def __init__(
        self, port: str, baudrate: int, bytesize: int, parity: str, stopbits: float
    ):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.serial_connection: Optional[serial.Serial] = None
        self.running = False
        
        self.data_buffer = deque(maxlen=65536)
        self.buffer_mutex = QMutex()
        
        self.last_update_time = time.time()
        self.update_interval = 0.05  # 50ms更新间隔

    def run(self):
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=0.01,  # 减少超时时间
            )
            # 增大接收缓冲区
            self.serial_connection.timeout = 0.01
            self.serial_connection.inter_byte_timeout = 0.001
            
            self.running = True

            while self.running:
                if self.serial_connection and self.serial_connection.is_open:
                    try:
                        # 动态调整读取大小，高波特率时读取更多数据
                        read_size = min(4096, max(1024, self.baudrate // 1000))
                        data = self.serial_connection.read(read_size)
                        if data:
                            # 添加到缓冲区
                            self.buffer_mutex.lock()
                            self.data_buffer.append(data)
                            self.buffer_mutex.unlock()
                            
                            # 控制更新频率
                            current_time = time.time()
                            if current_time - self.last_update_time >= self.update_interval:
                                self.flush_buffer()
                                self.last_update_time = current_time
                    except SerialException:
                        self.connection_lost.emit()
                        break
                else:
                    break
            
            self.flush_buffer()

        except Exception as e:
            print(f"Serial connection error: {e}")
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()

    def flush_buffer(self):
        """刷新缓冲区"""
        self.buffer_mutex.lock()
        if self.data_buffer:
            # 合并缓冲区数据
            combined_data = b''.join(self.data_buffer)
            self.data_buffer.clear()
            self.buffer_mutex.unlock()
            if combined_data:
                self.data_received.emit(combined_data)
        else:
            self.buffer_mutex.unlock()

    def stop(self):
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.wait()

    def send_data(self, data: bytes):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(data)
                return True
            except SerialException:
                return False
        return False
