"""
Campaign Debug API - Helper endpoints to inspect allocator state

These endpoints are for testing/debugging the dual-layer tracking implementation.
"""

import logging
from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status/{campaign_id}")
async def get_campaign_status(campaign_id: str):
    """
    Get current status of a campaign's memory allocation

    Returns:
        - SPU counter (remaining campaign items)
        - SKU caches (remaining per-SKU items)
        - Refill flags and metrics
    """
    try:
        from app.main import get_campaign_allocator
        allocator = get_campaign_allocator()
        status = allocator.get_campaign_status(campaign_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign {campaign_id} not found in allocator"
            )

        return {
            "status": "success",
            "data": status
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Allocator not initialized: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting campaign status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get campaign status: {str(e)}"
        )


@router.get("/all")
async def get_all_campaigns():
    """
    Get status of all loaded campaigns

    Returns list of campaign statuses
    """
    try:
        from app.main import get_campaign_allocator
        allocator = get_campaign_allocator()

        # Get all campaigns from allocator
        campaigns = []
        for campaign_id in allocator._campaigns.keys():
            status = allocator.get_campaign_status(campaign_id)
            if status:
                campaigns.append(status)

        return {
            "status": "success",
            "count": len(campaigns),
            "data": campaigns
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Allocator not initialized: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting all campaigns: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get campaigns: {str(e)}"
        )


@router.post("/close/{campaign_id}")
async def close_campaign(campaign_id: str):
    """
    Manually close a campaign (for testing)

    This simulates operator/tester closing the campaign.
    Further orders will use ordinary price.
    """
    try:
        from app.main import get_campaign_allocator
        allocator = get_campaign_allocator()
        await allocator.close_campaign(campaign_id)

        return {
            "status": "success",
            "message": f"Campaign {campaign_id} closed",
            "data": allocator.get_campaign_status(campaign_id)
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Allocator not initialized: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error closing campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to close campaign: {str(e)}"
        )
