import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Optional
from config.settings import BASE_DIR
from models.dtos import ChatResponseDTO, ContentDTO
from utils.dynamic_rule_matcher import DynamicRuleMatcher
from utils.dynamic_vector_matcher import DynamicVectorMatcher
from utils.extract_money import extract_money
from utils.string_process import extract_and_clean_phone

logger = logging.getLogger(__name__)


class AssistantService:
    def __init__(self):
        logger.info("正在载入ID跳转数据...")
        self.class7_matcher = DynamicRuleMatcher(excel_path=str(BASE_DIR / "knowledge" / "class7.xlsx"))
        logger.info("已载入class7数据")
        self.class1_matcher = DynamicRuleMatcher(excel_path=str(BASE_DIR / "knowledge" / "class1.xlsx"))
        logger.info("已载入class1数据")
        self.class1or4_matcher = DynamicVectorMatcher(excel_path=str(BASE_DIR / "knowledge" / "class1or4.xlsx"))
        logger.info("已载入class1or4数据")
        logger.info("ID跳转数据载入完毕")
        self.executor = ThreadPoolExecutor(max_workers=64)

    @staticmethod
    def _is_recharge_intent(text: str) -> Tuple[bool, Optional[str]]:
        """
        优化版缴费意图判断
        支持："充话费" (动作+对象), "交200" (动作+金额), "充值" (强动作)
        """
        if not text:
            return False, None

        # 1. 定义关键词
        # 动作词：单字动词，覆盖面广
        action_keywords = ['充', '缴', '交']
        # 强动作词：双字词，意图非常明确，即使没有金额或对象也能判定
        strong_action_keywords = ['充值', '缴费']
        # 对象词：业务类型
        target_keywords = ['费', '话费']

        # 2. 检测特征
        # 检测是否包含动作
        has_action = any(action in text for action in action_keywords)
        # 检测是否包含强动作
        has_strong_action = any(action in text for action in strong_action_keywords)
        # 检测是否包含业务对象
        has_target = any(target in text for target in target_keywords)
        # 检测是否包含金额
        money = extract_money(text)

        # 3. 组合判断逻辑
        # 情况A：包含强动作词 (例如用户只说了"我要缴费")
        if has_strong_action:
            return True, money

        # 情况B：包含普通动作词 (充/缴/交)
        if has_action:
            # 必须同时满足以下任意一个条件：
            # 1. 有业务对象 (充话费)
            # 2. 有金额数字 (交200)
            if has_target or money:
                return True, money

        return False, money

    async def search(self, question, phonenum) -> ChatResponseDTO:
        # 1. 文本正则
        clean_phones, text_without_phones = extract_and_clean_phone(question)
        if clean_phones:
            other = {"phoneNumber": clean_phones[0]}
        else:
            other = {"phoneNumber": phonenum}

        # 当question为纯手机号，直接返回
        if clean_phones and not text_without_phones:
            return ChatResponseDTO(
                question=question,
                code=0,
                content=ContentDTO(answer=clean_phones[0], type="电话号", class_type=3,
                                   other=other),
                msg="success"
            )

        # 2. 尝试匹配class7跳转
        rule_id = self.class7_matcher.match(text_without_phones)
        if rule_id:
            return ChatResponseDTO(
                question=question,
                code=0,
                content=ContentDTO(answer=rule_id, type="success", **{"class": 7}, other=other),
                msg="success"
            )

        # 3. 尝试匹配class1跳转
        # 3.1 尝试固定话术精准匹配
        rule_id = self.class1_matcher.match(text_without_phones)
        if rule_id:
            return ChatResponseDTO(
                question=question,
                code=0,
                content=ContentDTO(answer=rule_id, type="success", **{"class": 1}, other=other),
                msg="success"
            )

        # 3.2 尝试在class1or4中查找完全匹配项
        rule_id = self.class1or4_matcher.exact_match(text_without_phones)
        if rule_id:
            return ChatResponseDTO(
                question=question,
                code=0,
                content=ContentDTO(answer=rule_id, type="success", **{"class": 1}, other=other),
                msg="success"
            )
        # 3.3 判断是否是缴费充值业务
        is_recharge, money = self._is_recharge_intent(text_without_phones)
        other.update({"money": money})
        if is_recharge:
            return ChatResponseDTO(
                question=question,
                code=0,
                content=ContentDTO(answer="445985697623441408", type="success", **{"class": 1}, other=other),
                msg="success"
            )

        # 3.4 通过多路召回+重排序，从class1or4中拣选
        rule_ids = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.class1or4_matcher.fuzzy_match,
            text_without_phones
        )
        if rule_ids:
            class_type = 4 if len(rule_ids) > 1 else 1
            return ChatResponseDTO(
                question=question,
                code=0,
                content=ContentDTO(answer=",".join(rule_ids), type="success", **{"class": class_type}, other=other),
                msg="success"
            )

        default_content = ContentDTO(
            type="success",
            answer="很抱歉，未匹配到相关业务",
            class_type=1,
            other=None
        )
        return ChatResponseDTO(
            question=question,
            code=0,
            content=default_content,
            msg="很抱歉，未匹配到相关业务"
        )
