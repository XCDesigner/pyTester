from http_client import HttpClient
import asyncio
import os
import tkinter as tk
from tkinter import ttk, messagebox
from cvs_reader import CSVReader

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

        # 复选框列表容器
        self.list_container = ttk.Frame(right_frame)
        self.list_container.grid(row=5, column=0, sticky="nsew", padx=10, pady=4)
        right_frame.grid_rowconfigure(5, weight=1)

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

        if self.csv_reader.load(file_path):
            self.test_template = self.csv_reader.test_items
            messagebox.showinfo("成功", f"加载测试项成功！\n共 {len(self.test_template)} 项")
        else:
            messagebox.showerror("失败", "CSV文件加载失败")

    # ========== 获取勾选的IP ==========
    def get_checked_ips(self):
        checked = []
        for ip, info in self.devices.items():
            if info["var"].get():
                checked.append(ip)
        return checked

    # ========== 开始测试 ==========
    def start_test(self):
        if not self.test_template:
            messagebox.showwarning("提示", "请先选择CSV测试项文件！")
            return

        checked_ips = self.get_checked_ips()
        if not checked_ips:
            messagebox.showwarning("提示", "请先勾选要测试的设备！")
            return
        asyncio.run(self.run_test(checked_ips))

    async def run_test(self, ip_list):
        for ip in ip_list:
            if ip not in self.devices:
                continue

            device = self.devices[ip]
            tree = device["tree"]
            client = device["client"]
            self.tab_control.select(device["tab"])

            connected = await client.connect()
            if not connected:
                messagebox.showerror("连接失败", f"{ip} 连接失败")
                continue

            rows = tree.get_children()
            for i, item in enumerate(self.test_template):
                test_name = item["name"]
                standard = item["standard"]

                await client.send({
                    "device": ip,
                    "test_item": test_name,
                    "standard": standard
                })

                test_value = "正常"
                result = "合格"
                if i < len(rows):
                    tree.item(rows[i], values=(test_name, standard, test_value, result))

            await client.close()

        messagebox.showinfo("测试完成", "所有勾选设备已测试完毕！")

    # ------------------------------
    # 设备列表刷新
    # ------------------------------
    def refresh_device_list(self):
        for w in self.list_container.winfo_children():
            w.destroy()
        for idx, ip in enumerate(self.devices.keys()):
            ttk.Checkbutton(
                self.list_container,
                text=ip,
                variable=self.devices[ip]["var"]
            ).grid(row=idx, column=0, sticky="w")

    def add_device_by_ip(self, ip):
        if not ip or ip in self.devices:
            return
        if not self.test_template:
            messagebox.showwarning("提示", "请先选择CSV测试项文件！")
            return

        var = tk.BooleanVar(value=False)
        tab = ttk.Frame(self.tab_control)
        self.tab_control.add(tab, text=ip)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

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

        for item in self.test_template:
            tree.insert("", "end", values=(item.get("name", ""), item.get("standard", ""), "", ""))

        self.devices[ip] = {
            "var": var,
            "tab": tab,
            "tree": tree,
            "client": WebSocketJsonClient(ip)
        }
        self.refresh_device_list()

    def add_device(self):
        self.add_device_by_ip(self.ip_entry.get().strip())

    def delete_checked_devices(self):
        to_del = [ip for ip, info in self.devices.items() if info["var"].get()]
        if not to_del:
            messagebox.showwarning("提示", "请勾选要删除的设备")
            return
        for ip in to_del:
            self.tab_control.forget(self.devices[ip]["tab"])
            del self.devices[ip]
        self.refresh_device_list()

    def load_machine_list(self):
        if not os.path.exists("machinelist.txt"):
            return
        with open("machinelist.txt", "r", encoding="utf-8") as f:
            for line in f:
                ip = line.strip()
                if ip:
                    self.add_device_by_ip(ip)

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