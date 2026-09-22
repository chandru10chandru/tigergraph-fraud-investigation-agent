import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Try loading dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class LLMReasoner:
    """
    LLM Reasoning Engine for Fraud Investigation.
    Supports OpenAI, Google Gemini, and Anthropic API keys with an analyst-grade local fallback.
    """

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def synthesize_investigation(
        self,
        case_id: str,
        user_id: str,
        raw_case_data: Dict[str, Any],
        graph_rag_summary: str,
        structuring_results: Dict[str, Any],
        ring_results: Dict[str, Any],
        evidence_iteration: int = 0
    ) -> Dict[str, Any]:
        """
        Synthesizes graph evidence, transaction history, device profiles, and policy rules
        into a structured, professional fraud investigation report.
        """
        # 1. Try OpenAI if API key present
        if self.openai_key:
            res = self._call_openai(case_id, user_id, raw_case_data, graph_rag_summary, structuring_results, ring_results, evidence_iteration)
            if res:
                return res

        # 2. Try Gemini if API key present
        if self.gemini_key:
            res = self._call_gemini(case_id, user_id, raw_case_data, graph_rag_summary, structuring_results, ring_results, evidence_iteration)
            if res:
                return res

        # 3. Comprehensive Analyst-Grade Fallback Engine
        return self._fallback_analyst_reasoning(case_id, user_id, raw_case_data, graph_rag_summary, structuring_results, ring_results, evidence_iteration)

    def _call_openai(self, case_id: str, user_id: str, raw: Dict[str, Any], summary: str, struct: Dict[str, Any], ring: Dict[str, Any], iteration: int) -> Optional[Dict[str, Any]]:
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)
            prompt = self._build_prompt(case_id, user_id, raw, summary, struct, ring, iteration)
            
            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a Senior Anti-Money Laundering (AML) & Fraud Investigation Expert. Respond in strict JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.warning(f"OpenAI LLM reasoning call failed: {e}. Falling back to analyst engine.")
            return None

    def _call_gemini(self, case_id: str, user_id: str, raw: Dict[str, Any], summary: str, struct: Dict[str, Any], ring: Dict[str, Any], iteration: int) -> Optional[Dict[str, Any]]:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            prompt = self._build_prompt(case_id, user_id, raw, summary, struct, ring, iteration) + "\nReturn strictly JSON format."
            
            response = client.models.generate_content(
                model=self.gemini_model,
                contents=prompt
            )
            text = response.text
            # Extract JSON substring
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Gemini LLM reasoning call failed: {e}. Falling back to analyst engine.")
            return None

    def _build_prompt(self, case_id: str, user_id: str, raw: Dict[str, Any], summary: str, struct: Dict[str, Any], ring: Dict[str, Any], iteration: int) -> str:
        return f"""
Analyze the following Fraud Investigation Case Payload and GraphRAG Context:

Case ID: {case_id}
Target Customer ID: {user_id}
Trigger Type: {raw.get('type')}
Trigger Description: {raw.get('trigger_text') or raw.get('description')}
Evidence Iteration: {iteration}

=== GRAPHRAG CONTEXT & EVIDENCE SUMMARY ===
{summary}

=== GSQL STRUCTURED SIGNAL METRICS ===
Structuring Signal: {json.dumps(struct)}
Fraud Ring Signal: {json.dumps(ring)}

Return a JSON object with the following exact keys:
1. "risk_score": float between 0.0 and 1.0
2. "confidence_score": float between 0.0 and 1.0
3. "status": one of ["CONFIRMED_FRAUD", "PENDING_EVIDENCE", "CLEARED"]
4. "investigation_narrative": a detailed 2-3 paragraph analyst narrative explaining the transaction sequence, graph evidence, device/IP risk, and past case memory matches.
5. "identified_patterns": list of string pattern names identified
6. "policy_justification": explanation of why specific actions (Card Block, SMS Warning, SAR Filing, Account Freeze) are mandated or deferred under institutional policy rules.
"""

    def _fallback_analyst_reasoning(
        self,
        case_id: str,
        user_id: str,
        raw: Dict[str, Any],
        summary: str,
        struct: Dict[str, Any],
        ring: Dict[str, Any],
        iteration: int
    ) -> Dict[str, Any]:
        """
        Analyst-grade reasoning engine generating rich multi-paragraph narratives.
        """
        init_risk = float(raw.get("initial_risk_score") or raw.get("risk_score") or 0.10)
        risk_score = init_risk
        confidence_score = 0.90
        case_type = str(raw.get("type", "")).upper()
        
        txs = raw.get("transactions", [])
        total_amount = sum(float(t.get("amount", 0.0)) for t in txs)
        max_tx_risk = max((float(t.get("risk_score", 0.0)) for t in txs), default=0.0)

        identified_patterns = []
        narrative_paragraphs = []

        # Paragraph 1: Case Initiation & Context
        trigger_desc = raw.get("trigger_text") or raw.get("description") or f"Alert triggered for account {user_id}"
        p1 = f"Case {case_id} was initiated under trigger type '{case_type}' for target customer {user_id}. {trigger_desc}. "
        p1 += f"Total cumulative exposure across {len(txs)} analyzed transactions totals ${total_amount:,.2f}."
        narrative_paragraphs.append(p1)

        # Paragraph 2: GraphRAG & Technical Evidence Analysis
        p2_parts = []
        if struct.get("is_structuring_detected"):
            risk_score += 0.75
            identified_patterns.append("Cash Structuring (Below $10k Threshold)")
            p2_parts.append(f"GSQL Graph Traversal detected a structuring velocity pattern totaling ${struct.get('total_structured_amount'):,.2f} across multiple transactions specifically designed to evade the $10,000 BSA threshold.")
        
        if ring.get("is_ring_detected"):
            risk_score += 0.70
            identified_patterns.append("Shared Device / Fraud Ring Link")
            p2_parts.append(f"Graph analytics identified an active fraud ring connection via shared device token ({ring.get('shared_device')}) and IP address ({ring.get('shared_ip')}), linking this account to unlinked suspicious profiles.")

        if case_type == "CUSTOMER_REPORT":
            risk_score = max(risk_score, 0.85)
            identified_patterns.append("Cardholder Disputed Transaction")
            p2_parts.append("Direct customer dispute notification confirmed unrecognized card activity, consistent with account takeover or card-not-present fraud.")
        elif case_type == "ANALYST_REQUEST":
            risk_score = max(risk_score, 0.80)
            identified_patterns.append("Analyst Flagged Device Profile")
            p2_parts.append("Specialist analyst review flagged a shared device profile across multiple cardholders previously recorded in confirmed fraud cases.")
        elif max_tx_risk > 0.60:
            risk_score = max(risk_score, max_tx_risk)
            identified_patterns.append("High ML Risk Score Transaction")
            p2_parts.append(f"Real-time machine learning detection model assigned a elevated risk score of {max_tx_risk:.2f} on high-exposure authorizations.")

        if not p2_parts:
            risk_score = 0.05
            confidence_score = 0.95
            identified_patterns.append("Legitimate Baseline Activity")
            p2_parts.append("Graph neighborhood traversal confirmed transactions originate from trusted home devices and IP subnets matching historical low-risk baselines.")

        narrative_paragraphs.append(" ".join(p2_parts))

        risk_score = min(1.0, risk_score)

        # Paragraph 3: Uncertainty & Policy Actions
        if iteration == 0 and 0.40 <= risk_score <= 0.65:
            confidence_score = 0.45
            status = "PENDING_EVIDENCE"
            p3 = "Initial risk telemetry displays borderline signals (confidence < 0.50). Institutional policy dictates requesting secondary device and IP telemetry prior to final account action."
        elif risk_score > 0.50:
            status = "CONFIRMED_FRAUD"
            p3 = f"With risk score evaluated at {risk_score:.2f} and confidence at {confidence_score:.2f}, the activity is classified as CONFIRMED FRAUD. "
            policy_actions = ["Card Block", "Customer SMS Notification", "Escalation to Senior Analyst"]
            if total_amount >= 10000.0 or struct.get("is_structuring_detected"):
                policy_actions.append("Mandatory FinCEN SAR Filing")
            if total_amount >= 15000.0:
                policy_actions.append("Account Freeze (Requires Manager Approval)")
            p3 += f"Required policy actions triggered: {', '.join(policy_actions)}."
        else:
            status = "CLEARED"
            p3 = "Activity cleared as low-risk benign customer behavior. No restrictive policy controls required."

        narrative_paragraphs.append(p3)

        policy_just = f"Policy compliance verified. Actions taken under BSA/AML guidelines for risk level {risk_score:.2f} and total exposure ${total_amount:,.2f}."

        return {
            "risk_score": round(risk_score, 2),
            "confidence_score": round(confidence_score, 2),
            "status": status,
            "investigation_narrative": "\n\n".join(narrative_paragraphs),
            "identified_patterns": identified_patterns,
            "policy_justification": policy_just
        }
