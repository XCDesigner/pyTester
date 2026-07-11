import re
from typing import Dict, List, Optional
from datetime import datetime
import os, paramiko
from scp import SCPClient
import csv

class TemplateParser:
    def __init__(self, template: str):
        """
        传入样板字符串，例如：
        "Side {i+1}/4 - {status} - Expected: {total_dist:.3f} mm, Detected: {actual_detected_length:.3f} mm"
        自动解析变量并生成匹配正则
        """
        self.template = template.strip()
        self.pattern, self.var_names = self._template_to_regex()

    def _template_to_regex(self):
        """
        把 {变量名:格式} 自动转换成正则捕获组
        支持：{name}, {val:.3f}, {x:.03f}
        """
        template = self.template

        # 转义正则特殊字符
        template_escaped = re.escape(template)

        # 匹配所有 {xxx} 格式变量
        var_pattern = r'\\{([^}]+)\\}'
        var_names = []
        regex_parts = []

        # 按 {变量} 分割
        parts = re.split(var_pattern, template_escaped)
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # 普通文本
                regex_parts.append(part)
            else:
                # 变量名处理
                var_full = part
                var_name = var_full.split(':')[0].strip()
                var_names.append(var_name)
                # 匹配数字/字符串的通用正则
                regex_parts.append(r'([\w\.\-\+]+)')

        full_regex = '^' + ''.join(regex_parts) + '$'
        return re.compile(full_regex.strip()), var_names

    def parse(self, log_str: str) -> Optional[Dict[str, float | str | int]]:
        """解析单行日志，返回变量字典"""
        log_str = log_str.strip()
        match = self.pattern.match(log_str)
        if not match:
            return None

        result = {}
        for name, val_str in zip(self.var_names, match.groups()):
            # 自动类型转换
            try:
                if '.' in val_str or 'e' in val_str:
                    val = float(val_str)
                else:
                    val = int(val_str)
            except:
                val = val_str.strip()
            result[name] = val
        return result

    def parse_list(self, log_lines: List[str]) -> List[Dict]:
        """批量解析多行日志"""
        return [res for line in log_lines if (res := self.parse(line))]
    

class Report:
    def __init__(self):
        ''''''

    def save_log(self, mac, test_name, test_time, log):
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f'reports/{mac}/{date_str}/{test_time}'
        file_name = f'{folder_name}/{test_name}.txt'
        print(f'store to {file_name}')
        os.makedirs(folder_name, exist_ok=True)

        with open(file_name, 'a+', encoding='utf-8') as f:
            f.write(f'========={datetime.now().strftime("%H-%M-%S")}==========\n')
            for l in log:
                f.write(l)
            f.write('\n\n')

    def save_report(self, mac, test_time, items):
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f'reports/{mac}/{date_str}/{test_time}'
        file_name = f'{folder_name}/test_report.csv'
        try:
            with open(file_name, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(["测试项", "标准", "测试值", "结果"])
                # 逐行写入表格数据
                for item in items:
                    writer.writerow(item)
        except Exception as e:
            print('导出失败')

    def save_image(self, mac, test_time, filename, image):
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f'reports/{mac}/{date_str}/{test_time}'
        file_name = f'{folder_name}/{filename}'
        print(f'save image {filename}')
        try:
            with open(file_name, "wb+") as f:
                f.write(image.getvalue())
        except Exception as e:
            print('图片保存失败')
        
    def downfile(self, mac, ip, test_time, filename):
        # 配置账号密码
        username = "ysl"
        password = "123456"

        # 构造本地目录
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f'reports/{mac}/{date_str}/{test_time}'
        os.makedirs(folder_name, exist_ok=True)

        # 远程文件路径 / 本地保存路径
        remote_dir = f"/home/ysl/printer_data/logs/"
        local_save_path = os.path.join(folder_name, filename)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        sftp = ssh.open_sftp()
        print(remote_dir)
        file_list = sftp.listdir(remote_dir)
        print(file_list)
        if filename in file_list:
            remote_file = f"{remote_dir}/{filename}"
            # SCP下载
            with SCPClient(ssh.get_transport()) as scp:
                scp.get(remote_file, local_save_path)  # 远程 → 本地

            print("下载完成")
            ssh.close()