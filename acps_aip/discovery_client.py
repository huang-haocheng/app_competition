from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

import httpx

__all__ = [
    "DiscoveryError",
    "DiscoveryRequest",
    "DiscoveredEndpoint",
    "AgentDiscoveryClient",
    "discover_agent_endpoints",
]


class DiscoveryError(RuntimeError):
    """当拉取 Agent 发现信息失败或响应缺失必要字段时抛出。"""


@dataclass(frozen=True)
class DiscoveryRequest:
    """描述一次发现查询请求（包含查询关键字与期望技能 ID）。"""

    key: str  # 唯一键，用于将发现结果映射回具体业务 Agent
    query: str  # 发送给发现服务的查询词，例如“购物意图拆解”
    skill_id: Optional[str] = None  # 若指定，则优先匹配该技能 ID
    limit: int = 5  # 远端返回的候选数量上限


@dataclass
class DiscoveredEndpoint:
    """封装好的发现结果，包含可直接调用的 RPC 端点 URL。"""

    key: str  # 对应的业务键
    name: str  # Agent 名称或技能描述
    skill_id: Optional[str]
    endpoint_url: str  # 真实可调用的 RPC 接口地址
    raw: Dict[str, Any]  # 远端完整响应，便于调试


class AgentDiscoveryClient:
    """封装远程发现服务的 HTTP 调用，提供批量查询能力。"""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """初始化客户端基础配置。"""

        if not base_url:
            raise ValueError("base_url is required for discovery")

        # 统一记录 URL/超时/请求头，便于后续复用
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self._headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            self._headers.update(headers)

    async def fetch_many(
        self, requests: Iterable[DiscoveryRequest]
    ) -> Dict[str, DiscoveredEndpoint]:
        """并发发送多个发现请求，返回键到端点的映射。"""

        request_list = list(requests)
        if not request_list:
            return {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [self._discover_single(client, req) for req in request_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        endpoints: Dict[str, DiscoveredEndpoint] = {}
        errors: List[str] = []
        for req, result in zip(request_list, results):
            if isinstance(result, Exception):
                message = str(result)
                if not message:
                    message = repr(result)
                errors.append(
                    f"{req.key}: {type(result).__name__}: {message}"
                )
            else:
                endpoints[req.key] = result

        if errors:
            raise DiscoveryError(
                "Failed to discover required agents:\n" + "\n".join(errors)
            )
        return endpoints

    async def _discover_single(
        self, client: httpx.AsyncClient, request: DiscoveryRequest
    ) -> DiscoveredEndpoint:
        """针对单个请求调用发现服务，并解析第一条可用端点。"""

        payload = {"query": request.query, "limit": request.limit}
        response = await client.post(
            self.base_url,
            json=payload,
            headers=self._headers,
        )
        response.raise_for_status()
        data = response.json()
        entry = self._select_agent(data.get("agents") or [], request.skill_id)
        if entry is None:
            raise DiscoveryError(
                f"No agent returned for query '{request.query}' (skill_id={request.skill_id})"
            )

        endpoint_url = self._extract_endpoint(entry)
        acs = entry.get("acs") or {}
        name = acs.get("name") or entry.get("skill_description") or request.key
        skill_id = entry.get("skill_id") or request.skill_id
        return DiscoveredEndpoint(
            key=request.key,
            name=name,
            skill_id=skill_id,
            endpoint_url=endpoint_url,
            raw=entry,
        )

    @staticmethod
    def _select_agent(
        entries: List[Dict[str, Any]], skill_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """优先按 skill_id 精确匹配，否则回退到列表首个候选。"""

        if skill_id:
            for entry in entries:
                if entry.get("skill_id") == skill_id:
                    return entry
                skill_info = entry.get("skill") or {}
                if skill_info.get("id") == skill_id:
                    return entry
        return entries[0] if entries else None

    @staticmethod
    def _extract_endpoint(entry: Dict[str, Any]) -> str:
        """从 ACS 描述中提取第一个可用的 `endPoints.url`。"""

        acs = entry.get("acs") or {}
        for endpoint in acs.get("endPoints") or []:
            url = endpoint.get("url")
            if url:
                print(url)
                return url
        raise DiscoveryError("Discovery response did not include a valid endpoint URL")


async def discover_agent_endpoints(
    base_url: str,
    config: Mapping[str, Dict[str, Any]],
    *,
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, DiscoveredEndpoint]:
    """基于传入配置批量发现 Agent 端点。

    Args:
        base_url: 发现服务的基础 URL。
        config: 键到配置的映射，配置中可包含 ``query``、``skill_id``、``limit``。
        timeout: HTTP 请求超时秒数。
        headers: 附加的 HTTP 头，例如鉴权信息。

    Returns:
        业务键到发现结果的映射。

    Raises:
        DiscoveryError: 当任意请求失败或缺少必需字段时抛出。
        ValueError: 当配置缺少查询词时抛出。
    """

    if not base_url:
        raise ValueError("base_url is required for discovery")

    requests: List[DiscoveryRequest] = []
    for key, settings in config.items():
        settings = settings or {}
        query = settings.get("query")
        if not query:
            raise ValueError(f"Discovery config for '{key}' must include a query")
        skill_id = settings.get("skill_id")
        limit_value = settings.get("limit", 5)
        try:
            limit = int(limit_value)
        except (TypeError, ValueError):
            limit = 5
        requests.append(
            DiscoveryRequest(
                key=key,
                query=query,
                skill_id=skill_id,
                limit=limit,
            )
        )

    client = AgentDiscoveryClient(base_url, timeout=timeout, headers=headers)
    return await client.fetch_many(requests)
