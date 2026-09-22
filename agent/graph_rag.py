import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GraphRAGRetriever:
    """Graph-augmented Retrieval System to format graph context into rich text prompts."""

    def __init__(self, query_runner=None):
        from gsql.install_queries import GSQLQueryRunner
        self.query_runner = query_runner or GSQLQueryRunner()

    def retrieve_context(self, user_id: str) -> Dict[str, Any]:
        """Fetches 3-hop graph context, structuring analytics, and fraud ring signals."""
        subgraph = self.query_runner.get_3hop_subgraph(user_id)
        structuring = self.query_runner.detect_structuring(user_id)
        ring = self.query_runner.detect_fraud_ring(user_id)

        summary_text = self._build_text_summary(user_id, subgraph, structuring, ring)
        
        return {
            "subgraph": subgraph,
            "structuring": structuring,
            "ring": ring,
            "summary_text": summary_text
        }

    def _build_text_summary(self, user_id: str, subgraph: Dict[str, Any], structuring: Dict[str, Any], ring: Dict[str, Any]) -> str:
        lines = []
        user = subgraph.get("user") or {}
        case_meta = subgraph.get("case_metadata") or {}
        lines.append(f"=== GraphRAG Evidence Context for Target Customer: {user_id} ===")
        lines.append(f"Customer Name: {user.get('name', 'Unknown')} | Risk Score: {user.get('risk_score', 0.0)} | Status: {user.get('status', 'ACTIVE')}")
        if case_meta:
            lines.append(f"Case Trigger Type: {case_meta.get('type')} | Description: {case_meta.get('description')}")

        # Transactions
        txs = subgraph.get("transactions", [])
        lines.append(f"\n[Transaction History ({len(txs)} records analyzed)]:")
        total_val = 0.0
        for tx in txs[:10]:  # Highlight top 10 most relevant transactions
            t_id = tx.get("id") or tx.get("TransactionID")
            amt = tx.get("amount") or tx.get("TransactionAmt") or 0.0
            ts = tx.get("timestamp") or tx.get("ts") or "N/A"
            loc = tx.get("location") or f"Region {tx.get('addr1', 'Unknown')}"
            risk = tx.get("risk_score", 0.0)
            channel = tx.get("channel", "online")
            p_code = tx.get("product_cd", "")
            lines.append(f"  - TX ID: {t_id} | Amount: ${float(amt):,.2f} | TS: {ts} | Channel: {channel} | Product: {p_code} | Risk Score: {risk:.2f} | Loc: {loc}")
            total_val += float(amt)
        if len(txs) > 10:
            lines.append(f"  ... (+ {len(txs)-10} additional transactions analyzed)")
        lines.append(f"  Total Cumulative Transaction Volume: ${total_val:,.2f}")

        # Identity Telemetry
        identities = subgraph.get("identities", {})
        if identities:
            lines.append(f"\n[Device & Identity Telemetry ({len(identities)} profile links)]:")
            for t_id, id_data in list(identities.items())[:5]:
                d_type = id_data.get("device_type", "Unknown")
                d_info = id_data.get("device_info", "Unknown")
                os_info = id_data.get("id_30_os", "")
                browser = id_data.get("id_31_browser", "")
                lines.append(f"  - TX {t_id}: DeviceType={d_type} | DeviceInfo={d_info} | OS={os_info} | Browser={browser}")

        # Historical Case Memory
        history = subgraph.get("history_cases", [])
        if history:
            lines.append(f"\n[Case Memory - Historical Investigation Matches ({len(history)} cases)]:")
            for hc in history[:3]:
                lines.append(f"  - Case {hc.get('case_id')}: Outcome={hc.get('outcome')} | Pattern={hc.get('pattern')} | Exposure=${float(hc.get('exposure_usd', 0.0)):,.2f} | Notes: {hc.get('analyst_notes', '')[:120]}...")

        # Structuring signals
        lines.append("\n[GSQL Structuring Pattern Signal]:")
        if structuring.get("is_structuring_detected"):
            lines.append(f"  CRITICAL: Structuring pattern detected! Total structured amount: ${structuring.get('total_structured_amount'):,.2f} across {structuring.get('transaction_count')} transactions (Just below $10,000 threshold).")
            lines.append(f"  SAR Mandatory: {structuring.get('sar_mandatory')}")
        else:
            lines.append("  No structuring pattern detected.")

        # Fraud Ring signals
        lines.append("\n[GSQL Fraud Ring & Entity Link Signal]:")
        if ring.get("is_ring_detected"):
            lines.append(f"  HIGH RISK: Fraud ring link identified!")
            lines.append(f"  Shared Device ID: {ring.get('shared_device')}")
            lines.append(f"  Shared IP Address: {ring.get('shared_ip')}")
            lines.append(f"  Connected Account IDs: {', '.join(ring.get('connected_accounts', []))}")
        else:
            lines.append("  No shared devices or suspicious entity links found.")

        return "\n".join(lines)
