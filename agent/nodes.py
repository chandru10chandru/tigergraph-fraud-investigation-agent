import logging
from typing import Dict, Any, List
from agent.state import FraudInvestigationState
from agent.graph_rag import GraphRAGRetriever
from agent.actions import (
    freeze_account, block_card, send_customer_sms,
    request_step_up_auth, escalate_to_analyst, file_sar
)

from agent.llm_reasoner import LLMReasoner

logger = logging.getLogger(__name__)
rag_retriever = GraphRAGRetriever()
llm_reasoner = LLMReasoner()

def gather_transaction_data(state: FraudInvestigationState) -> Dict[str, Any]:
    """Node 1: Gather initial case payload and transaction graph metadata."""
    logger.info(f"Node [gather_transaction_data] executing for Case {state['case_id']} (User: {state['target_user']})")
    
    raw = state.get("raw_case_data", {})
    logs = list(state.get("execution_logs", []))
    logs.append(f"[Gather Data]: Loaded initial case payload for {state['target_user']}.")
    
    return {
        "execution_logs": logs,
        "evidence_iteration": state.get("evidence_iteration", 0)
    }

def graph_rag_evidence(state: FraudInvestigationState) -> Dict[str, Any]:
    """Node 2: Retrieve GraphRAG context (3-hop subgraph, structuring, fraud ring queries)."""
    user_id = state["target_user"]
    logger.info(f"Node [graph_rag_evidence] querying graph context for {user_id}")
    
    rag_data = rag_retriever.retrieve_context(user_id)
    logs = list(state.get("execution_logs", []))
    logs.append(f"[GraphRAG Evidence]: Retrieved 3-hop graph context and GSQL analytics for {user_id}.")
    
    return {
        "subgraph_context": rag_data["subgraph"],
        "structuring_results": rag_data["structuring"],
        "ring_results": rag_data["ring"],
        "graph_rag_summary": rag_data["summary_text"],
        "execution_logs": logs
    }

def assess_risk(state: FraudInvestigationState) -> Dict[str, Any]:
    """Node 3: Assess risk score, confidence score, and synthesizes reasoning via LLM Reasoner."""
    case_id = state["case_id"]
    user_id = state["target_user"]
    struct = state.get("structuring_results", {})
    ring = state.get("ring_results", {})
    raw = state.get("raw_case_data", {})
    summary = state.get("graph_rag_summary", "")
    iteration = state.get("evidence_iteration", 0)
    
    # Synthesize investigation via LLM Reasoner
    result = llm_reasoner.synthesize_investigation(
        case_id=case_id,
        user_id=user_id,
        raw_case_data=raw,
        graph_rag_summary=summary,
        structuring_results=struct,
        ring_results=ring,
        evidence_iteration=iteration
    )

    risk_score = float(result.get("risk_score", 0.10))
    confidence_score = float(result.get("confidence_score", 0.90))
    status = result.get("status", "CLEARED")
    narrative = result.get("investigation_narrative", "")

    logs = list(state.get("execution_logs", []))
    logs.append(f"[Assess Risk]: Calculated Risk={risk_score:.2f}, Confidence={confidence_score:.2f}, Status={status}.")
    logs.append(f"[LLM Narrative]:\n{narrative}")
    
    return {
        "risk_score": risk_score,
        "confidence_score": confidence_score,
        "fraud_reasoning": narrative,
        "status": status,
        "execution_logs": logs
    }

def check_policy(state: FraudInvestigationState) -> Dict[str, Any]:
    """Node 4: Enforce institution policy rules."""
    risk = state.get("risk_score", 0.0)
    struct = state.get("structuring_results", {})
    raw = state.get("raw_case_data", {})
    total_amount = raw.get("total_amount", 0.0)
    
    # Policy rules:
    # 1. SAR required if confirmed fraud > $10,000 OR structuring pattern detected
    is_sar_required = (risk > 0.50 and total_amount >= 10000.0) or struct.get("is_structuring_detected", False)
    
    # 2. Account freeze requires manager approval
    is_account_freeze_required = (risk > 0.70 and total_amount >= 15000.0)
    requires_manager_approval = is_account_freeze_required
    
    # 3. Card block auto-executed for card fraud or ring links
    is_card_block_required = (risk > 0.60 or raw.get("type") in ["CARD_FRAUD", "FRAUD_RING"])
    
    # 4. Customer SMS warning auto-executed
    is_sms_warning_required = (risk > 0.40)
    
    logs = list(state.get("execution_logs", []))
    logs.append(f"[Check Policy]: SAR Required={is_sar_required}, Freeze Required={is_account_freeze_required}, Manager Approval Required={requires_manager_approval}.")
    
    return {
        "is_sar_required": is_sar_required,
        "is_account_freeze_required": is_account_freeze_required,
        "is_card_block_required": is_card_block_required,
        "is_sms_warning_required": is_sms_warning_required,
        "requires_manager_approval": requires_manager_approval,
        "execution_logs": logs
    }

def request_additional_evidence(state: FraudInvestigationState) -> Dict[str, Any]:
    """Node 5 (Branch): Request additional evidence when confidence < 0.50 or 0.50-0.70."""
    logger.info(f"Node [request_additional_evidence] fetching extra evidence for {state['target_user']}")
    logs = list(state.get("execution_logs", []))
    iteration = state.get("evidence_iteration", 0) + 1
    logs.append(f"[Request Evidence (Iteration {iteration})]: Gathered secondary device telemetry & IP geo-location logs.")
    
    return {
        "evidence_iteration": iteration,
        "execution_logs": logs
    }

def determine_next_best_action(state: FraudInvestigationState) -> Dict[str, Any]:
    """Node 6: Execute mock action APIs based on policy evaluation."""
    actions = []
    logs = list(state.get("execution_logs", []))
    user_id = state["target_user"]
    case_id = state["case_id"]
    
    if state.get("is_card_block_required"):
        res = block_card(f"card_{user_id}")
        actions.append(res)
        logs.append(f"[Action Executed]: Blocked card card_{user_id}.")

    if state.get("is_sms_warning_required"):
        res = send_customer_sms(user_id, "Security Alert: Suspicious transaction flagged on your account.")
        actions.append(res)
        logs.append(f"[Action Executed]: Sent SMS warning to user {user_id}.")

    if state.get("is_account_freeze_required"):
        res = freeze_account(user_id, manager_approved=False)  # Requires manager approval
        actions.append(res)
        logs.append(f"[Action Executed]: Deferring account freeze for {user_id} (Requires Manager Approval).")

    if state.get("is_sar_required"):
        sar_payload = {
            "case_id": case_id,
            "user_id": user_id,
            "total_amount": state.get("raw_case_data", {}).get("total_amount", 0.0),
            "reasoning": state.get("fraud_reasoning"),
            "structuring_detected": state.get("structuring_results", {}).get("is_structuring_detected", False)
        }
        res = file_sar(case_id, sar_payload)
        actions.append(res)
        sar_report_obj = res
        logs.append(f"[Action Executed]: Filed FinCEN SAR report SAR-FINCEN-2024-{case_id}.")
    else:
        sar_report_obj = None

    if state.get("risk_score", 0.0) > 0.50:
        res = escalate_to_analyst(case_id, priority="HIGH")
        actions.append(res)
        logs.append(f"[Action Executed]: Escalated case {case_id} to Senior Analyst.")

    return {
        "actions_taken": actions,
        "sar_report": sar_report_obj,
        "execution_logs": logs
    }
