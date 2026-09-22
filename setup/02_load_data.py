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

def generate_benchmark_dataset() -> Dict[str, Any]:
    """Generates 20 distinct fraud investigation benchmark cases with graph entities."""
    cases = []
    
    # 1-5: Structuring Cases
    for i in range(1, 6):
        cases.append({
            "case_id": f"CASE-STR-{i:03d}",
            "type": "STRUCTURING",
            "target_user": f"user_str_{i}",
            "user_details": {"id": f"user_str_{i}", "name": f"Structuring Suspect {i}", "email": f"struct{i}@mail.com", "phone": f"+1555010{i}", "created_at": "2024-01-10", "risk_score": 0.82, "status": "SUSPICIOUS"},
            "transactions": [
                {"id": f"tx_str_{i}_1", "amount": 9500.0, "timestamp": "2024-09-01T10:00:00", "location": "NY, USA", "device_id": f"dev_str_{i}", "ip_address": f"192.168.1.{10+i}", "is_fraud": True, "risk_score": 0.88, "merchant": "Merch_ATM_1"},
                {"id": f"tx_str_{i}_2", "amount": 9800.0, "timestamp": "2024-09-01T11:30:00", "location": "NY, USA", "device_id": f"dev_str_{i}", "ip_address": f"192.168.1.{10+i}", "is_fraud": True, "risk_score": 0.90, "merchant": "Merch_ATM_2"},
                {"id": f"tx_str_{i}_3", "amount": 9200.0, "timestamp": "2024-09-01T14:15:00", "location": "NY, USA", "device_id": f"dev_str_{i}", "ip_address": f"192.168.1.{10+i}", "is_fraud": True, "risk_score": 0.85, "merchant": "Merch_Wire_1"}
            ],
            "total_amount": 28500.0,
            "expected_fraud": True,
            "expected_action": "FILE_SAR_AND_FREEZE",
            "description": f"Multiple cash deposits/wires just below $10,000 threshold totaling ${28500.0}"
        })

    # 6-10: Shared Device / Fraud Ring Cases
    for i in range(1, 6):
        shared_dev = f"dev_ring_shared_{i}"
        shared_ip = f"10.0.44.{i}"
        cases.append({
            "case_id": f"CASE-RING-{i:03d}",
            "type": "FRAUD_RING",
            "target_user": f"user_ring_{i}_a",
            "user_details": {"id": f"user_ring_{i}_a", "name": f"Ring Member {i}A", "email": f"ring{i}a@mail.com", "phone": f"+1555020{i}", "created_at": "2024-05-12", "risk_score": 0.79, "status": "ACTIVE"},
            "connected_users": [f"user_ring_{i}_b", f"user_ring_{i}_c"],
            "transactions": [
                {"id": f"tx_ring_{i}_1", "amount": 4500.0, "timestamp": "2024-09-02T08:00:00", "location": "FL, USA", "device_id": shared_dev, "ip_address": shared_ip, "is_fraud": True, "risk_score": 0.80, "merchant": "CryptoExchange_X"}
            ],
            "shared_device": shared_dev,
            "shared_ip": shared_ip,
            "total_amount": 13500.0,
            "expected_fraud": True,
            "expected_action": "BLOCK_CARD_AND_ESCALATE",
            "description": f"Shared device {shared_dev} and IP {shared_ip} across 3 unlinked accounts"
        })

    # 11-15: Card Fraud / Stolen Card
    for i in range(1, 6):
        cases.append({
            "case_id": f"CASE-CARD-{i:03d}",
            "type": "CARD_FRAUD",
            "target_user": f"user_card_{i}",
            "user_details": {"id": f"user_card_{i}", "name": f"Card Victim {i}", "email": f"card{i}@mail.com", "phone": f"+1555030{i}", "created_at": "2022-03-15", "risk_score": 0.65, "status": "ACTIVE"},
            "card_id": f"card_val_{i}",
            "transactions": [
                {"id": f"tx_card_{i}_1", "amount": 1250.0, "timestamp": "2024-09-03T02:10:00", "location": "Overseas/VPN", "device_id": f"dev_unrecognized_{i}", "ip_address": f"185.220.101.{i}", "is_fraud": True, "risk_score": 0.92, "merchant": "LuxuryGoods_Store"}
            ],
            "total_amount": 1250.0,
            "expected_fraud": True,
            "expected_action": "BLOCK_CARD_AND_SMS",
            "description": f"High value transaction from foreign VPN IP on luxury goods merchant"
        })

    # 16-20: Legitimate / Benign Cases
    for i in range(1, 6):
        cases.append({
            "case_id": f"CASE-LEG-{i:03d}",
            "type": "LEGITIMATE",
            "target_user": f"user_leg_{i}",
            "user_details": {"id": f"user_leg_{i}", "name": f"Honest Customer {i}", "email": f"legit{i}@mail.com", "phone": f"+1555040{i}", "created_at": "2020-01-01", "risk_score": 0.05, "status": "ACTIVE"},
            "transactions": [
                {"id": f"tx_leg_{i}_1", "amount": 320.0, "timestamp": "2024-09-04T12:00:00", "location": "Home City", "device_id": f"dev_known_{i}", "ip_address": f"73.12.99.{i}", "is_fraud": False, "risk_score": 0.08, "merchant": "GrocerySuperstore"}
            ],
            "total_amount": 320.0,
            "expected_fraud": False,
            "expected_action": "APPROVE",
            "description": "Standard low-risk recurring transaction from known home device"
        })

    return {"cases": cases}

def load_data_to_tigergraph(conn, dataset: Dict[str, Any]):
    """Upserts vertex and edge records into TigerGraph DB instance."""
    logger.info("Upserting dataset into TigerGraph database...")
    for case in dataset["cases"]:
        u = case["user_details"]
        # Upsert User vertex
        conn.upsertVertex("User", u["id"], attributes={
            "name": u["name"], "email": u["email"], "phone": u["phone"],
            "created_at": u["created_at"], "risk_score": u["risk_score"], "status": u["status"]
        })
        
        # Upsert transactions & connections
        for tx in case["transactions"]:
            conn.upsertVertex("Transaction", tx["id"], attributes={
                "amount": tx["amount"], "timestamp": tx["timestamp"],
                "location": tx["location"], "device_id": tx["device_id"],
                "ip_address": tx["ip_address"], "is_fraud": tx["is_fraud"],
                "risk_score": tx["risk_score"]
            })
            conn.upsertEdge("User", u["id"], "PERFORMED_TRANSACTION", "Transaction", tx["id"])

def main():
    logger.info("Starting Phase 1 Data Loading...")
    dataset = generate_benchmark_dataset()
    
    # Save dataset locally as json database
    data_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(os.path.dirname(data_dir), "benchmark", "dataset.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    with open(json_path, "w") as f:
        json.dump(dataset, f, indent=2)
    logger.info(f"Saved 20 benchmark test cases to {json_path}")
    
    # Try tigergraph connection if available
    host = os.getenv("TG_HOST", "http://localhost:9000")
    graphname = os.getenv("TG_GRAPH", "FraudInvestigation")
    if HAS_PYTIGERGRAPH:
        try:
            conn = tg.TigerGraphConnection(host=host, graphname=graphname)
            load_data_to_tigergraph(conn, dataset)
            logger.info("Successfully loaded dataset into live TigerGraph instance.")
        except Exception as e:
            logger.info(f"TigerGraph instance loading skipped ({e}). Offline JSON store active.")
    else:
        logger.info("pyTigerGraph not installed. Local JSON store ready for benchmarking and agent operations.")

if __name__ == "__main__":
    main()
