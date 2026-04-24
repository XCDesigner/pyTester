import csv
from typing import Dict, Optional, List

class CSVReader:
    """从CSV文件读取测试项名称、标准值"""
    def __init__(self, file_path="test_items.csv"):
        self.file_path = file_path
        self.test_items_dict: Dict[str, Dict[str, str]] = {}
        # 存储CSV文件表头信息
        self.headers: List[str] = []
        # 记录已读取的文件路径
        self.read_file_path: str = ""

    def read_csv(self, file_path: str, encoding: str = 'gbk') -> bool:
        """
        读取CSV文件并解析测试项数据
        
        Args:
            file_path: CSV文件的完整路径（绝对路径或相对路径）
            encoding: 文件编码格式，默认gbk（兼容Windows系统导出的CSV）
        
        Returns:
            bool: 读取成功返回True，失败返回False
        """
        # 重置存储数据（避免多次读取数据叠加）
        self.test_items_dict.clear()
        self.headers.clear()
        self.read_file_path = file_path
        
        try:
            # 打开CSV文件（newline='' 避免空行问题）
            with open(file_path, 'r', encoding=encoding, newline='') as csv_file:
                # 使用DictReader，直接将行数据转为字典（表头为键）
                csv_reader = csv.DictReader(csv_file)
                
                # 保存表头信息
                self.headers = csv_reader.fieldnames or []
                required_headers = ['序号', '测试项', '标准', 'gcode']
                
                # 验证CSV格式是否符合要求
                if not all(header in self.headers for header in required_headers):
                    print(f"错误：CSV文件格式不符合要求，缺少必要表头")
                    print(f"要求表头：{required_headers}")
                    print(f"实际表头：{self.headers}")
                    return False
                
                # 遍历每一行数据，结构化存储到字典
                for row_idx, row_data in enumerate(csv_reader, start=1):
                    # 以"序号"作为字典主键（转为字符串避免数字/字符串类型问题）
                    seq_num = str(row_data.get('序号', str(row_idx)))
                    
                    # 构建测试项详情字典（统一处理空值）
                    test_item_detail = {
                        '测试项': row_data.get('测试项', '未命名测试项'),
                        '标准': row_data.get('标准', '无'),
                        'gcode': row_data.get('gcode', '无')
                    }
                    
                    # 避免序号重复（重复序号会覆盖前一个）
                    if seq_num in self.test_items_dict:
                        print(f"警告：序号 {seq_num} 重复，后出现的测试项将覆盖前一个")
                    
                    # 存入核心字典
                    self.test_items_dict[seq_num] = test_item_detail
                
                # 读取成功提示
                print(f"✅ CSV文件读取成功！")
                print(f"📁 文件路径：{file_path}")
                print(f"📊 测试项总数：{len(self.test_items_dict)}")
                print(f"🏷️  表头信息：{self.headers}")
                return True
        except FileNotFoundError:
            print(f"❌ 错误：文件不存在 - {file_path}")
            return False
        except UnicodeDecodeError:
            print(f"❌ 错误：编码格式不匹配，当前使用 {encoding}")
            print("建议尝试其他编码：utf-8、gb2312、latin-1")
            return False
        except Exception as e:
            print(f"❌ 读取文件时发生未知错误：{str(e)}")
            return False
        
    def get_all_items(self) -> Dict[str, Dict[str, str]]:
        """
        获取所有测试项的完整字典
        
        Returns:
            Dict: 完整的测试项字典（{序号: 详情}）
        """
        return self.test_items_dict.copy()  # 返回副本，避免外部修改内部数据