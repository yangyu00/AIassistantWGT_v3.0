from enum import IntEnum, Enum
from typing import Optional, List, Union, Dict, Any, Literal
from pydantic import BaseModel, Field


# --- 1. 枚举定义 ---
class AbilityCode(int, Enum):
    """能力编码枚举 """
    SCRIPT = 0  # 标签查询话术
    AI_ASSISTANT = 1  # AI助手 (智能问答/跳转)
    ARTICLE = 2  # 产品宣发超链接


# --- 2. DTO 对象设计 ---
class ChatRequestDTO(BaseModel):
    """
    请求参数 DTO (对应文档 '三、输入参数')
    """
    question: str = Field(..., description="用户输入文字")
    user: Literal["网格通"] = Field(..., description="确定用户身份，固定（网格通）", example="网格通")
    abilityCode: AbilityCode = Field(..., description="能力编码: 0-话术, 1-AI助手, 2-宣发")

    user_id: str = Field(None, description="用户ID，用于上下文")
    phonenum: Optional[str] = Field(None, description="电话号")
    label1: Optional[str] = Field(None, description="标签1 (abilityCode=0时必填)")
    label2: Optional[str] = Field(None, description="标签2 (abilityCode=0时必填)")
    history: Optional[List[List[str]]] = Field(default_factory=list, description="历史聊天记录")


class OtherInfo(BaseModel):
    """
    定义 other 字段可能的对象结构
    """
    phoneNumber: Optional[str] = Field(None, description="电话号码")
    money: Optional[str] = Field(None, description="金额")


class ContentDTO(BaseModel):
    """
    响应内容 DTO (对应文档 '四、输出参数' 中的 content 字段)
    """
    type: Optional[str] = Field(None, description="内容描述，异常时为None")
    answer: Union[str, Dict] = Field(..., description="输出内容/跳转ID/电话号码")
    class_type: Optional[int] = Field(None, alias="class",
                                      description="返回类型: 0-话术, 1-单一常规展位跳转, 2-智能宣发, 3-电话号, 4-多个常规展位跳转, 7-单一特殊展位跳转")
    other: Optional[Union[OtherInfo, str]] = Field(None, description="其他参数，可以是对象或JSON字符串")


class ChatResponseDTO(BaseModel):
    """
    统一响应 DTO (对应文档 '四、输出参数')
    """
    question: str = Field(..., description="用户问题回显")
    code: int = Field(..., description="状态码: 0-成功, 1-失败")
    content: Union[ContentDTO, str, None] = Field(None, description="返回内容对象或字符串")
    msg: str = Field(..., description="返回信息描述")
