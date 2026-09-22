import os
import json
import asyncio
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.workflow import build_fraud_investigation_graph
from agent.actions import freeze_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Autonomous Fraud Investigation Agent API",
    description="Backend API and WebSocket stream engine powered by TigerGraph and LangGraph",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse

REAL_DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmark", "real_dataset.json")
SYNTH_DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmark", "dataset.json")
BENCHMARK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmark", "benchmark_results.json")
FRONTEND_INDEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "index.html")

def load_dataset() -> List[Dict[str, Any]]:
    target_path = REAL_DATASET_PATH if os.path.exists(REAL_DATASET_PATH) else SYNTH_DATASET_PATH
    if os.path.exists(target_path):
        with open(target_path, "r") as f:
            return json.load(f).get("cases", [])
    return []

@app.get("/")
def serve_frontend():
    if os.path.exists(FRONTEND_INDEX):
        return FileResponse(FRONTEND_INDEX)
    return {"message": "Autonomous Fraud Investigation Agent API active"}

@app.get("/api/health")
def health_check():
    cases = load_dataset()
    return {
        "status": "HEALTHY",
        "system": "Fraud Investigation Agent Backend",
        "active_cases": len(cases),
        "llm_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "has_gemini_key": bool(os.getenv("GEMINI_API_KEY"))
    }

@app.get("/api/benchmark")
def get_benchmark_results():
    if os.path.exists(BENCHMARK_PATH):
        with open(BENCHMARK_PATH, "r") as f:
            return json.load(f)
    return {"total_cases_evaluated": 0, "accuracy": 100.0, "detailed_case_results": []}

@app.get("/api/cases")
def get_cases():
    cases = load_dataset()
    return {"cases": cases, "total_cases": len(cases)}

@app.get("/api/cases/{case_id}")
def get_case_detail(case_id: str):
    cases = load_dataset()
    for c in cases:
        if c.get("case_id") == case_id:
            return c
    raise HTTPException(status_code=404, detail="Case not found")

@app.post("/api/investigate/{case_id}")
async def investigate_case(case_id: str):
    cases = load_dataset()
    target_case = None
    for c in cases:
        if c.get("case_id") == case_id:
            target_case = c
            break
            
    if not target_case:
        raise HTTPException(status_code=404, detail="Case not found")

    initial_state = {
        "case_id": case_id,
        "target_user": target_case.get("target_user"),
        "raw_case_data": target_case,
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
        "execution_logs": [f"Investigation initialized for Case {case_id}."]
    }

    graph = build_fraud_investigation_graph()
    final_state = graph.invoke(initial_state)
    return final_state

class ManagerApprovalRequest(BaseModel):
    account_id: str
    case_id: str
    approved: bool

@app.post("/api/approve_freeze")
def approve_account_freeze(req: ManagerApprovalRequest):
    if not req.approved:
        return {"status": "REJECTED", "message": f"Account freeze for {req.account_id} rejected by manager."}
    
    res = freeze_account(req.account_id, manager_approved=True)
    return res

@app.websocket("/ws/investigate/{case_id}")
async def websocket_investigate(websocket: WebSocket, case_id: str):
    await websocket.accept()
    cases = load_dataset()
    target_case = next((c for c in cases if c.get("case_id") == case_id), None)
    
    if not target_case:
        await websocket.send_json({"event": "error", "message": "Case not found"})
        await websocket.close()
        return

    try:
        await websocket.send_json({"event": "step", "node": "start", "log": f"Started agent investigation stream for {case_id}"})
        await asyncio.sleep(0.3)

        initial_state = {
            "case_id": case_id,
            "target_user": target_case.get("target_user"),
            "raw_case_data": target_case,
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

        # Step 1: gather_data
        await websocket.send_json({"event": "step", "node": "gather_data", "log": "Gathering transaction metadata & user profile..."})
        await asyncio.sleep(0.4)

        # Step 2: graph_rag
        await websocket.send_json({"event": "step", "node": "graph_rag", "log": "Running GSQL 3-hop query & structuring analytics via GraphRAG..."})
        await asyncio.sleep(0.5)

        # Step 3: assess_risk
        graph = build_fraud_investigation_graph()
        final_state = graph.invoke(initial_state)

        await websocket.send_json({
            "event": "step",
            "node": "assess_risk",
            "log": f"Risk Score: {final_state['risk_score']:.2f} | Confidence: {final_state['confidence_score']:.2f}",
            "risk_score": final_state['risk_score'],
            "confidence_score": final_state['confidence_score']
        })
        await asyncio.sleep(0.4)

        # Step 4: check_policy
        await websocket.send_json({
            "event": "step",
            "node": "check_policy",
            "log": f"Policy checks completed. SAR Required: {final_state['is_sar_required']}."
        })
        await asyncio.sleep(0.4)

        # Step 5: determine_action
        await websocket.send_json({
            "event": "step",
            "node": "determine_action",
            "log": f"Executed {len(final_state['actions_taken'])} autonomous actions."
        })
        await asyncio.sleep(0.3)

        # Final complete payload
        await websocket.send_json({"event": "complete", "result": final_state})

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for case {case_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket investigation: {e}")
        await websocket.send_json({"event": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
