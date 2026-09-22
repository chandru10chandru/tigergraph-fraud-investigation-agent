import logging
from typing import Dict, Any, Literal, List, Callable

logger = logging.getLogger(__name__)

# Try importing langgraph
try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

from agent.state import FraudInvestigationState
from agent.nodes import (
    gather_transaction_data,
    graph_rag_evidence,
    assess_risk,
    check_policy,
    request_additional_evidence,
    determine_next_best_action
)

def should_gather_more_evidence(state: FraudInvestigationState) -> Literal["gather_more", "act"]:
    """Conditional Edge Evaluator based on confidence threshold rules:
    - confidence < 0.50: MUST gather more evidence (PENDING_EVIDENCE)
    - 0.50-0.70: SHOULD gather more evidence if possible (max 1 round)
    - 0.70-0.85: Proceed with caveats
    - > 0.85: Act with high confidence
    """
    conf = state.get("confidence_score", 0.0)
    iteration = state.get("evidence_iteration", 0)

    if conf < 0.50 and iteration == 0:
        logger.info(f"Conditional Edge: Confidence {conf:.2f} < 0.50 -> Routing to request_additional_evidence")
        return "gather_more"
    elif 0.50 <= conf <= 0.70 and iteration == 0:
        logger.info(f"Conditional Edge: Confidence {conf:.2f} (0.50-0.70 range) -> Routing to request_additional_evidence")
        return "gather_more"
    else:
        logger.info(f"Conditional Edge: Confidence {conf:.2f} sufficient or max retries reached -> Routing to determine_next_best_action")
        return "act"

class FallbackStateGraphRunner:
    """Standard StateGraph execution engine when langgraph package is loading or fallback."""
    
    def invoke(self, initial_state: FraudInvestigationState) -> FraudInvestigationState:
        state = dict(initial_state)
        
        # Step 1: gather_data
        updates = gather_transaction_data(state)
        state.update(updates)
        
        # Step 2: graph_rag
        updates = graph_rag_evidence(state)
        state.update(updates)
        
        # Step 3: assess_risk
        updates = assess_risk(state)
        state.update(updates)
        
        # Step 4: check_policy
        updates = check_policy(state)
        state.update(updates)
        
        # Conditional Edge Check
        route = should_gather_more_evidence(state)
        if route == "gather_more":
            updates = request_additional_evidence(state)
            state.update(updates)
            
            # Re-assess risk & policy after gathering evidence
            updates = assess_risk(state)
            state.update(updates)
            updates = check_policy(state)
            state.update(updates)

        # Step 5: determine_action
        updates = determine_next_best_action(state)
        state.update(updates)
        
        return state

def build_fraud_investigation_graph():
    """Builds and compiles the Fraud Investigation StateGraph workflow."""
    if HAS_LANGGRAPH:
        workflow = StateGraph(FraudInvestigationState)
        workflow.add_node("gather_data", gather_transaction_data)
        workflow.add_node("graph_rag", graph_rag_evidence)
        workflow.add_node("assess_risk", assess_risk)
        workflow.add_node("check_policy", check_policy)
        workflow.add_node("request_evidence", request_additional_evidence)
        workflow.add_node("determine_action", determine_next_best_action)

        workflow.set_entry_point("gather_data")
        workflow.add_edge("gather_data", "graph_rag")
        workflow.add_edge("graph_rag", "assess_risk")
        workflow.add_edge("assess_risk", "check_policy")
        workflow.add_conditional_edges(
            "check_policy",
            should_gather_more_evidence,
            {"gather_more": "request_evidence", "act": "determine_action"}
        )
        workflow.add_edge("request_evidence", "assess_risk")
        workflow.add_edge("determine_action", END)
        return workflow.compile()
    else:
        logger.info("Using FallbackStateGraphRunner engine for LangGraph execution.")
        return FallbackStateGraphRunner()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    graph = build_fraud_investigation_graph()
    logger.info("LangGraph Fraud Investigation workflow created successfully.")
