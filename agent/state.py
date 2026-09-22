from typing import TypedDict, List, Dict, Any, Optional

class FraudInvestigationState(TypedDict):
    case_id: str
    target_user: str
    raw_case_data: Dict[str, Any]
    
    # Data gathered
    subgraph_context: Dict[str, Any]
    structuring_results: Dict[str, Any]
    ring_results: Dict[str, Any]
    graph_rag_summary: str
    
    # Reasoning & Risk
    risk_score: float
    confidence_score: float
    fraud_reasoning: str
    status: str  # e.g., "INITIALIZED", "PENDING_EVIDENCE", "CONFIRMED_FRAUD", "CLEARED"
    evidence_iteration: int
    
    # Policy checks
    is_sar_required: bool
    is_account_freeze_required: bool
    is_card_block_required: bool
    is_sms_warning_required: bool
    requires_manager_approval: bool
    
    # Actions executed
    actions_taken: List[Dict[str, Any]]
    execution_logs: List[str]
    sar_report: Optional[Dict[str, Any]]
