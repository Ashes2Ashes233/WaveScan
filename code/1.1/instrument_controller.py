#instrument_controller.py

import telnetlib
import time
import random
import re

# 假设备模拟
class FakeSignalAnalyzer:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.connected = False
        self.hotspots = [2450.0, 2480.0, 2420.0, 2460.0, 2490.0]
        self.amplitudes = [1.0, 0.8, 0.6, 0.4, 0.2]
        print(f"模拟设备：初始化于地址 {self.address}:{self.port}")

    def connect(self):
        print(f"模拟设备：正在尝试连接到 {self.address}:{self.port}...")
        time.sleep(0.5)
        self.connected = True
        print("模拟设备：连接成功。")
        return True

    def read_peak_frequency(self):
        """模拟读取单个峰值频率，并模拟仪器延迟"""
        if not self.connected:
            raise ConnectionError("模拟设备未连接")

        # 模拟仪器处理和网络延迟，假设总共15ms
        time.sleep(0.015)

        if random.random() < 0.8:
            idx = random.choices(range(len(self.hotspots)), weights=self.amplitudes)[0]
            base_freq = self.hotspots[idx]
            freq = base_freq + random.gauss(0, 0.1)
        else:
            freq = random.uniform(2400, 2500)
        return freq  # 返回单个频率值

    def close(self):
        self.connected = False
        print("模拟设备：连接已断开。")

    def query(self,command):
        if command=="*IDN?":
            return "FakeController"
        else:
            return False
# 真实设备控制器
class SignalAnalyzerController:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.tn = None
        self.connected = False

    def connect(self):
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', self.address):
            print("无效的 IP 地址格式")
            return False
        try:
            print(f"正在尝试连接到: {self.address}:{self.port}")
            self.tn = telnetlib.Telnet(self.address, self.port, timeout=5)
            response = self.query("*IDN?")
            if not response:
                raise ConnectionError("Instrument did not respond to *IDN?")
            print(f"仪器识别: {response}")
            self.connected = True
            self.setup_instrument()
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            self.connected = False
            return False

    def send_command(self, cmd):
        if self.tn:
            self.tn.write(cmd.encode('ascii') + b'\n')

    def query(self, cmd):
        if self.tn:
            self.send_command(cmd)
            return self.tn.read_until(b'\n', timeout=0.5).decode().strip()
        return ""

    def query_data(self, cmd):
        if self.tn:
            self.send_command(cmd)
            response = self.tn.read_until(b'\n', timeout=0.5).decode().strip()
            match = re.search(r'[-+]?\d*\.?\d+E?[-+]?\d*', response)
            if match:
                return match.group()
            return ""
        return ""

    def setup_instrument(self):
        print("正在配置仪器...")
        self.send_command("*CLS")
        time.sleep(0.1)
        self.send_command(":INSTrument:SELect SA")
        self.send_command(":SENSe:FREQuency:CENTer 2.45GHz")
        self.send_command(":SENSe:FREQuency:SPAN 100MHz")
        self.send_command(":SENSe:BANDwidth:RESolution 1MHz")
        self.send_command(":DISPlay:WINDow:TRACe:MODE WRITe")
        self.send_command(":CALCulate:MARKer1:STATe ON")
        self.send_command(":INITiate:CONTinuous ON")
        print("仪器配置完成。")

    def read_peak_frequency(self):
        if not self.connected:
            raise ConnectionError("设备未连接")
        try:
            self.send_command("CALCulate:MARKer1:MAXimum")
            freq_hz_str = self.query_data("CALCulate:MARKer1:X?")
            if freq_hz_str:
                try:
                    return float(freq_hz_str) / 1e6 # 返回MHz
                except ValueError:
                    return None
            return None
        except Exception as e:
            print(f"读取峰值频率失败: {e}")
            return None

    def close(self):
        if self.tn:
            self.tn.close()
        self.connected = False
        print("设备连接已成功关闭。")