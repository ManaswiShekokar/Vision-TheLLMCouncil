"""
Pydantic models for LLM Council application.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class RoleType(str, Enum):
    """Available roles in the council."""
    RESEARCHER = "researcher"
    CRITIC = "critic"
    CREATIVE_THINKER = "creative_thinker"
    PRACTICAL_ADVISOR = "practical_advisor"
    VERIFIER = "verifier"
    CHAIRMAN = "chairman"


class DeliberationStage(str, Enum):
    """Stages in the deliberation process."""
    INITIAL_RESPONSE = "initial_response"
    PEER_REVIEW = "peer_review"
    IMPROVEMENT = "improvement"
    VERIFICATION = "verification"
    SYNTHESIS = "synthesis"
    COMPLETED = "completed"


# Request Models

class QueryRequest(BaseModel):
    """Request model for submitting a query."""
    query: str = Field(..., min_length=1, description="The user's question or query")
    custom_models: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Optional custom model assignments for roles"
    )
    enable_peer_review: bool = Field(default=True, description="Enable peer review stage")
    enable_verification: bool = Field(default=False, description="Enable verifier validation")
    deliberation_rounds: int = Field(default=0, ge=0, le=3, description="Number of improvement rounds")


class PeerReviewRequest(BaseModel):
    """Request for peer review submission."""
    session_id: str
    reviewer_role: str
    target_role: str
    scores: Dict[str, float]
    feedback: str


# Response Models

class RoleResponse(BaseModel):
    """Response from a single role."""
    role: str
    role_name: str
    model_used: str
    response: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reasoning_trace: Optional[str] = None
    token_count: Optional[int] = None


class PeerReviewScore(BaseModel):
    """Score given by one role to another."""
    reviewer_role: str
    target_role: str
    accuracy_score: float = Field(ge=0, le=10)
    clarity_score: float = Field(ge=0, le=10)
    completeness_score: float = Field(ge=0, le=10)
    reasoning_score: float = Field(ge=0, le=10)
    feedback: str
    weighted_score: Optional[float] = None


class ImprovedResponse(BaseModel):
    """Improved response after deliberation round."""
    role: str
    role_name: str
    original_response: str
    improved_response: str
    changes_made: List[str]
    round_number: int


class VerificationReport(BaseModel):
    """Report from the Verifier."""
    verified: bool
    hallucination_flags: List[str]
    factual_errors: List[str]
    logical_inconsistencies: List[str]
    confidence_assessment: str
    overall_reliability_score: float = Field(ge=0, le=100)
    recommendations: List[str]


class ChairmanSynthesis(BaseModel):
    """Final synthesis from the Chairman."""
    final_answer: str
    consensus_score: float = Field(ge=0, le=100)
    confidence_level: str  # Low, Medium, High
    key_points: List[str]
    areas_of_agreement: List[str]
    areas_of_disagreement: List[str]
    synthesis_methodology: str


class CouncilSession(BaseModel):
    """Complete session data for a council deliberation."""
    session_id: str
    query: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    current_stage: DeliberationStage = DeliberationStage.INITIAL_RESPONSE
    
    # Stage 1: Initial responses
    initial_responses: Dict[str, RoleResponse] = Field(default_factory=dict)
    
    # Stage 2: Peer reviews
    peer_reviews: List[PeerReviewScore] = Field(default_factory=list)
    
    # Stage 3: Improved responses
    improved_responses: Dict[str, ImprovedResponse] = Field(default_factory=dict)
    
    # Stage 4: Weighted scores
    weighted_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Stage 5: Verification
    verification_report: Optional[VerificationReport] = None
    
    # Stage 6: Final synthesis
    chairman_synthesis: Optional[ChairmanSynthesis] = None
    
    # Metadata
    total_tokens_used: int = 0
    processing_time_seconds: float = 0.0
    model_config_used: Dict[str, str] = Field(default_factory=dict)


# API Response Models

class SessionCreatedResponse(BaseModel):
    """Response when a new session is created."""
    session_id: str
    message: str
    query: str


class StageCompletedResponse(BaseModel):
    """Response when a deliberation stage completes."""
    session_id: str
    stage: str
    message: str
    data: Any


class FullCouncilResponse(BaseModel):
    """Complete council response with all stages."""
    session: CouncilSession
    reasoning_trace: List[Dict[str, Any]]
    summary: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    session_id: Optional[str] = None
