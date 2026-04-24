import csv

class CSVReader:
    """从CSV文件读取测试项名称、标准值"""
    def __init__(self, file_path="test_items.csv"):
        self.file_path = file_path
        self.test_items = []  # 格式: [{"name":"xxx", "standard":"xxx"}, ...]

    def load(self):
        """加载CSV"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.test_items = [row for row in reader]
            return True
        except Exception as e:
            print(f"CSV加载失败: {e}")
            return False
        
    