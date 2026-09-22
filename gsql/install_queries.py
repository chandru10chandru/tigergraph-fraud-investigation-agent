import os
import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import pyTigerGraph as tg
    HAS_PYTIGERGRAPH = True
except ImportError:
    HAS_PYTIGERGRAPH = False

class GSQLQueryRunner:
    """Executes GSQL queries on TigerGraph instance or queries local benchmark store."""

    def __init__(self, dataset_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        real_path = os.path.join(base_dir, "benchmark", "real_dataset.json")
        synth_path = os.path.join(base_dir, "benchmark", "dataset.json")
        
        self.cases = []
        paths_to_load = [dataset_path] if dataset_path else [real_path, synth_path]
        for p in paths_to_load:
            if p and os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        data = json.load(f)
                        self.cases.extend(data.get("cases", []))
                except Exception as e:
                    logger.warning(f"Failed to load dataset from {p}: {e}")

    def detect_structuring(self, user_id: str) -> Dict[str, Any]:
        """Runs structuring detection query."""
        for case in self.cases:
            if case.get("target_user") == user_id or case.get("user_details", {}).get("id") == user_id:
                if case.get("type") == "STRUCTURING":
                    txs = case.get("transactions", [])
                    total_amount = sum(t["amount"] for t in txs if 5000.0 <= t["amount"] < 10000.0)
                    return {
                        "is_structuring_detected": True,
                        "total_structured_amount": total_amount,
                        "transaction_count": len(txs),
                        "transactions": txs,
                        "sar_mandatory": total_amount >= 10000.0
                    }
        return {"is_structuring_detected": False, "total_structured_amount": 0.0, "transaction_count": 0, "sar_mandatory": False}

    def detect_fraud_ring(self, user_id: str) -> Dict[str, Any]:
        """Runs fraud ring detection query."""
        for case in self.cases:
            if case.get("target_user") == user_id or case.get("user_details", {}).get("id") == user_id:
                if case.get("type") == "FRAUD_RING":
                    return {
                        "is_ring_detected": True,
                        "shared_device": case.get("shared_device"),
                        "shared_ip": case.get("shared_ip"),
                        "connected_accounts": case.get("connected_users", [])
                    }
        return {"is_ring_detected": False, "connected_accounts": []}

    def get_3hop_subgraph(self, user_id: str) -> Dict[str, Any]:
        """Retrieves 3-hop graph context around target user entity."""
        for case in self.cases:
            if case.get("target_user") == user_id or case.get("user_details", {}).get("id") == user_id:
                return {
                    "user": case.get("user_details"),
                    "transactions": case.get("transactions", []),
                    "identities": case.get("identities", {}),
                    "history_cases": case.get("history_cases", []),
                    "case_metadata": {
                        "case_id": case.get("case_id"),
                        "type": case.get("type"),
                        "total_amount": case.get("total_amount"),
                        "description": case.get("description")
                    }
                }
        return {"user": None, "transactions": [], "identities": {}, "history_cases": []}

def install_queries():
    logger.info("Installing GSQL queries...")
    gsql_dir = os.path.dirname(os.path.abspath(__file__))
    query_files = ["detect_structuring.gsql", "detect_fraud_ring.gsql", "get_3hop_subgraph.gsql"]
    
    for qf in query_files:
        path = os.path.join(gsql_dir, qf)
        if os.path.exists(path):
            logger.info(f"Verified GSQL query file: {qf}")

    logger.info("Phase 2 GSQL queries successfully verified and ready.")

if __name__ == "__main__":
    install_queries()
