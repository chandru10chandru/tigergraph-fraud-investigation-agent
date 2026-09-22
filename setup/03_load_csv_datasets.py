import os
import csv
import json
import logging
from typing import Dict, Any, List, Set

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logger = logging.getLogger(__name__)

def load_csv_datasets(datasets_dir: str, output_path: str) -> Dict[str, Any]:
    """
    Parses case_pack.csv, closed_cases_history.csv, transactions.csv, and identity.csv.
    Generates a structured graph dataset (real_dataset.json) for the 20 HHG benchmark cases.
    """
    case_pack_path = os.path.join(datasets_dir, "case_pack.csv")
    closed_cases_path = os.path.join(datasets_dir, "closed_cases_history.csv")
    transactions_path = os.path.join(datasets_dir, "transactions.csv")
    identity_path = os.path.join(datasets_dir, "identity.csv")

    logger.info("Reading benchmark cases from case_pack.csv...")
    cases = []
    customer_ids: Set[str] = set()
    card_ids: Set[str] = set()
    flagged_txn_ids: Set[str] = set()

    with open(case_pack_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("case_id"):
                continue
            c_id = row["customer_id"].strip() if row.get("customer_id") else ""
            card_id = row["card_id"].strip() if row.get("card_id") else ""
            txn_id = row["flagged_txn_id"].strip() if row.get("flagged_txn_id") else ""

            if c_id:
                customer_ids.add(c_id)
            if card_id:
                card_ids.add(card_id)
            if txn_id:
                flagged_txn_ids.add(txn_id)

            risk_val = float(row["risk_score"]) if row.get("risk_score") and row["risk_score"].strip() else 0.50

            cases.append({
                "case_id": row["case_id"].strip(),
                "opened_at": row.get("opened_at", "").strip(),
                "type": row.get("trigger_type", "risk_score").strip().upper(),
                "trigger_text": row.get("trigger_text", "").strip(),
                "flagged_txn_id": txn_id,
                "card_id": card_id,
                "target_user": c_id,
                "initial_risk_score": risk_val,
                "transactions": [],
                "identities": {},
                "history_cases": []
            })

    logger.info(f"Loaded {len(cases)} benchmark cases. Targeted customers: {len(customer_ids)}")

    # Load matching closed cases history
    logger.info("Loading closed cases history...")
    closed_cases = []
    with open(closed_cases_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            closed_cases.append(row)

    # Attach relevant closed cases to benchmark cases based on customer_id or card_id
    for case in cases:
        c_id = case["target_user"]
        card_id = case["card_id"]
        relevant_history = [
            cc for cc in closed_cases
            if (c_id and cc.get("customer_id") == c_id) or (card_id and cc.get("card_id") == card_id)
        ]
        case["history_cases"] = relevant_history

    # Fast scan of transactions.csv for target customers
    logger.info("Scanning transactions.csv for benchmark customer transactions...")
    all_matching_txns = []
    matching_txn_ids = set()

    with open(transactions_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            c_id = row.get("customer_id", "").strip()
            t_id = row.get("TransactionID", "").strip()
            if c_id in customer_ids or t_id in flagged_txn_ids:
                tx_record = {
                    "id": t_id,
                    "amount": float(row["TransactionAmt"]) if row.get("TransactionAmt") else 0.0,
                    "timestamp": row.get("ts", "").strip(),
                    "customer_id": c_id,
                    "card1": row.get("card1", ""),
                    "card2": row.get("card2", ""),
                    "channel": row.get("channel", "online"),
                    "product_cd": row.get("ProductCD", ""),
                    "email_domain": row.get("P_emaildomain", ""),
                    "risk_score": float(row["risk_score"]) if row.get("risk_score") else 0.0,
                    "location": f"Billing Region {row.get('addr1', 'Unknown')}"
                }
                all_matching_txns.append(tx_record)
                matching_txn_ids.add(t_id)

    logger.info(f"Retrieved {len(all_matching_txns)} transactions matching benchmark customers.")

    # Scan identity.csv for matching transaction IDs
    logger.info("Scanning identity.csv for device & identity profiles...")
    identity_map = {}
    with open(identity_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t_id = row.get("TransactionID", "").strip()
            if t_id in matching_txn_ids:
                identity_map[t_id] = {
                    "device_type": row.get("DeviceType", ""),
                    "device_info": row.get("DeviceInfo", ""),
                    "id_30_os": row.get("id_30", ""),
                    "id_31_browser": row.get("id_31", "")
                }

    logger.info(f"Retrieved {len(identity_map)} identity profiles.")

    # Map transactions & identity profiles back into cases
    txn_by_customer = {}
    for tx in all_matching_txns:
        c_id = tx["customer_id"]
        if c_id not in txn_by_customer:
            txn_by_customer[c_id] = []
        txn_by_customer[c_id].append(tx)

    total_exposure = 0.0
    for case in cases:
        c_id = case["target_user"]
        txs = txn_by_customer.get(c_id, [])
        case["transactions"] = txs
        case["total_amount"] = sum(t["amount"] for t in txs)
        total_exposure += case["total_amount"]
        
        # Attach identity info
        case_identities = {}
        for t in txs:
            t_id = t["id"]
            if t_id in identity_map:
                case_identities[t_id] = identity_map[t_id]
        case["identities"] = case_identities

        # User details object
        max_risk = max((t["risk_score"] for t in txs), default=case["initial_risk_score"])
        case["user_details"] = {
            "id": c_id,
            "name": f"Customer {c_id}",
            "email": f"{c_id.lower()}@bank-client.com",
            "risk_score": round(max_risk, 2),
            "status": "SUSPICIOUS" if max_risk > 0.60 else "ACTIVE"
        }
        
        # Expected ground truth heuristic for benchmark runner
        case["expected_fraud"] = max_risk > 0.60 or case["type"] in ("CUSTOMER_REPORT", "ANALYST_REQUEST")
        case["description"] = case["trigger_text"]

    output_dataset = {
        "dataset_name": "IEEE-CIS Fraud Benchmark (HHG)",
        "total_cases": len(cases),
        "total_transactions_indexed": len(all_matching_txns),
        "cases": cases
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_dataset, f, indent=2)

    logger.info(f"Successfully generated {output_path} with {len(cases)} cases.")
    return output_dataset

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    datasets_dir = os.path.join(base_dir, "datasets")
    output_path = os.path.join(base_dir, "benchmark", "real_dataset.json")
    load_csv_datasets(datasets_dir, output_path)
