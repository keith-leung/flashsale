"""Campaign admin endpoints for manual campaign management."""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.flash_sale_campaign import FlashSaleCampaign, FlashSaleStatus
from app.services.campaign_writeback import writeback_campaign
from app.schemas.response import ResponseDTO

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/campaigns/{campaign_id}/end", response_model=ResponseDTO)
async def end_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually end a flash sale campaign and trigger write-back.

    Use cases:
    - Benchmark completed before time/inventory runs out
    - Admin decision to end campaign early
    - Emergency campaign termination

    This endpoint:
    1. Updates campaign status to 'ended'
    2. Triggers async write-back from Redis to MariaDB
    3. Returns immediately (write-back happens in background)
    """
    logger.info(f"Manual campaign end requested for {campaign_id}")

    # Get campaign
    result = await db.execute(
        select(FlashSaleCampaign).filter(FlashSaleCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    if campaign.status == FlashSaleStatus.ENDED.value:
        logger.info(f"Campaign {campaign_id} already ended")
        return ResponseDTO(
            status=200,
            message=f"Campaign {campaign.name} is already ended",
            data={
                "campaign_id": campaign_id,
                "status": campaign.status,
                "action": "none"
            }
        )

    # Update campaign status
    campaign.status = FlashSaleStatus.ENDED.value
    await db.commit()

    # Trigger write-back in background
    background_tasks.add_task(writeback_campaign, campaign_id, db, "manual")

    logger.info(f"Campaign {campaign_id} marked as ended, write-back queued")

    return ResponseDTO(
        status=200,
        message=f"Campaign {campaign.name} ended successfully, write-back in progress",
        data={
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "previous_status": campaign.status,
            "new_status": FlashSaleStatus.ENDED.value,
            "action": "write_back_queued"
        }
    )


@router.get("/campaigns/{campaign_id}/writeback-status", response_model=ResponseDTO)
async def get_writeback_status(
    campaign_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check write-back status for a campaign.

    Returns:
    - Campaign status
    - sold_quantity (updated after write-back)
    - Whether write-back appears complete
    """
    result = await db.execute(
        select(FlashSaleCampaign).filter(FlashSaleCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    # Check if write-back completed by checking sold_quantity
    writeback_complete = campaign.sold_quantity > 0 or campaign.status == FlashSaleStatus.ENDED.value

    return ResponseDTO(
        status=200,
        message="Write-back status retrieved",
        data={
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "status": campaign.status,
            "sold_quantity": campaign.sold_quantity,
            "total_sale_limit": campaign.total_sale_limit,
            "remaining_quantity": campaign.remaining_quantity,
            "writeback_complete": writeback_complete
        }
    )


@router.post("/campaigns/{campaign_id}/writeback", response_model=ResponseDTO)
async def trigger_writeback(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger write-back without changing campaign status.

    Use case:
    - Campaign already ended but write-back failed
    - Retry after fixing Redis/DB issues
    - Testing write-back process
    """
    logger.info(f"Manual write-back triggered for campaign {campaign_id}")

    # Verify campaign exists
    result = await db.execute(
        select(FlashSaleCampaign).filter(FlashSaleCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    # Trigger write-back in background
    background_tasks.add_task(writeback_campaign, campaign_id, db, "manual_retry")

    return ResponseDTO(
        status=200,
        message=f"Write-back triggered for campaign {campaign.name}",
        data={
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "action": "write_back_queued"
        }
    )
