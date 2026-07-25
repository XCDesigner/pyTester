from http_client import HttpClient
import asyncio
from ttkthemes import ThemedTk
import os, time, re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Button
from cvs_reader import CSVReader
import threading
from threading import Thread
from typing import List
from datetime import datetime
from result_analizer import Report
from PIL import Image, ImageTk
from serial_port import SerialTester, WaitCompletion

class DeviceTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("设备测试工具")
        self.root.geometry("1680x720")
        self.root.minsize(1500, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.csv_reader = CSVReader()
        self.test_template = []
        self.devices = {}
        self.root.state("zoomed")
        self.serial_port = SerialTester()

        self.create_widgets()
        self.load_machine_list()

    def create_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Normal.TButton")
        style.configure("Red.TButton", background="#ee3333")
        style.configure("Green.TButton", background="#32CD32")
        style.map("Red.TButton", background=[("active", "#cc2222")])
        style.map("Green.TButton", background=[("active", "#27b827")])

    def create_widgets(self):
        self.create_style()
        # 最顶层Tab容器
        main_tab = ttk.Notebook(self.root)
        main_tab.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # =========== Tab1：单机测试，放入原来左侧left_frame ===========
        tab_single = ttk.Frame(main_tab)
        main_tab.add(tab_single, text="单机测试")
        tab_single.grid_columnconfigure(0, weight=2)
        tab_single.grid_columnconfigure(1, weight=1)
        tab_single.grid_rowconfigure(0, weight=1)
        tab_single.grid_rowconfigure(1, weight=2)

        tab1_left_frame = ttk.Frame(tab_single)
        tab1_left_frame.grid(row=0, column=0, sticky='ewns', padx=0, pady=0)
        tab1_left_frame.grid_columnconfigure(0, weight=1)
        tab1_left_frame.grid_columnconfigure(1, weight=2)
        tab1_left_frame.grid_rowconfigure(0, weight=1)

        tab1_right_frame = ttk.Frame(tab_single)
        tab1_right_frame.grid(row=0, column=1, sticky='ewns', padx=0, pady=0)
        tab1_right_frame.grid_columnconfigure(0, weight=1)
        tab1_right_frame.grid_rowconfigure(1, weight=1)

        # ----------------------新增：日志区域----------------------
        log_frame = ttk.LabelFrame(tab1_right_frame, text="运行日志")
        log_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        log_frame.grid_rowconfigure(0, weight=3)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        # 垂直滚动条
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.grid(row=0, column=1, sticky="ns")

        # 文本框
        self.log_text = tk.Text(log_frame, yscrollcommand=log_scroll.set, font=("Consolas",9))
        log_scroll.config(command=self.log_text.yview)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.config(state=tk.DISABLED) # 设置默认只读

        self.image_lab = ttk.Label(log_frame, text="")
        self.image_lab.grid(row=1, column=0, sticky="nsew", pady=2)
# ----------------------------------------------------------

        # 串口区域
        serial_container = ttk.LabelFrame(tab1_left_frame, text="串口")
        serial_container.grid(row=0, column=0, sticky='ewns', padx=1, pady=0)
        serial_container.grid_columnconfigure(0, weight=2)
        serial_container.grid_columnconfigure(1, weight=3)
        serial_container.grid_columnconfigure(2, weight=8)

        ttk.Label(serial_container, text="COM端口:").grid(row=0, column=0, sticky="w", padx=5, pady=0)
        self.com_combo = ttk.Combobox(serial_container, state="readonly")
        self.com_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        self.btn_fresh_port:Button = ttk.Button(serial_container, text="刷新", command=self.refresh_port)
        self.btn_fresh_port.grid(row=1, column=0, sticky="ew", padx=4, pady=2)

        self.btn_open_serial:Button = ttk.Button(serial_container, text="打开串口", command=self.open_serial)
        self.btn_open_serial.grid(row=1, column=1, sticky="ew", padx=4, pady=2)

        self.btn_query_ip:Button = ttk.Button(serial_container, text="获取设备IP", command=self.get_ip)
        self.btn_query_ip.grid(row=2, column=0, sticky="ew", padx=4, pady=2)
        self.btn_add_ip_to_list:Button = ttk.Button(serial_container, text="添加到列表", command=self.add_to_list)
        self.btn_add_ip_to_list.grid(row=2, column=1, sticky="ew", padx=4, pady=2)

        ttk.Label(serial_container, text="IP").grid(row=3, column=0, sticky="w", padx=5, pady=0)
        self.lab_machine_ip = ttk.Entry(serial_container, font=("微软雅黑", 10), state='normal')
        self.lab_machine_ip.grid(row=3, column=1, sticky="w", padx=5, pady=0)
        ttk.Label(serial_container, text="版本").grid(row=3, column=2, sticky="w", padx=5, pady=0)
        self.lab_version = ttk.Label(serial_container, text="")
        self.lab_version.grid(row=3, column=3, sticky="w", padx=5, pady=0)
        ttk.Label(serial_container, text="路由信息").grid(row=4, column=0, sticky="w", padx=5, pady=0)
        self.lab_ssid = ttk.Entry(serial_container, font=("微软雅黑", 10), state='normal')
        self.lab_ssid.grid(row=4, column=1, sticky="w", padx=5, pady=0)
        self.lab_pwd = ttk.Entry(serial_container, font=("微软雅黑", 10), state='normal')
        self.lab_pwd.grid(row=4, column=2, sticky="w", padx=5, pady=0)
        self.btn_connect_wifi:Button = ttk.Button(serial_container, text="设置WIFI", command=self.connect_wifi)
        self.btn_connect_wifi.grid(row=4, column=3, sticky="ew", padx=4, pady=2)

        # 传感器单项测试区域
        sensor_container = ttk.LabelFrame(tab1_left_frame, text="传感器单项测试")
        sensor_container.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        sensor_container.grid_columnconfigure(0, weight=1)
        sensor_container.grid_columnconfigure(1, weight=2)
        sensor_container.grid_columnconfigure(2, weight=2)
        sensor_container.grid_columnconfigure(3, weight=2)

        ttk.Label(sensor_container, text="设备:").grid(row=0, column=0, sticky="ew", padx=5, pady=4)
        self.com_ips = ttk.Combobox(sensor_container, state="readonly")
        self.com_ips.grid(row=0, column=1, sticky="ew", padx=5, pady=4)

        self.btn_beeper_test:Button = ttk.Button(sensor_container, text="蜂鸣器响3声", command=self.beeper_test, style="Normal.TButton")
        self.btn_beeper_test.grid(row=1, column=0, sticky="ew", padx=10, pady=3)
        self.btn_beeper_test_ok:Button = ttk.Button(sensor_container, text="OK", command=lambda: self.set_btn_style(self.btn_beeper_test, "Green.TButton"))
        self.btn_beeper_test_ok.grid(row=1, column=1, sticky="ew", padx=10, pady=3)
        self.btn_beeper_test_ng:Button = ttk.Button(sensor_container, text="NG", command=lambda: self.set_btn_style(self.btn_beeper_test, "Red.TButton"))
        self.btn_beeper_test_ng.grid(row=1, column=2, sticky="ew", padx=10, pady=3)  
        self.btn_led_test:Button = ttk.Button(sensor_container, text="灯条测试", command=self.led_test)
        self.btn_led_test.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        self.btn_led_ok:Button = ttk.Button(sensor_container, text="OK", command=lambda: self.set_btn_style(self.btn_led_test, "Green.TButton"))
        self.btn_led_ok.grid(row=2, column=1, sticky="ew", padx=10, pady=3)
        self.btn_led_ng:Button = ttk.Button(sensor_container, text="NG", command=lambda: self.set_btn_style(self.btn_led_test, "Red.TButton"))
        self.btn_led_ng.grid(row=2, column=2, sticky="ew", padx=10, pady=3)
        self.btn_panelled_test:Button = ttk.Button(sensor_container, text="面版灯测试", command=self.temp_panel)
        self.btn_panelled_test.grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        self.btn_panelled_ok:Button = ttk.Button(sensor_container, text="OK", command=lambda: self.set_btn_style(self.btn_panelled_test, "Green.TButton"))
        self.btn_panelled_ok.grid(row=3, column=1, sticky="ew", padx=10, pady=3)
        self.btn_panelled_ng:Button = ttk.Button(sensor_container, text="NG", command=lambda: self.set_btn_style(self.btn_panelled_test, "Red.TButton"))
        self.btn_panelled_ng.grid(row=3, column=2, sticky="ew", padx=10, pady=3)

        self.btn_th_fan_on_test:Button = ttk.Button(sensor_container, text="风扇开", command=self.fan_on)
        self.btn_th_fan_on_test.grid(row=4, column=0, sticky="ew", padx=10, pady=4)
        self.btn_ok:Button = ttk.Button(sensor_container, text="OK", command=lambda: self.set_btn_style(self.btn_th_fan_on_test, "Green.TButton"))
        self.btn_ok.grid(row=4, column=1, sticky="ew", padx=10, pady=3)
        self.btn_ng:Button = ttk.Button(sensor_container, text="NG", command=lambda: self.set_btn_style(self.btn_th_fan_on_test, "Red.TButton"))
        self.btn_ng.grid(row=4, column=2, sticky="ew", padx=10, pady=3)
        self.btn_th_fan_off_test:Button = ttk.Button(sensor_container, text="风扇关", command=self.fan_off)
        self.btn_th_fan_off_test.grid(row=5, column=0, sticky="ew", padx=10, pady=4)
        self.btn_ok:Button = ttk.Button(sensor_container, text="OK", command=lambda: self.set_btn_style(self.btn_th_fan_off_test, "Green.TButton"))
        self.btn_ok.grid(row=5, column=1, sticky="ew", padx=10, pady=3)
        self.btn_ng:Button = ttk.Button(sensor_container, text="NG", command=lambda: self.set_btn_style(self.btn_th_fan_off_test, "Red.TButton"))
        self.btn_ng.grid(row=5, column=2, sticky="ew", padx=10, pady=3)

        self.btn_door_open_test:Button = ttk.Button(sensor_container, text="门抽屉开检测", command=self.door_open_test)
        self.btn_door_open_test.grid(row=6, column=0, sticky="ew", padx=10, pady=3)
        self.btn_door_close_test:Button = ttk.Button(sensor_container, text="门抽屉关检测", command=self.door_close_test)
        self.btn_door_close_test.grid(row=6, column=1, sticky="ew", padx=10, pady=3)

        self.btn_pump_calibrate:Button = ttk.Button(sensor_container, text="气压传感校准", command=self.pump_calibrate)
        self.btn_pump_calibrate.grid(row=7, column=0, sticky="ew", padx=10, pady=4)
        self.btn_pump_test:Button = ttk.Button(sensor_container, text="气压传感器测试", command=self.pump_test)
        self.btn_pump_test.grid(row=7, column=1, sticky="ew", padx=10, pady=4)

        self.btn_pd_test:Button = ttk.Button(sensor_container, text="PD自检", command=self.pd_test)
        self.btn_pd_test.grid(row=8, column=0, sticky="ew", padx=10, pady=4)
        self.btn_temp_test:Button = ttk.Button(sensor_container, text="温度检测", command=self.temp_test)
        self.btn_temp_test.grid(row=8, column=1, sticky="ew", padx=10, pady=4)
        self.btn_ukey_test:Button = ttk.Button(sensor_container, text="USB Key", command=self.usb_key_test)
        self.btn_ukey_test.grid(row=8, column=2, sticky="ew", padx=10, pady=4)
        
        self.btn_th_cam_test:Button = ttk.Button(sensor_container, text="近端摄像头", command=self.th_cam_test)
        self.btn_th_cam_test.grid(row=9, column=1, sticky="ew", padx=10, pady=4)
        self.btn_global_cam_test:Button = ttk.Button(sensor_container, text="远端摄像头", command=self.global_cam_test)
        self.btn_global_cam_test.grid(row=9, column=2, sticky="ew", padx=10, pady=4)
        self.btn_reset_sensors_setting:Button = ttk.Button(sensor_container, text="恢复传感器设置", command=self.reset_sensor_settings)
        self.btn_reset_sensors_setting.grid(row=9, column=0, sticky="ew", padx=10, pady=4)

        # =========== Tab2：性能测试：中间区域+右侧区域做水平分栏 ===========
        tab_perf = ttk.Frame(main_tab)
        main_tab.add(tab_perf, text="性能测试")
        perf_pane = ttk.PanedWindow(tab_perf, orient=tk.HORIZONTAL)
        perf_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 中间Tab页（设备测试结果表格）
        min_frame = ttk.Frame(perf_pane)
        perf_pane.add(min_frame, weight=3)
        self.tab_control = ttk.Notebook(min_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        min_frame.grid_columnconfigure(0, weight=1)
        min_frame.grid_rowconfigure(0, weight=1)

        # 右侧控制面板
        right_frame = ttk.Frame(perf_pane)
        perf_pane.add(right_frame, weight=2)
        right_frame.grid_columnconfigure(0, weight=1)

        self.btn_select_csv:Button =ttk.Button(right_frame, text="选择测试项CSV文件", command=self.select_csv_file)
        self.btn_select_csv.grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        ttk.Label(right_frame, text="已添加设备（勾选测试）", font=("微软雅黑", 10))\
            .grid(row=4, column=0, sticky="w", padx=10, pady=(8, 2))

        self.list_container = ttk.Frame(right_frame)
        self.list_container.grid(row=5, column=0, sticky="nsew", padx=10, pady=4)
        right_frame.grid_rowconfigure(5, weight=1)

        scroll_y = ttk.Scrollbar(self.list_container, orient=tk.VERTICAL)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_canvas = tk.Canvas(self.list_container, yscrollcommand=scroll_y.set)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.list_canvas.yview)

        self.list_inner = ttk.Frame(self.list_canvas)
        self.list_canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        self.list_inner.bind("<Configure>", lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))

        self.btn_remove_devices:Button = ttk.Button(right_frame, text="删除勾选设备", command=self.delete_checked_devices)
        self.btn_remove_devices.grid(row=6, column=0, sticky="ew", padx=10, pady=3)
        self.btn_start:Button = ttk.Button(right_frame, text="开始测试（勾选设备）", command=self.start_test)
        self.btn_start.grid(row=7, column=0, sticky="ew", padx=10, pady=(6, 12))

    def append_log(self, content):
        """线程安全添加日志，自动追加时间戳"""
        def _inner():
            self.log_text.config(state=tk.NORMAL)
            time_str = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{time_str}] {content}")
            self.log_text.see(tk.END)  # 自动滚动到底部
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, _inner)

    def refresh_port(self):
        ports = self.serial_port.get_all_com_ports()
        self.com_combo["values"] = ports
        self.com_combo.set('')
        if ports:
            self.com_combo.current(0)
        
    def open_serial(self):
        selected_com = self.com_combo.get().strip()
        if not selected_com:
            messagebox.showwarning("提示", "请先选择COM端口!")
            return
        # 判断当前串口状态
        if self.serial_port.ser and self.serial_port.ser.is_open:
            self.serial_port.close_port()
            self.btn_open_serial.config(text="打开串口")
            messagebox.showinfo("串口", "串口已关闭")
        else:
            ret = self.serial_port.open_port(selected_com, baudrate=115200)
            if ret:
                self.btn_open_serial.config(text="关闭串口")
                messagebox.showinfo("串口", f"{selected_com} 打开成功")
                self.serial_port.disconnect_callback = self.open_serial_disconnect_cb
            else:
                messagebox.showerror("串口", "打开失败，请检查端口占用")
    
    def open_serial_disconnect_cb(self):
        self.btn_open_serial.config(text="打开串口")
        self.refresh_port()
    
    def connect_wifi(self):
        ssid = self.lab_ssid.get().strip()
        pwd = self.lab_pwd.get().strip()
        if self.serial_port.run_command(command='WIFI_CONNECT', ssid=ssid, password=pwd):
            self.append_log(f'WIFI设置成功\n')
        else:
            self.append_log(f'WIFI设置失败\n')

    def get_ip(self):
        ip = self.serial_port.run_command(command='WIFI_INFO')
        print(ip)
        self.lab_machine_ip.delete(0, tk.END)
        self.lab_machine_ip.insert(0, ip)
        version = self.serial_port.run_command(command='$I')
        print(version)
        self.lab_version.config(text=version)

    def add_to_list(self):
        ip = self.lab_machine_ip.get().strip()
        if self.add_device_by_ip(ip):
            self.root.after(0, self.refresh_device_list, self.list_inner, self.list_canvas)
        self.refresh_device_test_items(ip)

    def beeper_test(self):
        msg_list = self.select_run_gcode('BEEPER_START H=0.2 L=0.2 C=3')
        if msg_list is None:
            self.append_log(f'蜂鸣器测试失败\n')
        else:
            self.append_log(f'蜂鸣器测试结束\n')
            
    def pd_test(self):
        msg_list = self.select_run_gcode('PD_TEST')

    def door_open_test(self):
        state = self.door_test()
        if state == [1, 1]:
            self.set_btn_style(self.btn_door_open_test, "Green.TButton")
        else:
            self.set_btn_style(self.btn_door_open_test, "Red.TButton")
        self.append_log(f'门抽屉开检测结束\n')

    def door_close_test(self):
        state = self.door_test()
        if state == [0, 0]:
            self.set_btn_style(self.btn_door_close_test, "Green.TButton")
        else:
            self.set_btn_style(self.btn_door_close_test, "Red.TButton")
        self.append_log(f'门抽屉关检测结束\n')

    def door_test(self):
        try:
            msg_list = self.select_run_gcode('DOOR_QUERY')
            line = msg_list[0]
            self.append_log(line)
            data = {k.strip():v.strip() for k, v in re.findall(r"([\w ]+):\s*(\w+)",line)}
            hall_state = []
            if data["Chassis Status"] == 'Closed': hall_state.append(0)
            else: hall_state.append(1)
            if data["Drawer"] == 'Closed': hall_state.append(0)
            else: hall_state.append(1)
            return hall_state
        except Exception as e:
            messagebox.showinfo(f'门抽屉检测', f'{e}')

    def temp_test(self):
        try:
            msg_list = self.select_run_gcode('BLUE_TEMP_GET')
            temp_line = msg_list[0]
            fault = False
            self.append_log(temp_line)
            data = list({k: float(v) for k, v in (p.split(":") for p in temp_line.split(","))}.values())
            temp = []
            temp.extend(data)
            str_blue_temp = f'T0:{data[0]} T1:{data[1]} T2:{data[2]}'
            msg_list = self.select_run_gcode('LW_TEMP_GET', 10)
            temp_line = msg_list[0]
            self.append_log(temp_line)
            data = list({k: float(v) for k, v in (p.split(":") for p in temp_line.split(","))}.values())
            temp.extend(data)
            for t in temp:
                if t<5 or t>45:
                    fault = True
            if fault == True:
                self.set_btn_style(self.btn_temp_test, "Red.TButton")
            else:
                self.set_btn_style(self.btn_temp_test, "Green.TButton")
            str_optical_temp = f'QCS:{data[0]} SEP:{data[1]} GALVO:{data[2]}'
            # self.root.after(0, lambda: self.lab_temp.config(text=str_blue_temp + " " + str_optical_temp))
            self.append_log(f'温度获取结束\n')
        except Exception as e:
            messagebox.showinfo(f'获取温度失败', f'{e}')

    def usb_key_test(self):
        msg_list = self.select_run_gcode('QUERY_ACCESS_KEY')
        temp_line = msg_list[0]
        if 'Access key: detected' in temp_line:
            self.set_btn_style(self.btn_ukey_test, "Green.TButton")
        else:
            self.set_btn_style(self.btn_ukey_test, "Red.TButton")
        self.append_log(f'UKey测试结束\n')

    def temp_panel(self):
        msg_log = f'面版灯测试失败\n'
        while True:
            if self.select_run_gcode('SET_LED R=80 G=0 B=0', 3) is None:
                break
            time.sleep(0.1)
            self.select_run_gcode('SET_LED R=0 G=80 B=0', 3)
            time.sleep(0.1)
            self.select_run_gcode('SET_LED R=0 G=0 B=80', 3)
            time.sleep(0.1)
            self.select_run_gcode('SET_LED R=0 G=80 B=0', 3)
            msg_log = f'面版灯测试结束\n'
            break
        self.append_log(msg_log)

    def fan_on(self):
        if self.select_run_gcode('SET_PIN PIN=th_fan VALUE=1', 3) is None:
            self.append_log(f'风扇打开失败')
            return
        self.select_run_gcode('SET_PIN PIN=qcs_fan VALUE=1', 3)
        self.select_run_gcode('SET_PIN PIN=shield_fan VALUE=1', 3)
        self.select_run_gcode('SET_PIN PIN=shield_fan_pwm VALUE=1', 3)
        self.append_log(f'风扇已打开\n')

    def fan_off(self):
        if self.select_run_gcode('SET_PIN PIN=th_fan VALUE=0', 3) is None:
            self.append_log(f'风扇关闭失败')
            return
        self.select_run_gcode('SET_PIN PIN=qcs_fan VALUE=0', 3)
        self.select_run_gcode('SET_PIN PIN=shield_fan VALUE=0', 3)
        self.select_run_gcode('SET_PIN PIN=shield_fan_pwm VALUE=0', 3)
        self.append_log(f'风扇已关闭\n')

    def led_test(self):
        for i in range(2):
            if self.select_run_gcode('SET_PIN PIN=shield_led VALUE=1', 3) is None:
                self.append_log(f'灯条测试失败\n')
                return
            msg_list = self.select_run_gcode('SET_PIN PIN=logo_led VALUE=1', 3)
            time.sleep(0.1)
            msg_list = self.select_run_gcode('SET_PIN PIN=shield_led VALUE=0', 3)
            msg_list = self.select_run_gcode('SET_PIN PIN=logo_led VALUE=0', 3)
            time.sleep(0.1)
        msg_list = self.select_run_gcode('SET_PIN PIN=shield_led VALUE=1', 3)
        msg_list = self.select_run_gcode('SET_PIN PIN=logo_led VALUE=1', 3)
        self.append_log(f'灯条测试结束\n')

    def th_cam_test(self):
        ''''''
        res = self.select_camera_capture('th')
        if res is None:
            self.append_log(f'近端摄像头，抓拍失败\n')
        else:
            self.append_log(f'近端摄像头，抓拍成功\n')
            image = Image.open(res)
            image = image.resize((400,300))
            self.img_tk = ImageTk.PhotoImage(image)
            self.root.after(0, lambda: self.image_lab.config(image=self.img_tk))

    def global_cam_test(self):
        ''''''
        res = self.select_camera_capture('global')
        if res is None:
            self.append_log(f'远端摄像头，抓拍失败\n')
        else:
            self.append_log(f'远端摄像头，抓拍成功\n')
            image = Image.open(res)
            image = image.resize((400,300))
            self.img_tk = ImageTk.PhotoImage(image)
            self.root.after(0, lambda: self.image_lab.config(image=self.img_tk))
    
    def pump_calibrate(self):
        msg_list = self.select_run_gcode('PUMP_PRESSURE_CALIBRATE', 3)
        self.append_log(f'{msg_list[0]}')
        self.append_log(f'气压传感器校准完成\n')

    def pump_test(self):
        try:
            msg_list = self.select_run_gcode('PUMP_PRESSURE_QUERY', 3)
            data_line = msg_list[0].strip().split('\n')
            data = []
            for l in data_line:
                data.append(float(l.split(':')[1].strip()))
            if data[0] - data[1] > 0.015:
                self.set_btn_style(self.btn_pump_test, "Green.TButton")
            else:
                self.set_btn_style(self.btn_pump_test, "Red.TButton")
            self.append_log(f'{msg_list[0]}')
            self.append_log(f'气压传感器测试完成\n')
        except Exception as e:
            messagebox.showerror("气压传感器测试失败", f"{e}")

    def reset_sensor_settings(self):
        msg_list = self.select_run_gcode('DOOR_SET LEVEL=job', 2)
        self.append_log(f'{msg_list[0]}')
        msg_list = self.select_run_gcode('PD_SET LEVEL=job S=600 C=400', 2)
        self.append_log(f'{msg_list[0]}')
        msg_list = self.select_run_gcode('BLUE_TEMP_SET LEVEL=always S=45 H=90 L=-10', 2)
        self.append_log(f'{msg_list[0]}')
        msg_list = self.select_run_gcode('SET_FIRE LEVEL=job S=0.45 C=50', 2)
        self.append_log(f'{msg_list[0]}')
        msg_list = self.select_run_gcode('LW_TEMP_SET LEVEL=job qcs=45 sep=45 galvo=45', 2)
        self.append_log(f'{msg_list[0]}')
        self.append_log(f'传感器恢复完成\n')

    def select_run_gcode(self, gcode, timeout=3):
        try:
            sel_ip = self.com_ips.get()
            sel_device = self.devices.get(sel_ip)
            wait_completion = WaitCompletion()
            thread = Thread(
                target=self.run_gcode_thread,
                args=(sel_device, wait_completion, gcode),
                daemon=True
                )
            thread.start()
            res = wait_completion.wait(timeout)
        except Exception as e:
            print(f'Run gcode {gcode} fail: {e}')
            res = None
        return res
    
    def run_gcode_thread(self, sel_device, wait_comp, gcode: str):
        try:
            gcode_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(gcode_event_loop)
            res = gcode_event_loop.run_until_complete(sel_device.get('client').run_gcode(gcode))
            wait_comp.complete(res)
        except Exception as e:
            print(f"{e}")
            wait_comp.complete(None)
        finally:
            gcode_event_loop.close()

    def select_camera_capture(self, camera_name, timeout=5):
        sel_ip = self.com_ips.get()
        sel_device = self.devices.get(sel_ip)
        wait_completion = WaitCompletion()
        thread = Thread(
            target=self.camera_capture_thread,
            args=(sel_device, wait_completion, camera_name),
            daemon=True
            )
        thread.start()
        res = wait_completion.wait(timeout)
        return res
    
    def camera_capture_thread(self, sel_device, wait_comp, camera_name):
        try:
            gcode_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(gcode_event_loop)
            res = gcode_event_loop.run_until_complete(sel_device.get('client').get_cv_image(camera_name))
            wait_comp.complete(res)
        except Exception as e:
            print(f"{e}")
            wait_comp.complete(None)
        finally:
            gcode_event_loop.close()

    # ========== 选择CSV文件 ==========
    def select_csv_file(self):
        
        file_path = filedialog.askopenfilename(
            title="选择测试项CSV文件",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        if self.csv_reader.read_csv(file_path):
            self.test_template = self.csv_reader.get_all_items()
            self.update_test_list()  # 修复：移除多余参数
            messagebox.showinfo("成功", f"加载测试项成功！\n共 {len(self.test_template)} 项")
        else:
            messagebox.showerror("失败", "CSV文件加载失败")

    # 修复：为单个设备更新测试项
    def refresh_device_test_items(self, ip):
        if ip not in self.devices:
            return
        tree = self.devices[ip]['tree']
        # 清空原有内容
        for item in tree.get_children():
            tree.delete(item)
        # 重新插入测试项
        for item in self.test_template.values():
            tree.insert("", "end", values=(item.get("测试项", ""), item.get("标准", ""), "", ""))

    # ========== 修复：更新测试项到表格中 ==========
    def update_test_list(self):
        for ip in self.devices:
            self.refresh_device_test_items(ip)

    # ========== 获取勾选的IP ==========
    def get_checked_ips(self):
        checked = []
        for ip, info in self.devices.items():
            if info["var"].get():
                checked.append(ip)
        return checked
    
    def on_websocket_closed(self, ip, message):
        messagebox.showerror(f'{ip}', f'{message}' )

    # ========== 测试开始前，清除显示 ==========
    def reset_test_result(self, ips):
        for ip, dev in self.devices.items():
            tree = dev['tree']
            for item_id in tree.get_children():
                vals = tree.item(item_id, "values")
                # 保留：测试项、标准；清空：测试值、结果
                new_vals = (vals[0], vals[1], "", "")
                tree.item(item_id, values=new_vals)
                # 移除背景标签，恢复原色
                tree.item(item_id, tags=())
    
    # ========== 测试过程更新UI回调 ==========
    def test_complete_callback(self, ip, result:List):
        dev = self.devices.get(ip)
        if not dev:
            return
        index = result[0]
        test_pass = result[1]    # True/False/Manual
        item_list = list(self.test_template.values())[index]
        item_gcode = item_list.get('gcode').split(' ')[0]
        item_name = item_list.get('测试项')
        logs = dev['client'].get_ws_messages()

        if item_gcode == 'CAMERAS_TEST':
            report = Report()
            mac = dev['client'].mac
            try:
                th_image_data = result[3][0]
                global_image_data = result[3][1]
                report.save_image(mac, dev['test_time'], 'th.png', th_image_data)
                report.save_image(mac, dev['test_time'], 'global.png', global_image_data)
            except Exception as e:
                print(f'图片无效:{e}')
                
        elif logs and item_gcode != 'SYS_MODE':
            report = Report()
            mac = dev['client'].mac
            if item_gcode == 'TEST_RESONANCES':
                report.downfile(mac, ip, dev['test_time'], 'resonances_x_.csv')
                report.downfile(mac, ip, dev['test_time'], 'resonances_y_.csv')
            report.save_log(mac, item_name, dev['test_time'], logs)
        
        

        if test_pass == 'Manual':
            res = messagebox.askyesno(f"{ip}", "请确认是否继续")
            if res:
                result[1] = True
                self.update_result(ip, result)
                return True
            else:
                result[1] = False
                self.update_result(ip, result)
                return False
        else:
            self.update_result(ip, result)
            return True
        
    def update_result(self, ip, result:List):
        dev = self.devices.get(ip)
        if not dev:
            return
        tree = dev['tree']
        row_index = result[0]
        test_pass = result[1]    # True/False
        test_value = result[2]  # 测试值
        result_text = "PASS" if test_pass else "FAIL"

        children = tree.get_children()
        if row_index < 0 or row_index >= len(children):
            return
        item_id = children[row_index]  # 用索引取 item_id
        current_values = tree.item(item_id, "values")
        new_values = list(current_values)
        new_values[2] = test_value
        new_values[3] = result_text
        dev['test_result'].append(new_values)
        self.root.after(0, self._update_tree_item, tree, row_index, new_values)

    # ========== 真正执行 Tree 表格更新的内部函数 ==========
    def _update_tree_item(self, tree, row_index, new_values):
        children = tree.get_children()
        if row_index < 0 or row_index >= len(children):
            return
        item_id = children[row_index]  # 用索引取 item_id

        # 赋值：测试项、标准、测试值、结果
        tree.item(item_id, values = tuple(new_values))

        # 颜色高亮
        if new_values[3] == "PASS":
            tree.tag_configure("pass", background="#90EE90")  # 浅绿
            tree.item(item_id, tags=("pass",))
        else:
            tree.tag_configure("fail", background="#FFB6C1")  # 浅红
            tree.item(item_id, tags=("fail",))
    
    def set_btn_style(self, btn: ttk.Button, style_name: str):
        self.root.after(0, lambda: btn.config(style=style_name))

    def _update_tree_color(self, tree, row_index, color):
        def inner():
            item_id = tree.get_children("")[row_index]
            tag_name = f"row_{row_index}"
            tree.tag_configure(tag_name, background=color)
            tree.item(item_id, tags=(tag_name,))
        self.root.after(0, inner)

    def set_buttons_state(self, buttons:List[Button], new_state:str):
        for btn in buttons:
            self.root.after(0, lambda b=btn : b.config(state=new_state))

    # ========== 开始测试 ==========
    def start_test(self):
        if not self.test_template:
            messagebox.showwarning("提示", "请先选择CSV测试项文件！")
            return
        checked_ips = self.get_checked_ips()
        if not checked_ips:
            messagebox.showwarning("提示", "请先勾选要测试的设备！")
            return
        self.reset_test_result(checked_ips)
        print(checked_ips)
        thread = threading.Thread(target=self.run_async_loop,args=(checked_ips,), daemon=True)
        thread.start()
        self.set_buttons_state([self.btn_add_ip_to_list ,self.btn_remove_devices, self.btn_start, self.btn_select_csv], 'disabled')
    
    def befor_test(self, ip, index):
        dev = self.devices.get(ip)
        if not dev:
            return
        tree = dev['tree']
        self.root.after(0, self._update_tree_color, tree, index, "#778487")
    
    def run_async_loop(self, ip_list):
        # 在线程中设置并运行新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for dev in self.devices.values():
            dev['test_time'] = datetime.now().strftime("%H-%M-%S")
            dev['test_result'] = []
        tasks = [self.devices[ip].get('client').test(self.test_template, self.test_complete_callback, self.on_websocket_closed, self.befor_test) for ip in ip_list]

        try:
            # 运行具体的协程
            result = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            print(result)
            report = Report()
            for r in result:
                dev = self.devices[r[2]]
                report.save_report(r[1], dev['test_time'], dev['test_result'])
        except Exception as e:
            ''''''
            print("run_async_loop 错误 =>", e)
        finally:
            self.set_buttons_state([self.btn_add_ip_to_list, self.btn_remove_devices, self.btn_start, self.btn_select_csv], 'normal')
            loop.close()

    # ------------------------------
    # 修复：设备列表刷新（渲染到带滚动的容器）
    # ------------------------------
    def refresh_device_list(self, list_inner, list_canvas):
        # 清空原有复选框
        for w in list_inner.winfo_children():
            w.destroy()
        # 重新渲染所有设备的复选框
        for idx, ip in enumerate(self.devices.keys()):
            ttk.Checkbutton(
                list_inner,
                text=ip,
                variable=self.devices[ip]["var"]
            ).grid(row=idx, column=0, sticky="w", padx=2, pady=1)
        self.com_ips['values'] = list(self.devices.keys())
        self.com_ips.current(0)
        # # 强制更新滚动区域
        list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))

    def add_device_by_ip(self, ip):
        if not ip:
            messagebox.showwarning("提示", "IP地址不能为空！")
            return False
        # print(self.devices.keys())
        if ip in self.devices:
            messagebox.showinfo("提示", f"{ip} 已添加，无需重复！")
            return False

        var = tk.BooleanVar(value=False)
        tab = ttk.Frame(self.tab_control)
        self.tab_control.add(tab, text=ip)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # 构建设备的测试表格
        tree_frame = ttk.Frame(tab)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        vs = ttk.Scrollbar(tree_frame, orient="vertical")
        hs = ttk.Scrollbar(tree_frame, orient="horizontal")
        tree = ttk.Treeview(
            tree_frame,
            columns=("name", "std", "val", "res"),
            show="headings",
            yscrollcommand=vs.set, xscrollcommand=hs.set
        )
        vs.config(command=tree.yview)
        hs.config(command=tree.xview)

        tree.heading("name", text="测试项")
        tree.heading("std", text="标准")
        tree.heading("val", text="测试值")
        tree.heading("res", text="结果")
        tree.column("name", width=180)
        tree.column("std", width=160)
        tree.column("val", width=140)
        tree.column("res", width=120)
        tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")

        # 若已有CSV模板，初始化表格；否则留空
        # if self.test_template:
        #     for item in self.test_template:
        #         tree.insert("", "end", values=(item.get("测试项", ""), item.get("标准", ""), "", ""))

        # 保存设备信息
        self.devices[ip] = {
            "var": var,
            "tab": tab,
            "tree": tree,
            "client": HttpClient(ip),
            "test_time": None,
            'test_result': []
        }
        return True

    def delete_checked_devices(self):
        to_del = [ip for ip, info in self.devices.items() if info["var"].get()]
        if not to_del:
            messagebox.showwarning("提示", "请勾选要删除的设备！")
            return
        for ip in to_del:
            self.tab_control.forget(self.devices[ip]["tab"])
            del self.devices[ip]
        self.root.after(0, self.refresh_device_list, self.list_inner, self.list_canvas)
        messagebox.showinfo("成功", f"已删除 {len(to_del)} 个设备！")

    def load_machine_list(self):
        if not os.path.exists("machinelist.txt"):
            return
        with open("machinelist.txt", "r", encoding="utf-8") as f:
            ip_count = 0
            for line in f:
                ip = line.strip()
                if ip:
                    self.add_device_by_ip(ip)
                    ip_count += 1
            if ip_count > 0:
                # 刷新设备列表显示
                self.root.after(0, self.refresh_device_list, self.list_inner, self.list_canvas)

    def save_machine_list(self):
        with open("machinelist.txt", "w", encoding="utf-8") as f:
            for ip in self.devices:
                f.write(ip + "\n")

    def on_close(self):
        self.save_machine_list()
        self.root.destroy()

# ====================== 运行程序 ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = DeviceTestApp(root)
    root.mainloop()