import re
from typing import Dict, List, Optional


class TemplateParser:
    def __init__(self, template: str):
        """
        传入样板字符串，例如：
        "Side {i+1}/4 - {status} - Expected: {total_dist:.3f} mm, Detected: {actual_detected_length:.3f} mm"
        自动解析变量并生成匹配正则
        """
        self.template = template.strip()
        self.pattern, self.var_names = self._template_to_regex()

    def _template_to_regex(self, template: str):
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