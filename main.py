from http_client import HttpClient
import asyncio
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from cvs_reader import CSVReader
import threading
from typing import Dict, Optional, List
import os
from datetime import datetime

class DeviceTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("设备测试工具")
        self.root.geometry("1280x720")
        self.root.minsize(1000, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.csv_reader = CSVReader()
        self.test_template = []
        self.devices = {}

        self.create_widgets()
        self.load_machine_list()

    def create_widgets(self):
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧 TAB
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=4)
        self.tab_control = ttk.Notebook(left_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # 右侧控制面板
        right_frame = ttk.Frame(main_pane, width=320)
        main_pane.add(right_frame, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # 选择CSV文件按钮
        ttk.Button(right_frame, text="选择测试项CSV文件", command=self.select_csv_file)\
            .grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        # IP输入
        ttk.Label(right_frame, text="设备IP", font=("微软雅黑", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=2)
        self.ip_entry = ttk.Entry(right_frame, font=("微软雅黑", 10))
        self.ip_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=2)
        self.ip_entry.insert(0, "127.0.0.1")

        ttk.Button(right_frame, text="添加设备", command=self.add_device)\
            .grid(row=3, column=0, sticky="ew", padx=10, pady=6)
        ttk.Label(right_frame, text="已添加设备（勾选测试）", font=("微软雅黑", 10))\
            .grid(row=4, column=0, sticky="w", padx=10, pady=(8, 2))

        # 修复：为设备列表添加滚动条（核心改动1）
        self.list_container = ttk.Frame(right_frame)
        self.list_container.grid(row=5, column=0, sticky="nsew", padx=10, pady=4)
        right_frame.grid_rowconfigure(5, weight=1)  # 让列表容器占满剩余高度
        
        # 滚动条 + Canvas 实现列表滚动
        scroll_y = ttk.Scrollbar(self.list_container, orient=tk.VERTICAL)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_canvas = tk.Canvas(self.list_container, yscrollcommand=scroll_y.set)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.list_canvas.yview)
        
        self.list_inner = ttk.Frame(self.list_canvas)
        self.list_canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        # 自动更新滚动区域
        self.list_inner.bind("<Configure>", lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))

        # 功能按钮
        ttk.Button(right_frame, text="删除勾选设备", command=self.delete_checked_devices)\
            .grid(row=6, column=0, sticky="ew", padx=10, pady=3)
        ttk.Button(right_frame, text="开始测试（勾选设备）", command=self.start_test)\
            .grid(row=7, column=0, sticky="ew", padx=10, pady=(6, 12))

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
            # 加载CSV后更新所有设备的测试列表
            for ip in self.devices:
                self.refresh_device_test_items(ip)
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
    
    # ========== 测试开始前，清除显示 ==========
    def reset_test_result(self, ips):
        # 1. 生成外层日期目录
        date_str = datetime.now().strftime("%Y-%m-%d")
        if not os.path.exists(date_str):
            os.makedirs(date_str)
            print(f"已创建日期根目录：{date_str}")

        # 2. 在日期目录下，为每个勾选IP创建独立子文件夹
        for ip in ips:
            ip_dir = os.path.join(date_str, ip)
            if not os.path.exists(ip_dir):
                os.makedirs(ip_dir)
                print(f"已创建设备目录：{ip_dir}")

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
        self.update_ui(ip, result)
        index = result[0]
        test_pass = result[1]    # True/False/Manual
        report = dev['client'].get_ws_messages()
        if test_pass == 'Manual':
            res = messagebox.askyesno(f"{ip}", "请确认是否继续")
            if res:
                result[1] = True
                self.update_ui(ip, result)
                return True
            else:
                result[1] = False
                self.update_ui(ip, result)
                return False
        else:
            self.update_ui(ip, result)
            return True

    def update_ui(self, ip, result:List):
        dev = self.devices.get(ip)
        if not dev:
            return
        tree = dev['tree']
        row_index = result[0]
        test_pass = result[1]    # True/False
        test_value = result[2]  # 测试值
        result_text = "PASS" if test_pass else "FAIL"

        # 👇 必须用 after 安全更新 UI（tkinter 跨线程唯一正确写法）
        self.root.after(0, self._update_tree_item, tree, row_index, test_value, result_text)

    # ========== 真正执行 Tree 表格更新的内部函数 ==========
    def _update_tree_item(self, tree, row_index, test_value, result_text):
        children = tree.get_children()
        if row_index < 0 or row_index >= len(children):
            return
        item_id = children[row_index]  # 用索引取 item_id
        current_values = tree.item(item_id, "values")

        # 赋值：测试项、标准、测试值、结果
        tree.item(item_id, values=(
            current_values[0],
            current_values[1],
            test_value,
            result_text
        ))

        # 颜色高亮
        if result_text == "PASS":
            tree.tag_configure("pass", background="#90EE90")  # 浅绿
            tree.item(item_id, tags=("pass",))
        else:
            tree.tag_configure("fail", background="#FFB6C1")  # 浅红
            tree.item(item_id, tags=("fail",))

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
    
    def run_async_loop(self, ip_list):
        # 在线程中设置并运行新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [self.devices[ip].get('client').test(self.test_template, self.test_complete_callback) for ip in ip_list]

        try:
            # 运行具体的协程
            result = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        except Exception as e:
            ''''''
            print("run_async_loop 错误 =>", e)
        finally:
            loop.close()

    # ------------------------------
    # 修复：设备列表刷新（渲染到带滚动的容器）
    # ------------------------------
    def refresh_device_list(self):
        # 清空原有复选框
        for w in self.list_inner.winfo_children():
            w.destroy()
        # 重新渲染所有设备的复选框
        for idx, ip in enumerate(self.devices.keys()):
            ttk.Checkbutton(
                self.list_inner,
                text=ip,
                variable=self.devices[ip]["var"]
            ).grid(row=idx, column=0, sticky="w", padx=2, pady=1)
        # 强制更新滚动区域
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))

    # 修复：移除CSV前置校验，允许先加设备（核心改动2）
    def add_device_by_ip(self, ip):
        if not ip:
            messagebox.showwarning("提示", "IP地址不能为空！")
            return
        if ip in self.devices:
            messagebox.showinfo("提示", f"{ip} 已添加，无需重复！")
            return

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
        if self.test_template:
            for item in self.test_template:
                tree.insert("", "end", values=(item.get("name", ""), item.get("standard", ""), "", ""))

        # 保存设备信息
        self.devices[ip] = {
            "var": var,
            "tab": tab,
            "tree": tree,
            "client": HttpClient(ip)
        }
        # 刷新设备列表显示
        self.refresh_device_list()

    def add_device(self):
        ip = self.ip_entry.get().strip()
        self.add_device_by_ip(ip)

    def delete_checked_devices(self):
        to_del = [ip for ip, info in self.devices.items() if info["var"].get()]
        if not to_del:
            messagebox.showwarning("提示", "请勾选要删除的设备！")
            return
        for ip in to_del:
            self.tab_control.forget(self.devices[ip]["tab"])
            del self.devices[ip]
        self.refresh_device_list()
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
                messagebox.showinfo("成功", f"从配置文件加载 {ip_count} 个设备！")

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