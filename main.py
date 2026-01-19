import argparse
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from ns_client import NSClient
from graph_builder import GraphBuilder
from typing import Optional, List
from models import CytoscapeElement
import logging
from config import settings
from security import DomainWhitelist
import httpx

# Setup Logging
LOG_LEVEL = logging.INFO
if os.getenv("DEBUG", "").lower() in ("true", "1", "yes"):
    LOG_LEVEL = logging.DEBUG

logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="NetSapiens Call Flow Visualizer")

templates = Jinja2Templates(directory="templates")

whitelist = DomainWhitelist(settings.WHITELIST_FILE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/static/route_graph_inventory_tab.js")
async def get_js_loader(request: Request):
    return templates.TemplateResponse(
        "route_graph_inventory_tab.js",
        {"request": request, "api_endpoint": settings.PUBLIC_API_URL},
        media_type="application/javascript",
    )


@app.get("/graph", response_model=List[CytoscapeElement])
async def get_graph(
    domain: str,
    token: str,
    api_url: Optional[str] = Query(None, description="Primary NetSapiens API URL"),
):
    logger.info(f"Received request for domain: {domain}")

    if api_url:
        whitelist.validate_or_raise(api_url)

    async with httpx.AsyncClient(timeout=10.0, verify=False) as http_client:
        client = NSClient(token, api_url, client=http_client)
        builder = GraphBuilder(client, domain)

        try:
            graph = await builder.build()
            logger.info(
                f"Successfully built graph for {domain} with {len(graph)} elements."
            )

            if logger.isEnabledFor(logging.DEBUG):
                import json

                graph_json = json.dumps([g.model_dump() for g in graph], indent=2)
                logger.debug(f"Final Graph JSON for {domain}:\n{graph_json}")

                client.log_stats()

            return graph
        except HTTPException as e:
            logger.warning(f"HTTP Exception: {e.detail}")
            raise e
        except Exception as e:
            logger.error(f"Error building graph: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the NetSapiens Call Flow Visualizer API"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.info("Debug logging enabled via command line argument.")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
