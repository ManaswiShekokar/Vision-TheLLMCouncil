"""
API Routes for LLM Council application.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
import logging

from ..models import (
    QueryRequest,
    SessionCreatedResponse,
    StageCompletedResponse,
    FullCouncilResponse,
    ErrorResponse,
    CouncilSession
)
from ..services.orchestrator import council_orchestrator
from ..config import settings, ROLE_DEFINITIONS, AVAILABLE_MODELS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["council"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@router.get("/config")
async def get_config():
    """Get current configuration."""
    return {
        "roles": list(ROLE_DEFINITIONS.keys()),
        "available_models": AVAILABLE_MODELS,
        "default_models": settings.default_models,
        "scoring_weights": settings.scoring_weights,
        "max_deliberation_rounds": settings.max_deliberation_rounds
    }


@router.get("/roles")
async def get_roles():
    """Get available council roles and their descriptions."""
    return {
        role: {
            "name": config["name"],
            "description": config["description"]
        }
        for role, config in ROLE_DEFINITIONS.items()
    }


@router.get("/models")
async def get_available_models():
    """Get list of available LLM models."""
    return {"models": AVAILABLE_MODELS}


@router.post("/deliberate", response_model=Dict[str, Any])
async def run_full_deliberation(request: QueryRequest):
    """
    Run a complete council deliberation.
    
    This endpoint executes all stages:
    1. Initial role-based responses
    2. Peer review
    3. Improvement rounds
    4. Weighted scoring
    5. Verification
    6. Chairman synthesis
    
    Returns the complete session with all data.
    """
    try:
        logger.info(f"Starting deliberation for query: {request.query[:100]}...")
        
        session = await council_orchestrator.run_full_deliberation(
            query=request.query,
            model_config=request.custom_models,
            enable_peer_review=request.enable_peer_review,
            enable_verification=request.enable_verification,
            deliberation_rounds=request.deliberation_rounds
        )
        
        # Generate reasoning trace
        reasoning_trace = council_orchestrator.get_reasoning_trace(session)
        
        # Convert session to dict
        session_dict = session.model_dump()
        
        # Convert datetime objects to ISO format strings
        if session_dict.get("created_at"):
            session_dict["created_at"] = session.created_at.isoformat()
        
        for role, resp in session_dict.get("initial_responses", {}).items():
            if resp.get("timestamp"):
                resp["timestamp"] = session.initial_responses[role].timestamp.isoformat()
        
        return {
            "success": True,
            "session": session_dict,
            "reasoning_trace": reasoning_trace,
            "summary": council_orchestrator.generate_summary(session)
        }
        
    except Exception as e:
        logger.error(f"Deliberation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliberate/start")
async def start_deliberation(request: QueryRequest):
    """
    Start a new deliberation session.
    Returns session ID immediately - use other endpoints to run stages.
    """
    try:
        session = council_orchestrator.create_session(
            query=request.query,
            model_config=request.custom_models
        )
        
        return SessionCreatedResponse(
            session_id=session.session_id,
            message="Session created successfully",
            query=request.query
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliberate/{session_id}/initial-responses")
async def run_initial_responses(
    session_id: str,
    model_config: Optional[Dict[str, str]] = None
):
    """Run Stage 1: Generate initial role-based responses."""
    session = council_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session = await council_orchestrator.run_initial_responses(
            session, model_config
        )
        
        return StageCompletedResponse(
            session_id=session_id,
            stage="initial_responses",
            message="Initial responses generated",
            data={
                role: {
                    "role_name": resp.role_name,
                    "model": resp.model_used,
                    "response": resp.response
                }
                for role, resp in session.initial_responses.items()
            }
        )
    except Exception as e:
        logger.error(f"Error in initial responses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliberate/{session_id}/peer-review")
async def run_peer_review(
    session_id: str,
    model_config: Optional[Dict[str, str]] = None
):
    """Run Stage 2: Anonymous peer review."""
    session = council_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session = await council_orchestrator.run_peer_review(
            session, model_config
        )
        
        return StageCompletedResponse(
            session_id=session_id,
            stage="peer_review",
            message="Peer review completed",
            data={
                "reviews": [
                    {
                        "reviewer": r.reviewer_role,
                        "target": r.target_role,
                        "accuracy": r.accuracy_score,
                        "clarity": r.clarity_score,
                        "completeness": r.completeness_score,
                        "reasoning": r.reasoning_score,
                        "weighted_score": r.weighted_score,
                        "feedback": r.feedback
                    }
                    for r in session.peer_reviews
                ]
            }
        )
    except Exception as e:
        logger.error(f"Error in peer review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliberate/{session_id}/improve")
async def run_improvement(
    session_id: str,
    round_number: int = 1,
    model_config: Optional[Dict[str, str]] = None
):
    """Run Stage 3: Improvement round."""
    session = council_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session = await council_orchestrator.run_improvement_round(
            session, round_number, model_config
        )
        
        return StageCompletedResponse(
            session_id=session_id,
            stage="improvement",
            message=f"Improvement round {round_number} completed",
            data={
                role: {
                    "original_preview": resp.original_response[:200] + "...",
                    "improved_preview": resp.improved_response[:200] + "...",
                    "full_improved": resp.improved_response
                }
                for role, resp in session.improved_responses.items()
            }
        )
    except Exception as e:
        logger.error(f"Error in improvement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliberate/{session_id}/verify")
async def run_verification(
    session_id: str,
    model_config: Optional[Dict[str, str]] = None
):
    """Run Stage 5: Verifier validation."""
    session = council_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Calculate weighted scores first
        session = council_orchestrator.calculate_weighted_scores(session)
        
        session = await council_orchestrator.run_verification(
            session, model_config
        )
        
        ver = session.verification_report
        return StageCompletedResponse(
            session_id=session_id,
            stage="verification",
            message="Verification completed",
            data={
                "verified": ver.verified,
                "reliability_score": ver.overall_reliability_score,
                "confidence": ver.confidence_assessment,
                "hallucination_flags": ver.hallucination_flags,
                "factual_errors": ver.factual_errors,
                "logical_inconsistencies": ver.logical_inconsistencies,
                "recommendations": ver.recommendations
            }
        )
    except Exception as e:
        logger.error(f"Error in verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliberate/{session_id}/synthesize")
async def run_synthesis(
    session_id: str,
    model_config: Optional[Dict[str, str]] = None
):
    """Run Stage 6: Chairman synthesis."""
    session = council_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session = await council_orchestrator.run_synthesis(
            session, model_config
        )
        
        syn = session.chairman_synthesis
        return StageCompletedResponse(
            session_id=session_id,
            stage="synthesis",
            message="Synthesis completed",
            data={
                "final_answer": syn.final_answer,
                "consensus_score": syn.consensus_score,
                "confidence_level": syn.confidence_level,
                "key_points": syn.key_points,
                "areas_of_agreement": syn.areas_of_agreement,
                "areas_of_disagreement": syn.areas_of_disagreement,
                "methodology": syn.synthesis_methodology
            }
        )
    except Exception as e:
        logger.error(f"Error in synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get full session data."""
    session = council_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_dict = session.model_dump()
    
    # Convert datetime objects
    if session_dict.get("created_at"):
        session_dict["created_at"] = session.created_at.isoformat()
    
    for role, resp in session_dict.get("initial_responses", {}).items():
        if resp.get("timestamp"):
            resp["timestamp"] = session.initial_responses[role].timestamp.isoformat()
    
    return {
        "session": session_dict,
        "reasoning_trace": council_orchestrator.get_reasoning_trace(session),
        "summary": council_orchestrator.generate_summary(session)
    }


@router.get("/session/{session_id}/trace")
async def get_reasoning_trace(session_id: str):
    """Get the reasoning trace for a session."""
    session = council_orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "trace": council_orchestrator.get_reasoning_trace(session)
    }


@router.get("/sessions")
async def list_sessions():
    """List all sessions."""
    sessions = []
    for session_id, session in council_orchestrator.sessions.items():
        sessions.append({
            "session_id": session_id,
            "query": session.query[:100] + "..." if len(session.query) > 100 else session.query,
            "stage": session.current_stage.value,
            "created_at": session.created_at.isoformat()
        })
    
    return {"sessions": sessions}
