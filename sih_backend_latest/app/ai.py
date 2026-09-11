"""Opt-in, authenticated development endpoint; does not write to the database."""
import os
from fastapi import APIRouter, Depends, HTTPException
from .auth import get_current_user
from .ai_service import AnalysisRequest, DistressResult, AIServiceUnavailable, analyze_distress


def require_ai_test_enabled():
    if os.getenv('AI_TEST_ENDPOINT_ENABLED', '').strip().lower() != 'true':
        raise HTTPException(status_code=404, detail='Not found')


router = APIRouter(prefix='/api/ai', tags=['AI development'],
                   dependencies=[Depends(require_ai_test_enabled), Depends(get_current_user)])


@router.post('/analyze', response_model=DistressResult)
async def analyze(data: AnalysisRequest):
    try:
        return await analyze_distress(data.message)
    except AIServiceUnavailable:
        raise HTTPException(status_code=503, detail='AI analysis is temporarily unavailable.') from None
