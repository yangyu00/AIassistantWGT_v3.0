import logging
from datetime import datetime
from contextlib import asynccontextmanager
import uvicorn
from typing import AsyncIterator
from fastapi import FastAPI
from config.settings import settings
from models.dtos import ChatRequestDTO, AbilityCode, ChatResponseDTO
from services.article_service import ArticleService
from services.assistant_service import AssistantService
from utils.response_builder import success_response, register_errors_handlers, error_response
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

article_matcher = None
assistant_matcher = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global article_matcher, assistant_matcher
    try:
        logger.info("🚀 应用正在启动，正在初始化客户端...")
        article_matcher = ArticleService()
        assistant_matcher = AssistantService()

        yield

    except Exception as e:
        logger.critical(f"❌ 应用启动失败 - {str(e)}")

    finally:
        logger.info("🧹 应用正在关闭...")


app = FastAPI(lifespan=lifespan)
register_errors_handlers(app)


@app.post("/api/chat_agent")
async def market_assistant(args: ChatRequestDTO) -> ChatResponseDTO:
    logger.info(f"收到请求 - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, 参数: {args.model_dump()}")
    start_time = time.perf_counter()

    # 话术功能已废弃
    if args.abilityCode == AbilityCode.SCRIPT:
        return success_response(
            question=args.question,
            answer="",
            type_val="success",
            class_type=0,
            other=None
        )
    try:
        if args.abilityCode == AbilityCode.ARTICLE:
            if isinstance(article_matcher, ArticleService):
                article_output = article_matcher.search(args.question)
                if "phoneNumber" not in article_output.content.other and args.phonenum:
                    article_output.content.other = {"phoneNumber": args.phonenum}
                return article_output

        if args.abilityCode == AbilityCode.AI_ASSISTANT:
            if isinstance(assistant_matcher, AssistantService):
                rule_id_output = await assistant_matcher.search(args.question, args.phonenum)
                return rule_id_output

    except Exception as e:
        logger.error(e)

    finally:
        duration = time.perf_counter() - start_time
        logger.info(f"请求处理完成 - 耗时: {duration:.3f}秒")

    return error_response(
        question=args.question,
        error_msg="未知的终点"
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=False)
