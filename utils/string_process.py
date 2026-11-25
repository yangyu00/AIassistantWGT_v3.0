import re


def clean_and_transform_text(text):
    """
    处理字符串：
    1. 只保留中文字符、英文字母和数字。
    2. 将所有英文字母转换为大写。
    3. 剔除所有长度大于等于5位的连续数字。
    """
    # 步骤 1: 使用正则表达式只保留中文、英文和数字
    # \u4e00-\u9fa5 匹配所有常用中文字符
    # a-zA-Z 匹配所有英文字母
    # 0-9 匹配所有数字
    cleaned_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)

    # 步骤 2: 将所有字母转换为大写
    uppercased_text = cleaned_text.upper()

    # 步骤 3: 剔除长度大于等于5位的连续数字
    # \d{5,} 匹配5位或更多位的连续数字
    final_text = re.sub(r'\d{5,}', '', uppercased_text)

    return final_text


def extract_and_clean_phone(text):
    """
    从文本中提取11位中国手机号，并返回手机号列表和去除手机号后的文本。
    支持格式：纯数字、带短横线、带空格。
    """

    # 1. 定义正则表达式
    # 逻辑说明：
    # (?<!\d)      : 左边不能是数字（防止匹配到长订单号中间）
    # 1[3-9]       : 以1开头，第二位是3-9
    # \d           : 第三位数字
    # (?:[-\s]?)   : 可选的分隔符（短横线或空格），非捕获分组
    # \d{4}        : 第四到七位
    # (?:[-\s]?)   : 可选的分隔符
    # \d{4}        : 最后四位
    # (?!\d)       : 右边不能是数字
    pattern = r'(?<!\d)1[3-9]\d(?:[-\s]?)\d{4}(?:[-\s]?)\d{4}(?!\d)'

    # 2. 提取所有匹配的手机号
    # findall 会返回所有匹配到的原始字符串（包含可能的横杠或空格）
    raw_phones = re.findall(pattern, text)

    # 3. 清洗提取出的手机号（去除分隔符，统一格式）
    clean_phones = []
    for phone in raw_phones:
        # 使用 re.sub 去除所有非数字字符
        cleaned = re.sub(r'\D', '', phone)
        clean_phones.append(cleaned)

    # 4. 从原文本中移除手机号
    # 使用 re.sub 将匹配到的部分替换为空字符串
    # 注意：这里直接替换原始匹配到的片段，保留原文本中的其他标点和空格结构
    text_without_phones = re.sub(pattern, '', text)

    # 5. 可选：清理因删除手机号而产生的多余空格（例如 "Contact: 138..." 变成 "Contact: "）
    # 将多个连续空格替换为一个，并去除首尾空格
    text_without_phones = re.sub(r'\s+', ' ', text_without_phones).strip()

    return clean_phones, text_without_phones
