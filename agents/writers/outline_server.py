from __future__ import annotations
import colorama
colorama.just_fix_windows_console()
import json
import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI

_CURRENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CURRENT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from base import get_agent_logger, load_capabilities_snippet_from_json
from transform_ import to_json
from outline_writer import OutlineWriter
from acps_aip.aip_rpc_server import add_aip_rpc_router
from acps_aip.single_turn_server import make_single_turn_handlers
from acps_aip.mtls_config import load_mtls_config_from_json

AGENT_ID = 'outline_writer'
AIP_ENDPOINT = os.getenv("OUTLINE_WRITER_AIP_ENDPOINT", "/outline_writer")
LOG_LEVEL = os.getenv("OUTLINE_WRITER_LOG_LEVEL", "INFO").upper()
CONFIG_JSON = "./agents/writers/outline_writer.json"

logger = get_agent_logger("agent.outline_writer", "OUTLINE_WRITER_LOG_LEVEL", LOG_LEVEL)

app = FastAPI(
    title="分镜大纲 Writer Agent",
    description="根据用户需求生成分镜大纲的 ACPs 兼容服务",
)

agent = OutlineWriter()

def _ensure_payload(text: str) -> str:
    """确保传入的字符串能转换为符合 ACPs 规范的 JSON 数据。

    此函数会尝试解析输入文本，如已是包含 data 字段的 JSON 结构，直接返回；
    否则通过 `to_json` 包装成字符串格式，方便 Agent 逻辑统一处理。

    Args:
        text: 来自 RPC 调用的原始输入文本。

    Returns:
        一个符合 Agent 处理约定的 JSON 字符串。
    """
    logger.debug("event=ensure_payload_start input_length=%d", len(text))
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "data" in obj:
            logger.debug("event=ensure_payload_complete format=already_json")
            return text
    except json.JSONDecodeError:
        logger.debug("event=ensure_payload_convert format=to_json")
        pass
    result = to_json(text)
    logger.debug("event=ensure_payload_complete format=converted_json")
    return result

def _process(text: str) -> str:
    """调用 Decision_Agent，返回拆解后的任务文本。

    Args:
        text: RPC 层透传的原始用户输入。

    Returns:
        Agent 逻辑处理后的文本结果（包含任务分解结构）。
    """
    logger.info("event=processing_start input_length=%d", len(text))
    try:
        payload = _ensure_payload(text)
        result = agent.call(payload)
        logger.info("event=processing_complete output_length=%d", len(result))
        return result
    except Exception as e:
        logger.error("event=processing_failed error=%s", str(e), exc_info=True)
        raise

handlers = make_single_turn_handlers(
    agent_id=AGENT_ID,
    processor=_process,
    empty_input_message="缺少用户输入，无法生成分镜大纲。",
    error_prefix="任务失败：",
)

add_aip_rpc_router(app, AIP_ENDPOINT, handlers)
CAPABILITIES_SNIPPET = load_capabilities_snippet_from_json(
    CONFIG_JSON,
    fallback="根据用户需求生成分镜大纲。",
)

@app.get("/")
def read_root():
    """健康检查与能力描述接口，供外部调用确认 Agent 状态。"""
    logger.info("event=health_check")
    return {
        "message": "分镜大纲 Agent 就绪",
        "agent_id": AGENT_ID,
        "capabilities": CAPABILITIES_SNIPPET,
        "endpoint": AIP_ENDPOINT,
    }

if __name__ == "__main__":
    import ssl
    import uvicorn

    mtls_config = load_mtls_config_from_json(
        CONFIG_JSON, cert_dir=os.path.join(_PROJECT_ROOT, "certs")
    )
    logger.info(
        "event=server_start agent_id=%s endpoint=%s", AGENT_ID, AIP_ENDPOINT
    )
    # 直接运行时开启 HTTPS 服务，为外部客户端提供 ACPs RPC 调用端点。
    uvicorn.run(
        "agents.writers.outline_server:app",
        host='0.0.0.0',
        port=8032,
        ssl_keyfile=str(mtls_config.key_file),
        ssl_certfile=str(mtls_config.cert_file),
        ssl_ca_certs=str(mtls_config.ca_cert_file),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        workers=1,
    )