import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from models import (
    NSAnswerRule,
    NSAutoAttendantResponse,
    NSCallQueueAgent,
    NSPhoneNumber,
    NSTimeframe,
    NSUser,
)

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class NSClient:
    def __init__(
        self,
        token: str,
        api_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.token = token
        self.client = client
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.candidate_urls = []
        if api_url:
            clean_url = api_url.strip().rstrip("/")
            if not clean_url.startswith("http"):
                clean_url = f"https://{clean_url}"

            if not clean_url.endswith("/ns-api/v2"):
                clean_url += "/ns-api/v2"

            self.candidate_urls.append(clean_url)

        if not self.candidate_urls:
            logger.warning("No API URL provided to NSClient.")

        self.call_stats: Dict[str, int] = {}
        self.total_calls = 0

    def log_stats(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("--- API Call Statistics ---")
            logger.debug(f"Total Calls: {self.total_calls}")
            for endpoint, count in self.call_stats.items():
                logger.debug(f"  {endpoint}: {count}")
            logger.debug("---------------------------")

    async def _request(
        self, method: str, path: str, model: Optional[Type[T]] = None, **kwargs
    ) -> Any:
        import re

        stat_path = re.sub(r"/[0-9]+", "/{id}", path)

        self.call_stats[stat_path] = self.call_stats.get(stat_path, 0) + 1
        self.total_calls += 1

        exceptions = []

        for base_url in self.candidate_urls:
            url = f"{base_url}{path}"
            logger.debug(f"Attempting API call: {method} {url}")

            try:
                # Use provided client or create a temporary one (fallback)
                if self.client:
                    response = await self.client.request(
                        method, url, headers=self.headers, **kwargs
                    )
                else:
                    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                        response = await client.request(
                            method, url, headers=self.headers, **kwargs
                        )

                if logger.isEnabledFor(logging.DEBUG):
                    try:
                        resp_json = response.json()
                        logger.debug(
                            f"Response from {url}:\n{json.dumps(resp_json, indent=2)}"
                        )
                    except Exception:
                        logger.debug(f"Response (Text) from {url}: {response.text}")

                if response.status_code < 500:
                    if response.status_code == 404:
                        logger.info(f"Resource not found (404) at {url}")
                        return [] if model else None

                    if response.status_code >= 400:
                        logger.error(
                            f"API Error {response.status_code} from {url}: {response.text}"
                        )
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"API Error: {response.text}",
                        )

                    try:
                        data = response.json()
                        if model and isinstance(data, list):
                            return [model.model_validate(item) for item in data]
                        elif model and isinstance(data, dict):
                            return model.model_validate(data)
                        return data
                    except Exception as e:
                        logger.error(f"Failed to parse response from {url}: {e}")
                        return None

                logger.warning(
                    f"API failover triggered. {base_url} returned {response.status_code}"
                )

            except (
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as e:
                logger.warning(f"API failover triggered. {base_url} unreachable: {e}")
                exceptions.append(e)
                continue

        logger.error(f"All API endpoints failed. Exceptions: {exceptions}")
        raise HTTPException(status_code=503, detail="Upstream PBX Unreachable")

    async def _get_paginated(
        self, path: str, model: Type[T], limit: int = 1000, max_items: int = 10000
    ) -> List[T]:
        items: List[T] = []
        start = 0
        while True:
            batch = await self._request(
                "GET", path, model=model, params={"limit": limit, "start": start}
            )

            if not batch:
                break

            items.extend(batch)

            if len(items) > max_items:
                raise HTTPException(
                    status_code=413,
                    detail=f"Resource limit exceeded: >{max_items} items found at {path}",
                )

            if len(batch) < limit:
                break

            start += limit

        return items

    async def get_dids(self, domain: str) -> List[NSPhoneNumber]:
        return await self._get_paginated(
            f"/domains/{domain}/phonenumbers", model=NSPhoneNumber
        )

    async def get_users(self, domain: str) -> List[NSUser]:
        return await self._get_paginated(f"/domains/{domain}/users", model=NSUser)

    async def get_domain_timeframes(self, domain: str) -> List[NSTimeframe]:
        return await self._request(
            "GET", f"/domains/{domain}/timeframes", model=NSTimeframe
        )

    async def get_user_timeframes(self, domain: str, user: str) -> List[NSTimeframe]:
        return await self._request(
            "GET", f"/domains/{domain}/users/{user}/timeframes", model=NSTimeframe
        )

    async def get_answer_rules(self, domain: str, user: str) -> List[NSAnswerRule]:
        return await self._request(
            "GET", f"/domains/{domain}/users/{user}/answerrules", model=NSAnswerRule
        )

    async def get_auto_attendant_prompts(
        self, domain: str, user: str, prompt: str
    ) -> Optional[NSAutoAttendantResponse]:
        safe_prompt = urllib.parse.quote(prompt)
        return await self._request(
            "GET",
            f"/domains/{domain}/users/{user}/autoattendants/{safe_prompt}",
            model=NSAutoAttendantResponse,
        )

    async def get_call_queue_agents(
        self, domain: str, queue: str
    ) -> List[NSCallQueueAgent]:
        return await self._request(
            "GET",
            f"/domains/{domain}/callqueues/{queue}/agents",
            model=NSCallQueueAgent,
        )
