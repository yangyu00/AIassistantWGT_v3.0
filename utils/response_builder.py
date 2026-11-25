from typing import Union, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from models.dtos import ChatResponseDTO, ContentDTO


def success_response(
        question: str,
        answer: Union[str, Dict],
        type_val: str = None,
        class_type: int = 0,
        other: str = None
) -> ChatResponseDTO:
    """
    构建成功响应
    """
    content = ContentDTO(
        type=type_val,
        answer=answer,
        class_type=class_type,
        other=other
    )
    return ChatResponseDTO(
        question=question,
        code=0,
        content=content,
        msg="success"
    )


def error_response(
        question: str,
        error_msg: str,
        type_val: str = "None",
        answer: str = "系统异常"
) -> ChatResponseDTO:
    """
    构建失败响应
    """
    content = ContentDTO(
        type=type_val,
        answer=answer,
        class_type=0
    )
    return ChatResponseDTO(
        question=question,
        code=1,
        content=content,
        msg=error_msg
    )


def register_errors_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        try:
            req_json = await request.json()
            question = req_json.get("question", "")
        except:
            question = ""

        # 遍历错误信息，判断缺失或错误的字段
        for error in exc.errors():
            # 检查 user_id 是否缺失
            if "user_id" in str(error):
                return error_response(
                    question=question,
                    error_msg="user_id参数缺失",
                    type_val="None",
                    answer="user_id参数缺失"
                )
            # 检查 abilityCode 是否缺失或值错误
            elif "abilityCode" in str(error):
                return error_response(
                    question=question,
                    error_msg="abilityCode参数输入错误，请输入0或1或2",
                    type_val="None",
                    answer="abilityCode参数输入错误，请输入0或1或2"
                )

        # 默认的参数校验错误
        return error_response(
            question=question,
            error_msg="参数校验错误",
            type_val="None",
            answer="参数校验错误"
        )
