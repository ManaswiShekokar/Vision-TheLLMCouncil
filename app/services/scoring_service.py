"""
Scoring service for weighted consensus scoring.
Implements the weighted scoring mechanism for council responses.
"""

from typing import Dict, List, Any
from ..config import settings


class ScoringService:
    """Service for calculating weighted consensus scores."""
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize scoring service.
        
        Args:
            weights: Custom weights for scoring criteria
        """
        self.weights = weights or settings.scoring_weights
    
    def calculate_review_score(
        self,
        accuracy: float,
        clarity: float,
        completeness: float,
        reasoning: float
    ) -> float:
        """
        Calculate weighted score from individual criteria.
        
        Formula: final_score = Σ(criterion_score × criterion_weight)
        
        Args:
            accuracy: Accuracy score (0-10)
            clarity: Clarity score (0-10)
            completeness: Completeness score (0-10)
            reasoning: Reasoning quality score (0-10)
            
        Returns:
            Weighted score (0-10)
        """
        score = (
            accuracy * self.weights.get("accuracy", 0.25) +
            clarity * self.weights.get("clarity", 0.25) +
            completeness * self.weights.get("completeness", 0.25) +
            reasoning * self.weights.get("reasoning", 0.25)
        )
        return round(score, 2)
    
    def aggregate_peer_reviews(
        self,
        peer_reviews: List[Dict[str, Any]],
        target_role: str
    ) -> Dict[str, Any]:
        """
        Aggregate peer review scores for a specific role.
        
        Args:
            peer_reviews: List of all peer reviews
            target_role: The role to aggregate scores for
            
        Returns:
            Dict containing aggregated scores and feedback
        """
        role_reviews = [
            r for r in peer_reviews 
            if r.get("target_role") == target_role
        ]
        
        if not role_reviews:
            return {
                "target_role": target_role,
                "review_count": 0,
                "avg_accuracy": 0,
                "avg_clarity": 0,
                "avg_completeness": 0,
                "avg_reasoning": 0,
                "weighted_score": 0,
                "feedback_summary": []
            }
        
        # Calculate averages
        n = len(role_reviews)
        avg_accuracy = sum(r.get("accuracy", 5) for r in role_reviews) / n
        avg_clarity = sum(r.get("clarity", 5) for r in role_reviews) / n
        avg_completeness = sum(r.get("completeness", 5) for r in role_reviews) / n
        avg_reasoning = sum(r.get("reasoning", 5) for r in role_reviews) / n
        
        weighted_score = self.calculate_review_score(
            avg_accuracy, avg_clarity, avg_completeness, avg_reasoning
        )
        
        feedback_summary = [
            r.get("feedback", "") for r in role_reviews 
            if r.get("feedback")
        ]
        
        return {
            "target_role": target_role,
            "review_count": n,
            "avg_accuracy": round(avg_accuracy, 2),
            "avg_clarity": round(avg_clarity, 2),
            "avg_completeness": round(avg_completeness, 2),
            "avg_reasoning": round(avg_reasoning, 2),
            "weighted_score": weighted_score,
            "feedback_summary": feedback_summary
        }
    
    def calculate_all_weighted_scores(
        self,
        peer_reviews: List[Dict[str, Any]],
        roles: List[str]
    ) -> Dict[str, float]:
        """
        Calculate weighted scores for all roles.
        
        Args:
            peer_reviews: All peer review data
            roles: List of roles to score
            
        Returns:
            Dict mapping role to weighted score
        """
        scores = {}
        for role in roles:
            aggregated = self.aggregate_peer_reviews(peer_reviews, role)
            scores[role] = aggregated["weighted_score"]
        return scores
    
    def normalize_scores(
        self,
        scores: Dict[str, float],
        target_min: float = 0,
        target_max: float = 100
    ) -> Dict[str, float]:
        """
        Normalize scores to a target range.
        
        Args:
            scores: Dict of role scores
            target_min: Target minimum value
            target_max: Target maximum value
            
        Returns:
            Dict of normalized scores
        """
        if not scores:
            return {}
        
        values = list(scores.values())
        current_min = min(values)
        current_max = max(values)
        
        if current_max == current_min:
            # All scores are equal
            mid = (target_min + target_max) / 2
            return {role: mid for role in scores}
        
        normalized = {}
        for role, score in scores.items():
            normalized_score = (
                (score - current_min) / (current_max - current_min) *
                (target_max - target_min) + target_min
            )
            normalized[role] = round(normalized_score, 2)
        
        return normalized
    
    def calculate_consensus_score(
        self,
        peer_reviews: List[Dict[str, Any]],
        weighted_scores: Dict[str, float]
    ) -> float:
        """
        Calculate overall consensus score indicating agreement level.
        
        Higher score = more agreement among council members.
        
        Args:
            peer_reviews: All peer review data
            weighted_scores: Weighted scores for each role
            
        Returns:
            Consensus score (0-100)
        """
        if not weighted_scores:
            return 50.0
        
        # Calculate variance in scores
        scores = list(weighted_scores.values())
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        
        # Lower variance = higher consensus
        # Max variance for 0-10 scale is 25 (when scores are 0 and 10)
        max_variance = 25
        normalized_variance = min(variance / max_variance, 1.0)
        
        # Convert to consensus score (0-100)
        consensus = (1 - normalized_variance) * 100
        
        # Boost based on average score level
        avg_score = mean_score / 10 * 100
        
        # Final consensus is weighted combination
        final_consensus = consensus * 0.6 + avg_score * 0.4
        
        return round(min(max(final_consensus, 0), 100), 1)
    
    def get_confidence_level(self, consensus_score: float) -> str:
        """
        Convert consensus score to confidence level label.
        
        Args:
            consensus_score: The consensus score (0-100)
            
        Returns:
            Confidence level string
        """
        if consensus_score >= 80:
            return "High"
        elif consensus_score >= 60:
            return "Medium"
        else:
            return "Low"
    
    def rank_responses(
        self,
        weighted_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Rank responses by their weighted scores.
        
        Args:
            weighted_scores: Dict mapping role to score
            
        Returns:
            Sorted list of (role, score, rank) tuples
        """
        sorted_scores = sorted(
            weighted_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"role": role, "score": score, "rank": i + 1}
            for i, (role, score) in enumerate(sorted_scores)
        ]
    
    def calculate_influence_weights(
        self,
        weighted_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate how much each response should influence the final synthesis.
        
        Higher scoring responses get more weight in the synthesis.
        
        Args:
            weighted_scores: Dict mapping role to score
            
        Returns:
            Dict mapping role to influence weight (0-1, sum = 1)
        """
        if not weighted_scores:
            return {}
        
        # Use softmax-like normalization
        total = sum(weighted_scores.values())
        if total == 0:
            # Equal weights if all scores are 0
            n = len(weighted_scores)
            return {role: 1/n for role in weighted_scores}
        
        return {
            role: round(score / total, 3)
            for role, score in weighted_scores.items()
        }


# Global service instance
scoring_service = ScoringService()
