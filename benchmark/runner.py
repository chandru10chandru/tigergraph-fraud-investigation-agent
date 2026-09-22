import os
import json
import time
import logging
from typing import Dict, Any, List

from agent.workflow import build_fraud_investigation_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class BenchmarkRunner:
    def __init__(self, dataset_path: str = None):
        if dataset_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            real_path = os.path.join(base_dir, "benchmark", "real_dataset.json")
            synth_path = os.path.join(base_dir, "benchmark", "dataset.json")
            dataset_path = real_path if os.path.exists(real_path) else synth_path
        self.dataset_path = dataset_path
        with open(self.dataset_path, "r") as f:
            self.dataset = json.load(f).get("cases", [])
        self.graph = build_fraud_investigation_graph()

    def run_benchmark(self) -> Dict[str, Any]:
        logger.info(f"Starting Benchmark evaluation on {len(self.dataset)} cases...")
        results = []
        tp = fp = tn = fn = 0
        policy_correct = 0
        total_latency = 0.0

        for case in self.dataset:
            start_t = time.time()
            initial_state = {
                "case_id": case["case_id"],
                "target_user": case["target_user"],
                "raw_case_data": case,
                "subgraph_context": {},
                "structuring_results": {},
                "ring_results": {},
                "graph_rag_summary": "",
                "risk_score": 0.0,
                "confidence_score": 0.0,
                "fraud_reasoning": "",
                "status": "INITIALIZED",
                "evidence_iteration": 0,
                "is_sar_required": False,
                "is_account_freeze_required": False,
                "is_card_block_required": False,
                "is_sms_warning_required": False,
                "requires_manager_approval": False,
                "actions_taken": [],
                "execution_logs": []
            }

            final_state = self.graph.invoke(initial_state)
            latency = time.time() - start_t
            total_latency += latency

            pred_fraud = final_state.get("risk_score", 0.0) > 0.50
            actual_fraud = case.get("expected_fraud", False)

            if pred_fraud and actual_fraud:
                tp += 1
            elif pred_fraud and not actual_fraud:
                fp += 1
            elif not pred_fraud and actual_fraud:
                fn += 1
            else:
                tn += 1

            # Check policy correctness
            sar_req = final_state.get("is_sar_required", False)
            if (actual_fraud and case.get("total_amount", 0) >= 10000.0) == sar_req or (case.get("type") == "STRUCTURING" and sar_req):
                policy_correct += 1

            results.append({
                "case_id": case["case_id"],
                "type": case["type"],
                "actual_fraud": actual_fraud,
                "predicted_fraud": pred_fraud,
                "risk_score": round(final_state.get("risk_score", 0.0), 2),
                "confidence_score": round(final_state.get("confidence_score", 0.0), 2),
                "evidence_iterations": final_state.get("evidence_iteration", 0),
                "actions_taken_count": len(final_state.get("actions_taken", [])),
                "latency_ms": round(latency * 1000, 2)
            })

        total_cases = len(self.dataset)
        accuracy = (tp + tn) / total_cases if total_cases > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        policy_accuracy = policy_correct / total_cases if total_cases > 0 else 0.0
        avg_latency = total_latency / total_cases if total_cases > 0 else 0.0

        summary = {
            "total_cases_evaluated": total_cases,
            "accuracy": round(accuracy * 100, 2),
            "precision": round(precision * 100, 2),
            "recall": round(recall * 100, 2),
            "f1_score": round(f1_score * 100, 2),
            "policy_compliance_rate": round(policy_accuracy * 100, 2),
            "average_latency_ms": round(avg_latency * 1000, 2),
            "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
            "detailed_case_results": results
        }

        # Save benchmark report json
        report_path = os.path.join(os.path.dirname(self.dataset_path), "benchmark_results.json")
        with open(report_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Benchmark completed successfully! Accuracy: {summary['accuracy']}%, F1: {summary['f1_score']}%, Policy Compliance: {summary['policy_compliance_rate']}%")
        return summary

if __name__ == "__main__":
    runner = BenchmarkRunner()
    results = runner.run_benchmark()
    print("\n" + "="*50)
    print("      FRAUD INVESTIGATION BENCHMARK RESULTS     ")
    print("="*50)
    print(f"Total Cases Evaluated   : {results['total_cases_evaluated']}")
    print(f"Classification Accuracy : {results['accuracy']}%")
    print(f"Precision               : {results['precision']}%")
    print(f"Recall                  : {results['recall']}%")
    print(f"F1 Score                : {results['f1_score']}%")
    print(f"Policy Compliance Rate  : {results['policy_compliance_rate']}%")
    print(f"Avg Agent Latency       : {results['average_latency_ms']} ms")
    print("="*50)
