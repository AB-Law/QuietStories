"""
Prompt enrichment API — optionally expands a user's scenario description
before generation.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel

from backend.providers.factory import create_provider
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_ENRICH_SYSTEM = """You are a writing assistant helping to add context to story scenarios.

Rules:
- Keep the user's exact writing style and tone
- Don't add poetic or literary language unless the user already uses it
- Add 1-2 sentences of context at most
- Stay focused on what the user is asking for
- If the description is already clear, add very little

Keep it short and simple."""

_ENRICH_USER = """Original scenario: {description}

Add minimal context (1-2 sentences max) to clarify this for story generation:"""


class EnrichRequest(BaseModel):
    description: str


class EnrichResponse(BaseModel):
    original: str
    enriched: str


@router.post("/enrich", response_model=EnrichResponse)
async def enrich_prompt(request: EnrichRequest):
    """Lightly expand a scenario description before sending to the generator."""
    if len(request.description.strip()) < 10:
        raise HTTPException(status_code=400, detail="Description must be at least 10 characters")

    try:
        provider = create_provider()
        response = await provider.chat([
            SystemMessage(content=_ENRICH_SYSTEM),
            HumanMessage(content=_ENRICH_USER.format(description=request.description)),
        ])
        return EnrichResponse(original=request.description, enriched=response.content.strip())
    except Exception as e:
        logger.error(f"Prompt enrichment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {e}")
