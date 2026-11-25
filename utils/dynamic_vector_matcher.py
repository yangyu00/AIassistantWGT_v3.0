import logging
import pandas as pd
from config.settings import BASE_DIR
from sentence_transformers import SentenceTransformer
from difflib import SequenceMatcher
from utils.string_process import clean_and_transform_text
import jieba
from fuzzywuzzy import process
from difflib import SequenceMatcher
import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
import torch

logger = logging.getLogger(__name__)


class DynamicVectorMatcher:
    def __init__(self, excel_path, sheet_name='Sheet1'):
        """
        初始化匹配器，读取Excel配置并生成向量
        """
        # 1. 读取Excel，确保ID列为字符串类型
        df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype={'ID': str})

        # 确保NAME列存在，防止空文件报错
        if 'NAME' not in df.columns:
            logger.error("class1or4 中必须包含 'NAME' 列")
            raise ValueError("Excel文件中必须包含 'NAME' 列")

        # 填充空值，防止后续处理报错
        df['NAME'] = df['NAME'].fillna('')

        # 2. 利用 clean_and_transform_text 转换第二列 NAME
        df['NAME'] = df['NAME'].apply(clean_and_transform_text)

        # 3. 基于清洗后的NAME，利用模型转换为向量
        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        model_path = str(BASE_DIR / model_name)
        logger.info(f"正在加载模型 '{model_name}' (CPU模式) 并生成向量...")

        # 显式指定 device='cpu'
        self.semantic_model = SentenceTransformer(model_path, device='cpu',
                                                  tokenizer_kwargs={"fix_mistral_regex": True})

        # 将清洗后的名称转换为列表
        sentences = df['NAME'].tolist()

        # 批量生成向量 (返回的是 numpy 数组)
        embeddings = self.semantic_model.encode(sentences, show_progress_bar=True)

        # 4. 将向量保存在数据结构中
        # 方法：将向量存入一个新的列，然后将整个 df 转为字典列表
        df['VECTOR'] = list(embeddings)

        # 转为字典列表，此时每个 record 包含 'ID', 'NAME', 'VECTOR'
        self.records = df.to_dict('records')

        # 进一步处理
        self.all_names = [record.get('NAME') for record in self.records]
        vectors_list = [record.get('VECTOR') for record in self.records]
        # 过滤掉空向量，并转换为 Tensor
        valid_vectors = []
        self.valid_indices = []  # 记录有效向量在原 records 中的索引

        for idx, vec in enumerate(vectors_list):
            if vec is not None:
                if not isinstance(vec, torch.Tensor):
                    vec = torch.tensor(vec, dtype=torch.float32)
                valid_vectors.append(vec)
                self.valid_indices.append(idx)

        if valid_vectors:
            # 堆叠成矩阵，形状为 [数据量, 向量维度]
            self.all_vectors_matrix = torch.stack(valid_vectors)
        else:
            self.all_vectors_matrix = None

        logger.info(f"初始化完成，共加载 {len(self.records)} 条记录。")

    def exact_match(self, text):
        """
        精确匹配逻辑：
        1. 对输入的 text 进行清洗和转换。
        2. 遍历 self.records，取出已经清洗过的 'NAME' 字段进行比对。
        3. 如果一致，返回对应的 'ID'。
        """
        # 1. 预处理输入的文本
        processed_text = clean_and_transform_text(text)

        matched_records = []

        # 2. 遍历 records 进行查找
        for record in self.records:
            # 直接从字典获取已清洗的 NAME
            clean_name_in_db = record.get('NAME')

            # 3. 直接比较
            if processed_text in clean_name_in_db:
                # 返回对应的 ID
                matched_records.append(record.get('ID'))

        if len(matched_records) == 1:
            return matched_records[0]

        # 如果没有找到匹配项，返回 None
        return None

    def fuzzy_match(self, question, top_k=10):
        """
        多路召回 + 重排序逻辑（含矩阵加速）
        """
        candidates = {}

        # ==========================================
        # 第一路：分词匹配 (保持不变)
        # ==========================================
        words = jieba.lcut(question)
        words = [w for w in words if w.strip()]
        for record in self.records:
            name = record.get('NAME', '')
            if any(word in name for word in words):
                candidates[record.get('ID')] = record

        # ==========================================
        # 第二路：模糊字符串匹配 (保持不变)
        # ==========================================
        fuzzy_results = process.extract(question, self.all_names)
        for name, score in fuzzy_results:
            if score >= 40:
                for record in self.records:
                    if record.get('NAME') == name:
                        candidates[record.get('ID')] = record
                        break

        # ==========================================
        # 第三路：语义匹配
        # ==========================================
        if self.all_vectors_matrix is not None:
            # 1. 将问题转为向量 (1, Dimension)
            q_embedding = self.semantic_model.encode(question, convert_to_tensor=True)

            # 2. 一次性计算余弦相似度
            # 结果 shape: (1, N)，即问题与库中所有向量的相似度
            cos_scores = cos_sim(q_embedding, self.all_vectors_matrix)[0]

            # 3. 筛选大于 0.7 的索引
            # torch.where 返回满足条件的索引
            hit_indices = torch.where(cos_scores >= 0.7)[0]

            # 4. 根据索引提取记录
            for idx in hit_indices:
                # 注意：idx 是在 valid_vectors 中的索引，需要映射回 self.records 的真实索引
                real_record_idx = self.valid_indices[idx]
                record = self.records[real_record_idx]
                candidates[record.get('ID')] = record

        # ==========================================
        # 重排序
        # ==========================================
        candidate_list = list(candidates.values())
        if not candidate_list:
            return []

        def get_similarity_score(record):
            name = record.get('NAME', '')
            return SequenceMatcher(None, question, name).ratio()

        ranked_results = sorted(candidate_list, key=get_similarity_score, reverse=True)
        return [r.get('ID') for r in ranked_results[:top_k]]
