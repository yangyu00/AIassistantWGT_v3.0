import pandas as pd
import re
from typing import TypedDict, List, Literal

from utils.string_process import clean_and_transform_text


class KeywordGroup(TypedDict):
    type: Literal['or', 'and']
    keywords: List[str]


class DynamicRuleMatcher:
    def __init__(self, excel_path, sheet_name='Sheet1'):
        """
        初始化匹配器，读取Excel配置
        """
        # 读取Excel，确保ID列为字符串类型以防精度丢失
        df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype={'ID': str})
        # 填充空值并转为字典列表
        self.rules = df.fillna('').to_dict('records')

    def _parse_condition(self, condition_str):
        """
        解析单个单元格内的逻辑字符串
        逻辑：
        1. 括号 (...) 内的内容视为 AND 关系
        2. 括号外的内容，通过 '、' 或 ',' 或 '，'分隔，视为 OR 关系
        """
        if not condition_str:
            return []

        # 用于存储解析后的规则组，结构为 [{'type': 'and', 'keywords': [...]}, {'type': 'or', 'keywords': [...]}]
        parsed_groups: List[KeywordGroup] = []

        # 1. 提取所有括号 (...) 内的内容作为 AND 条件
        # 使用非贪婪匹配，支持中文和英文括号
        and_pattern = r'[\(（](.*?)[\)）]'
        and_matches = re.findall(and_pattern, condition_str)

        for match in and_matches:
            # 括号内如果有顿号，也视为需要同时满足的多个词
            raw_keywords = [k.strip() for k in re.split(r'[、,，]', match) if k.strip()]
            keywords = [clean_and_transform_text(k) for k in raw_keywords]

            # 过滤掉清洗后为空的词
            keywords = [k for k in keywords if k]

            if keywords:
                parsed_groups.append({'type': 'and', 'keywords': keywords})

        # 2. 处理括号外的内容作为 OR 条件
        # 将括号内容替换为空格，防止干扰后续分割
        or_part = re.sub(and_pattern, ' ', condition_str)
        # 使用顿号、逗号分割
        raw_or_keywords = [k.strip() for k in re.split(r'[、,，]', or_part) if k.strip()]
        or_keywords = [clean_and_transform_text(k) for k in raw_or_keywords]

        # 过滤掉清洗后为空的词
        or_keywords = [k for k in or_keywords if k]

        if or_keywords:
            parsed_groups.append({'type': 'or', 'keywords': or_keywords})

        return parsed_groups

    def _parse_stop_words(self, stop_words_str):
        """ 解析停止词字符串，返回列表 """
        if not stop_words_str:
            return []
        # 支持顿号、逗号分隔
        raw_words = re.split(r'[、,，]', stop_words_str)
        # 清洗并去重
        cleaned_words = set()
        for word in raw_words:
            w = clean_and_transform_text(word.strip())
            if w:
                cleaned_words.add(w)
        return list(cleaned_words)

    def match(self, text):
        """
        匹配输入文本，返回对应的 ID
        """
        if not text:
            return None

        # 预处理输入文本：清洗并转大写，用于后续匹配
        processed_text = clean_and_transform_text(text)

        for row in self.rules:
            rule_id = row.get('ID')
            condition_str = row.get('话术', '')
            stop_words_str = row.get('停止词', '')

            if not condition_str:
                continue

            # 检查停止词
            # 解析停止词
            stop_words = self._parse_stop_words(stop_words_str)
            # 如果输入文本中包含任意一个停止词，则跳过该行匹配
            if stop_words:
                if any(sw in processed_text for sw in stop_words):
                    continue

            # 解析匹配条件
            parsed_conditions = self._parse_condition(condition_str)

            # 检查当前规则是否匹配
            # 规则组之间是 OR 关系 (只要满足其中一组即可)
            is_match = False

            for group in parsed_conditions:
                keywords = group['keywords']
                if not keywords:
                    continue

                if group['type'] == 'and':
                    # AND 逻辑：所有关键词都必须存在
                    if all(kw in text for kw in keywords):
                        is_match = True
                        break
                elif group['type'] == 'or':
                    # OR 逻辑：任意一个关键词存在即可
                    if any(kw in text for kw in keywords):
                        is_match = True
                        break

            if is_match:
                return rule_id

        return None
