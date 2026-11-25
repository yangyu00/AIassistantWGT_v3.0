import logging
import re
import pandas as pd
import json
from urllib.parse import urlparse, parse_qs
from config.settings import BASE_DIR
from models.dtos import ChatResponseDTO, ContentDTO

logger = logging.getLogger(__name__)


class ArticleService:
    def __init__(self):
        """
        初始化：读取Excel并构建内存索引
        """
        logger.info("正在载入智能宣发数据...")

        self.index_map = {}  # 对象：关键字 -> 文章信息
        self.load_data()

        logger.info("智能宣发数据载入完毕")

    def load_data(self):
        """
        读取Excel文件，构建倒排索引
        """

        # 读取Excel
        df = pd.read_excel(str(BASE_DIR / "knowledge" / "articles.xlsx"))
        # 列顺序是：图片地址, 关键字, 跳转地址, 标题
        # 对应列索引：0, 1, 2, 3

        # 定义分隔符正则：匹配 英文逗号、中文逗号、顿号、斜杠、反斜杠、空格、分号
        # 你可以根据实际需求增减符号
        delimiter_pattern = r'[,\，、/\\;\s]+'

        # 遍历每一行数据
        for _, row in df.iterrows():
            keyword_str = str(row.iloc[1])  # B列：关键字
            jump_url = row.iloc[2]  # C列：跳转地址
            title = row.iloc[3]  # D列：标题
            img_url = row.iloc[0]  # A列：图片地址

            # 解析URL中的ID参数 (提取id的逻辑)
            # 例如: .../detail?id=793562089482821632
            parsed_url = urlparse(jump_url)

            # 1. 首先尝试从标准的 query 中获取（常规情况）
            query_params = parse_qs(parsed_url.query)
            article_id = query_params.get('id', [None])[0]

            # 2. 如果标准 query 为空，尝试从 fragment (哈希) 中解析
            if not article_id and parsed_url.fragment:
                # fragment 内容类似于: /message/detail?id=88...
                # 我们需要找到 '?' 的位置并截取后面的部分
                if '?' in parsed_url.fragment:
                    fragment_query = parsed_url.fragment.split('?', 1)[1]
                    fragment_params = parse_qs(fragment_query)
                    article_id = fragment_params.get('id', [None])[0]

            # 构建文章信息字典
            article_data = {
                "answer": article_id,
                "other": json.dumps({
                    "imagelink": img_url,
                    "jumplink": jump_url,
                    "title": title
                }, ensure_ascii=False),
                "class": 2
            }

            # 使用 re.split 进行多分隔符分割，并过滤空字符串
            # 如果 keyword_str 是 'nan' (float转str)，需要特殊处理或确保Excel里是字符串
            if keyword_str.lower() == 'nan':
                continue

            # 使用正则分割，自动处理多种符号
            keywords = [k.strip() for k in re.split(delimiter_pattern, keyword_str) if k.strip()]

            for kw in keywords:
                self.index_map[kw] = article_data

    def search(self, question, ) -> ChatResponseDTO:
        """核心匹配逻辑：根据用户问题查找"""
        # 遍历内存中的关键字索引，看问题里是否包含某个关键字
        for keyword, article_content in self.index_map.items():
            if keyword in question:
                # 模拟你之前返回的结构
                return ChatResponseDTO(
                    question=question,
                    code=0,
                    content=ContentDTO(**article_content, type="success"),
                    msg="success"
                )

        default_content = ContentDTO(
            type="success",
            answer="很抱歉，暂未查询到相关文章",
            class_type=2,
            other=None
        )
        return ChatResponseDTO(
            question=question,
            code=0,
            content=default_content,
            msg="很抱歉，暂未查询到相关文章"
        )
