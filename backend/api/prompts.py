"""
Prompt enrichment API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.prompts import PROMPT_ENRICHMENT_SYSTEM, PROMPT_ENRICHMENT_USER
from backend.providers.factory import create_provider
from backend.config import settings
from backend.utils.logger import get_logger

# Set up logging
logger = get_logger(__name__)

router = APIRouter()


class PromptEnrichRequest(BaseModel):
    """Request to enrich a prompt"""
    description: str
    max_tokens: Optional[int] = 500


class PromptEnrichResponse(BaseModel):
    """Response from prompt enrichment"""
    original: str
    enriched: str


@router.post("/enrich", response_model=PromptEnrichResponse)
async def enrich_prompt(request: PromptEnrichRequest):
    """
    Enrich a simple scenario description into a detailed prompt
    
    Takes a brief user description and uses the LLM to expand it into
    a rich, engaging scenario prompt suitable for generating a full ScenarioSpec.
    """
    
    logger.info("="*60)
    logger.info(f"PROMPT ENRICHMENT REQUEST")
    logger.info(f"Description: {request.description[:50]}...")
    logger.debug(f"Full description: {request.description}")
    logger.debug(f"Max tokens: {request.max_tokens}")
    
    if not request.description or len(request.description.strip()) < 10:
        logger.warning("✗ Description too short (minimum 10 characters)")
        raise HTTPException(
            status_code=400, 
            detail="Description must be at least 10 characters"
        )
    
    try:
        # Get the provider
        logger.info(f"Creating provider: {settings.model_provider}")
        logger.debug(f"Model name: {settings.model_name}")
        provider = create_provider()
        logger.info(f"✓ Provider created: {type(provider).__name__}")
        
        # Format the prompt
        logger.debug("Formatting enrichment prompt...")
        user_message = PROMPT_ENRICHMENT_USER.format(
            description=request.description
        )
        logger.debug(f"User message length: {len(user_message)}")
        
        # Call the LLM
        messages = [
            {"role": "system", "content": PROMPT_ENRICHMENT_SYSTEM},
            {"role": "user", "content": user_message}
        ]
        
        logger.debug("Converting messages to LangChain format...")
        # Convert to LangChain messages
        lc_messages = provider._convert_messages(messages)
        logger.debug(f"Converted {len(lc_messages)} messages")
        
        logger.info("Calling LLM provider for enrichment...")
        response = await provider.chat(
            messages=lc_messages,
            max_tokens=request.max_tokens,
            temperature=0.8,  # Higher temperature for more creative enrichment
            stream=False
        )
        logger.info("✓ LLM response received")
        
        enriched_text = response.content.strip()
        logger.info(f"Enriched text length: {len(enriched_text)} characters")
        logger.debug(f"Enriched text preview: {enriched_text[:200]}...")
        
        if not enriched_text:
            logger.error("✗ LLM returned empty response")
            raise HTTPException(
                status_code=500,
                detail="LLM returned empty response"
            )
        
        logger.info("✓ Successfully enriched prompt")
        return PromptEnrichResponse(
            original=request.description,
            enriched=enriched_text
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Prompt enrichment failed")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enrich prompt: {type(e).__name__}: {str(e)}"
        )


@router.get("/templates")
async def list_prompt_templates():
    """
    List available prompt templates
    
    Returns information about the prompts used in the system.
    Useful for debugging and understanding what prompts are being used.
    """
    logger.debug("Listing prompt templates")
    
    from backend.prompts import (
        PROMPT_ENRICHMENT_SYSTEM,
        SCENARIO_GENERATION_SYSTEM,
        NARRATOR_SYSTEM
    )
    
    templates = [
        {
            "name": "prompt_enrichment",
            "description": "Enriches user scenario descriptions",
            "system_prompt_preview": PROMPT_ENRICHMENT_SYSTEM[:200] + "..."
        },
        {
            "name": "scenario_generation",
            "description": "Generates ScenarioSpec from enriched prompt",
            "system_prompt_preview": SCENARIO_GENERATION_SYSTEM[:200] + "..."
        },
        {
            "name": "narrator",
            "description": "Generates narrative outcomes during gameplay",
            "system_prompt_preview": NARRATOR_SYSTEM[:200] + "..."
        }
    ]
    
    logger.debug(f"Returning {len(templates)} templates")
    return {"templates": templates}

