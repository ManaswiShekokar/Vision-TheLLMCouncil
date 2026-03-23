"""
Council Orchestrator - coordinates the multi-stage deliberation process.
"""

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..config import settings, ROLE_DEFINITIONS
from ..models import (
    CouncilSession,
    RoleResponse,
    PeerReviewScore,
    ImprovedResponse,
    VerificationReport,
    ChairmanSynthesis,
    DeliberationStage
)
from .llm_service import OpenRouterService, openrouter_service
from .scoring_service import ScoringService, scoring_service

logger = logging.getLogger(__name__)


class CouncilOrchestrator:
    """
    Orchestrates the complete council deliberation process.
    
    Stages:
    1. Initial role-based responses
    2. Anonymous peer review
    3. Multi-round improvement
    4. Weighted consensus scoring
    5. Verifier validation
    6. Chairman synthesis
    """
    
    # Roles that generate initial responses
    DELIBERATING_ROLES = ["researcher", "critic", "creative_thinker", "practical_advisor"]
    
    def __init__(
        self,
        llm_service: Optional[OpenRouterService] = None,
        scoring_service_instance: Optional[ScoringService] = None
    ):
        self.llm_service = llm_service or openrouter_service
        self.scoring = scoring_service_instance or scoring_service
        self.sessions: Dict[str, CouncilSession] = {}
    
    def create_session(
        self,
        query: str,
        model_config: Optional[Dict[str, str]] = None
    ) -> CouncilSession:
        """
        Create a new council session.
        
        Args:
            query: The user's question
            model_config: Optional custom model assignments
            
        Returns:
            New CouncilSession
        """
        session_id = str(uuid.uuid4())
        session = CouncilSession(
            session_id=session_id,
            query=query,
            model_config_used=model_config or settings.default_models
        )
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[CouncilSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    async def run_full_deliberation(
        self,
        query: str,
        model_config: Optional[Dict[str, str]] = None,
        enable_peer_review: bool = True,
        enable_verification: bool = True,
        deliberation_rounds: int = 1
    ) -> CouncilSession:
        """
        Run the complete council deliberation process.
        
        Args:
            query: The user's question
            model_config: Optional custom model assignments
            enable_peer_review: Whether to run peer review stage
            enable_verification: Whether to run verification stage
            deliberation_rounds: Number of improvement rounds
            
        Returns:
            Completed CouncilSession with all stages
        """
        start_time = datetime.utcnow()
        
        # Create session
        session = self.create_session(query, model_config)
        logger.info(f"Starting deliberation for session {session.session_id}")
        
        try:
            # Stage 1: Initial responses
            session = await self.run_initial_responses(session, model_config)
            
            # Stage 2: Peer review (optional)
            if enable_peer_review:
                session = await self.run_peer_review(session, model_config)
            
            # Stage 3: Improvement rounds
            for round_num in range(1, deliberation_rounds + 1):
                session = await self.run_improvement_round(
                    session, round_num, model_config
                )
            
            # Stage 4: Calculate weighted scores
            session = self.calculate_weighted_scores(session)
            
            # Stage 5: Verification (optional)
            if enable_verification:
                session = await self.run_verification(session, model_config)
            
            # Stage 6: Chairman synthesis
            session = await self.run_synthesis(session, model_config)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            session.processing_time_seconds = (end_time - start_time).total_seconds()
            session.current_stage = DeliberationStage.COMPLETED
            
            # Store updated session
            self.sessions[session.session_id] = session
            
            logger.info(
                f"Completed deliberation for session {session.session_id} "
                f"in {session.processing_time_seconds:.2f}s"
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Error in deliberation: {e}")
            raise
    
    async def run_initial_responses(
        self,
        session: CouncilSession,
        model_config: Optional[Dict[str, str]] = None
    ) -> CouncilSession:
        """
        Stage 1: Generate initial role-based responses.
        
        Each role receives the query and generates a response
        based on their specific perspective.
        """
        logger.info(f"Stage 1: Generating initial responses for {session.session_id}")
        session.current_stage = DeliberationStage.INITIAL_RESPONSE
        
        results = await self.llm_service.generate_parallel_responses(
            query=session.query,
            roles=self.DELIBERATING_ROLES,
            model_config=model_config
        )
        
        for role, result in results.items():
            role_config = ROLE_DEFINITIONS.get(role, {})
            response = RoleResponse(
                role=role,
                role_name=role_config.get("name", role),
                model_used=result.get("model", "unknown"),
                response=result.get("content", ""),
                token_count=result.get("usage", {}).get("total_tokens", 0)
            )
            session.initial_responses[role] = response
            session.total_tokens_used += response.token_count or 0
        
        self.sessions[session.session_id] = session
        return session
    
    async def run_peer_review(
        self,
        session: CouncilSession,
        model_config: Optional[Dict[str, str]] = None
    ) -> CouncilSession:
        """
        Stage 2: Anonymous peer review.
        
        Each role reviews responses from other roles
        without knowing which model generated them.
        """
        logger.info(f"Stage 2: Running peer review for {session.session_id}")
        session.current_stage = DeliberationStage.PEER_REVIEW
        
        # Each role reviews ONE other role (round-robin) to minimize API calls
        # researcher->critic, critic->creative_thinker, creative_thinker->practical_advisor, practical_advisor->researcher
        review_pairs = list(zip(
            self.DELIBERATING_ROLES,
            self.DELIBERATING_ROLES[1:] + [self.DELIBERATING_ROLES[0]]
        ))
        
        # Run reviews SEQUENTIALLY to avoid rate limits
        for reviewer_role, target_role in review_pairs:
            reviewer_response = session.initial_responses.get(reviewer_role)
            target_response = session.initial_responses.get(target_role)
            if not reviewer_response or not target_response:
                continue

            # Skip review calls for roles that already failed in stage 1.
            if reviewer_response.response.startswith("Error:"):
                continue
            if target_response.response.startswith("Error:"):
                continue
            
            try:
                logger.info(f"Peer review: {reviewer_role} reviewing {target_role}")
                result = await self.llm_service.generate_peer_review(
                    reviewer_role=reviewer_role,
                    target_role=target_role,
                    target_response=target_response.response,
                    original_query=session.query,
                    model=model_config.get(reviewer_role) if model_config else None
                )
                
                parsed = result.get("parsed_scores", {})
                review = PeerReviewScore(
                    reviewer_role=reviewer_role,
                    target_role=target_role,
                    accuracy_score=parsed.get("accuracy", 5.0),
                    clarity_score=parsed.get("clarity", 5.0),
                    completeness_score=parsed.get("completeness", 5.0),
                    reasoning_score=parsed.get("reasoning", 5.0),
                    feedback=parsed.get("feedback", "")
                )
                
                # Calculate weighted score
                review.weighted_score = self.scoring.calculate_review_score(
                    review.accuracy_score,
                    review.clarity_score,
                    review.completeness_score,
                    review.reasoning_score
                )
                
                session.peer_reviews.append(review)
                session.total_tokens_used += result.get("usage", {}).get("total_tokens", 0)
            except Exception as e:
                logger.error(f"Peer review error ({reviewer_role}->{target_role}): {e}")
        
        self.sessions[session.session_id] = session
        return session
    
    async def run_improvement_round(
        self,
        session: CouncilSession,
        round_number: int,
        model_config: Optional[Dict[str, str]] = None
    ) -> CouncilSession:
        """
        Stage 3: Multi-round improvement.
        
        Each role improves their response based on:
        - Feedback from peer reviews
        - Insights from other roles' responses
        """
        logger.info(
            f"Stage 3: Running improvement round {round_number} "
            f"for {session.session_id}"
        )
        session.current_stage = DeliberationStage.IMPROVEMENT
        
        # Prepare feedback for each role
        other_responses = {
            role: resp.response
            for role, resp in session.initial_responses.items()
        }
        
        # Run improvements SEQUENTIALLY to avoid rate limits on free tier
        for role in self.DELIBERATING_ROLES:
            original = session.initial_responses.get(role)
            if not original:
                continue

            # Skip improvement if this role failed in stage 1.
            if original.response.startswith("Error:"):
                continue
            
            # Get feedback for this role
            role_feedback = [
                {
                    "reviewer": r.reviewer_role,
                    "feedback": r.feedback,
                    "score": r.weighted_score
                }
                for r in session.peer_reviews
                if r.target_role == role
            ]
            
            try:
                result = await self.llm_service.generate_improvement(
                    original_response=original.response,
                    role=role,
                    peer_feedback=role_feedback,
                    other_responses=other_responses,
                    original_query=session.query,
                    model=model_config.get(role) if model_config else None
                )
                
                improved = ImprovedResponse(
                    role=role,
                    role_name=ROLE_DEFINITIONS.get(role, {}).get("name", role),
                    original_response=original.response,
                    improved_response=result.get("content", ""),
                    changes_made=[],  # Could parse from response
                    round_number=round_number
                )
                session.improved_responses[role] = improved
                session.total_tokens_used += result.get("usage", {}).get("total_tokens", 0)
            except Exception as e:
                logger.error(f"Improvement error for {role}: {e}")
        
        self.sessions[session.session_id] = session
        return session
    
    def calculate_weighted_scores(
        self,
        session: CouncilSession
    ) -> CouncilSession:
        """
        Stage 4: Calculate weighted consensus scores.
        
        Aggregates peer review scores into final weighted scores
        for each role.
        """
        logger.info(f"Stage 4: Calculating weighted scores for {session.session_id}")
        
        # Convert peer reviews to scoring format
        review_data = [
            {
                "reviewer_role": r.reviewer_role,
                "target_role": r.target_role,
                "accuracy": r.accuracy_score,
                "clarity": r.clarity_score,
                "completeness": r.completeness_score,
                "reasoning": r.reasoning_score,
                "feedback": r.feedback
            }
            for r in session.peer_reviews
        ]
        
        # Calculate weighted scores
        session.weighted_scores = self.scoring.calculate_all_weighted_scores(
            review_data,
            self.DELIBERATING_ROLES
        )
        
        self.sessions[session.session_id] = session
        return session
    
    async def run_verification(
        self,
        session: CouncilSession,
        model_config: Optional[Dict[str, str]] = None
    ) -> CouncilSession:
        """
        Stage 5: Verifier validation.
        
        The Verifier LLM analyzes all responses for:
        - Hallucinations
        - Factual errors
        - Logical contradictions
        """
        logger.info(f"Stage 5: Running verification for {session.session_id}")
        session.current_stage = DeliberationStage.VERIFICATION
        
        # Use improved responses if available, otherwise initial
        responses = {}
        for role in self.DELIBERATING_ROLES:
            if role in session.improved_responses:
                improved = session.improved_responses[role].improved_response
                if not improved.startswith("Error:"):
                    responses[role] = improved
            elif role in session.initial_responses:
                initial = session.initial_responses[role].response
                if not initial.startswith("Error:"):
                    responses[role] = initial

        # If everything failed, keep a minimal placeholder to avoid empty prompt failures.
        if not responses:
            responses["researcher"] = "No valid role responses were generated due to upstream rate limits."
        
        result = await self.llm_service.generate_verification(
            responses=responses,
            original_query=session.query,
            model=model_config.get("verifier") if model_config else None
        )
        
        ver = result.get("verification", {})
        session.verification_report = VerificationReport(
            verified=len(ver.get("factual_errors", [])) == 0,
            hallucination_flags=ver.get("hallucination_flags", []),
            factual_errors=ver.get("factual_errors", []),
            logical_inconsistencies=ver.get("logical_inconsistencies", []),
            confidence_assessment=ver.get("confidence_assessment", "Medium"),
            overall_reliability_score=ver.get("reliability_score", 70.0),
            recommendations=ver.get("recommendations", [])
        )
        
        session.total_tokens_used += result.get("usage", {}).get("total_tokens", 0)
        self.sessions[session.session_id] = session
        return session
    
    async def run_synthesis(
        self,
        session: CouncilSession,
        model_config: Optional[Dict[str, str]] = None
    ) -> CouncilSession:
        """
        Stage 6: Chairman synthesis.
        
        The Chairman synthesizes all responses, scores, and
        verification feedback into a final comprehensive answer.
        """
        logger.info(f"Stage 6: Running chairman synthesis for {session.session_id}")
        session.current_stage = DeliberationStage.SYNTHESIS
        
        # Use improved responses if available
        responses = {}
        for role in self.DELIBERATING_ROLES:
            if role in session.improved_responses:
                improved = session.improved_responses[role].improved_response
                if not improved.startswith("Error:"):
                    responses[role] = improved
            elif role in session.initial_responses:
                initial = session.initial_responses[role].response
                if not initial.startswith("Error:"):
                    responses[role] = initial

        if not responses:
            responses["researcher"] = "No valid role responses were generated due to upstream rate limits."
        
        # Convert peer reviews and verification for synthesis
        peer_review_data = [
            {
                "reviewer": r.reviewer_role,
                "target": r.target_role,
                "score": r.weighted_score,
                "feedback": r.feedback
            }
            for r in session.peer_reviews
        ]
        
        verification_data = {}
        if session.verification_report:
            verification_data = {
                "verification": {
                    "reliability_score": session.verification_report.overall_reliability_score,
                    "confidence_assessment": session.verification_report.confidence_assessment,
                    "hallucination_flags": session.verification_report.hallucination_flags,
                    "factual_errors": session.verification_report.factual_errors
                }
            }
        
        result = await self.llm_service.generate_synthesis(
            responses=responses,
            peer_reviews=peer_review_data,
            weighted_scores=session.weighted_scores,
            verification_report=verification_data,
            original_query=session.query,
            model=model_config.get("chairman") if model_config else None
        )
        
        syn = result.get("synthesis", {})
        
        # Calculate consensus score
        consensus = self.scoring.calculate_consensus_score(
            peer_review_data,
            session.weighted_scores
        )
        
        session.chairman_synthesis = ChairmanSynthesis(
            final_answer=syn.get("final_answer", result.get("content", "")),
            consensus_score=syn.get("consensus_score", consensus),
            confidence_level=syn.get("confidence_level", 
                self.scoring.get_confidence_level(consensus)),
            key_points=syn.get("key_points", []),
            areas_of_agreement=syn.get("areas_of_agreement", []),
            areas_of_disagreement=syn.get("areas_of_disagreement", []),
            synthesis_methodology=syn.get("synthesis_methodology", "")
        )
        
        session.total_tokens_used += result.get("usage", {}).get("total_tokens", 0)
        self.sessions[session.session_id] = session
        return session
    
    def get_reasoning_trace(self, session: CouncilSession) -> List[Dict[str, Any]]:
        """
        Generate a reasoning trace showing how the final answer was formed.
        
        Args:
            session: The completed session
            
        Returns:
            List of reasoning steps with timestamps and data
        """
        trace = []
        
        # User query
        trace.append({
            "step": 1,
            "stage": "Query Received",
            "timestamp": session.created_at.isoformat(),
            "data": {"query": session.query}
        })
        
        # Initial responses
        if session.initial_responses:
            trace.append({
                "step": 2,
                "stage": "Initial Responses",
                "data": {
                    role: {
                        "role_name": resp.role_name,
                        "model": resp.model_used,
                        "response_preview": resp.response[:200] + "..."
                    }
                    for role, resp in session.initial_responses.items()
                }
            })
        
        # Peer reviews
        if session.peer_reviews:
            review_summary = {}
            for review in session.peer_reviews:
                if review.target_role not in review_summary:
                    review_summary[review.target_role] = []
                review_summary[review.target_role].append({
                    "from": review.reviewer_role,
                    "score": review.weighted_score
                })
            
            trace.append({
                "step": 3,
                "stage": "Peer Reviews",
                "data": review_summary
            })
        
        # Improved responses
        if session.improved_responses:
            trace.append({
                "step": 4,
                "stage": "Improved Responses",
                "data": {
                    role: {
                        "improvements_made": True,
                        "preview": resp.improved_response[:200] + "..."
                    }
                    for role, resp in session.improved_responses.items()
                }
            })
        
        # Weighted scores
        if session.weighted_scores:
            trace.append({
                "step": 5,
                "stage": "Weighted Scoring",
                "data": {
                    "scores": session.weighted_scores,
                    "rankings": self.scoring.rank_responses(session.weighted_scores)
                }
            })
        
        # Verification
        if session.verification_report:
            trace.append({
                "step": 6,
                "stage": "Verification",
                "data": {
                    "reliability_score": session.verification_report.overall_reliability_score,
                    "issues_found": (
                        len(session.verification_report.hallucination_flags) +
                        len(session.verification_report.factual_errors) +
                        len(session.verification_report.logical_inconsistencies)
                    ),
                    "confidence": session.verification_report.confidence_assessment
                }
            })
        
        # Final synthesis
        if session.chairman_synthesis:
            trace.append({
                "step": 7,
                "stage": "Chairman Synthesis",
                "data": {
                    "consensus_score": session.chairman_synthesis.consensus_score,
                    "confidence_level": session.chairman_synthesis.confidence_level,
                    "key_points_count": len(session.chairman_synthesis.key_points)
                }
            })
        
        return trace
    
    def generate_summary(self, session: CouncilSession) -> str:
        """
        Generate a human-readable summary of the deliberation.
        
        Args:
            session: The completed session
            
        Returns:
            Summary string
        """
        lines = [
            f"# Council Deliberation Summary",
            f"",
            f"**Session ID:** {session.session_id}",
            f"**Query:** {session.query}",
            f"**Processing Time:** {session.processing_time_seconds:.2f} seconds",
            f"**Total Tokens Used:** {session.total_tokens_used}",
            f"",
        ]
        
        if session.chairman_synthesis:
            lines.extend([
                f"## Final Answer",
                f"",
                session.chairman_synthesis.final_answer,
                f"",
                f"## Consensus Metrics",
                f"- **Consensus Score:** {session.chairman_synthesis.consensus_score}%",
                f"- **Confidence Level:** {session.chairman_synthesis.confidence_level}",
                f"",
            ])
        
        if session.weighted_scores:
            lines.append("## Response Rankings")
            rankings = self.scoring.rank_responses(session.weighted_scores)
            for r in rankings:
                role_name = ROLE_DEFINITIONS.get(r["role"], {}).get("name", r["role"])
                lines.append(f"{r['rank']}. {role_name}: {r['score']:.2f}")
            lines.append("")
        
        if session.verification_report:
            lines.extend([
                f"## Verification",
                f"- **Reliability Score:** {session.verification_report.overall_reliability_score}%",
                f"- **Issues Found:** {len(session.verification_report.hallucination_flags) + len(session.verification_report.factual_errors)}",
                f"",
            ])
        
        return "\n".join(lines)


# Global orchestrator instance
council_orchestrator = CouncilOrchestrator()
