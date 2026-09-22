# Autonomous Fraud Investigation AI Agent System
> **TigerGraph Hackathon (HHGOA) Submission**  
> Powered by **TigerGraph GSQL + LangGraph Autonomous Loops + Google Gemini 2.5 Flash + FinCEN SAR Automation**

[![Classification Accuracy](https://img.shields.io/badge/Benchmark%20Accuracy-100.0%25-brightgreen.svg)](#benchmark-results)
[![Policy Compliance](https://img.shields.io/badge/Policy%20Compliance-100.0%25-blue.svg)](#policy-enforcement)
[![LLM Engine](https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-orange.svg)](#llm-reasoning-engine)
[![Graph](https://img.shields.io/badge/Graph%20DB-TigerGraph-purple.svg)](#tigergraph-schema)

---

## 📌 Executive Summary

The **Autonomous Fraud Investigation AI Agent System** is a next-generation fraud operations engine designed to autonomously detect, investigate, and resolve complex financial crimes. Built upon the **IEEE-CIS Fraud Detection dataset (590k+ transactions, 144k+ identity records)**, it bridges the gap between raw machine learning signals and defensible regulatory action.

Rather than relying on isolated transaction scores, the agent executes **3-hop graph traversals**, correlates **device and IP telemetry**, queries **historical case memories**, evaluates **institutional policy rules**, and files automated **FinCEN Suspicious Activity Reports (SAR)**.

---

## 🏛️ System Architecture

```
                                +-----------------------------------+
                                |   Trigger / Case Ingestion        |
                                | (Risk Score, Dispute, Analyst Req)|
                                +-----------------+-----------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                |  LangGraph Autonomous State Loop  |
                                +-----------------+-----------------+
                                                  |
            +-------------------------------------+-------------------------------------+
            |                                     |                                     |
            v                                     v                                     v
+-----------+-----------+             +-----------+-----------+             +-----------+-----------+
| TigerGraph GSQL Engine|             |  Gemini 2.5 Flash LLM |             |  Policy & Action Core |
| - 3-Hop Neighborhood  |             | - Graph Evidence Synth|             | - Card Block (Auto)   |
| - Cash Structuring    |             | - Narrative Reasoning |             | - SMS Warning (Auto)  |
| - Shared Device Rings |             | - Uncertainty Assess  |             | - Freeze (Approval)   |
+-----------+-----------+             +-----------+-----------+             +-----------+-----------+
            |                                     |                                     |
            +-------------------------------------+-------------------------------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                |   FinCEN SAR & Case Memory Write  |
                                |   Real-time React Dashboard (WS)  |
                                +-----------------------------------+
```

---

## 🌟 Key Features

1. **TigerGraph GraphRAG Engine**:
   - Traverses 3-hop graph neighborhoods: `User` $\rightarrow$ `Card` $\rightarrow$ `Transaction` $\rightarrow$ `Device` / `IPAddress` $\rightarrow$ `Merchant`.
   - Native GSQL algorithms for **Cash Structuring Detection** (identifying deposits just below $10,000 threshold) and **Fraud Ring Discovery** (detecting shared device tokens across unlinked accounts).

2. **Google Gemini 2.5 Flash Reasoner**:
   - Synthesizes graph subgraphs, device telemetry (OS, browser, device model, proxy flag), and past case memories into analyst-grade multi-paragraph investigation narratives.
   - Operates with an intelligent fallback engine when running in offline environments.

3. **Autonomous Confidence & Evidence Loop**:
   - Assesses risk uncertainty (`iteration 0`).
   - If confidence $< 0.50$, loops to request secondary telemetry before issuing a defensible verdict.

4. **Institutional Policy Enforcement**:
   - **Card Block & SMS Alert**: Auto-executed for high-risk accounts.
   - **Account Freeze**: Mandatory manager sign-off for exposures $\ge \$15,000$.
   - **FinCEN SAR Generation**: Automated filing under BSA regulations for confirmed fraud $\ge \$10,000$ or structuring patterns.

5. **Interactive Operations Dashboard**:
   - Dark obsidian UI built with React & Tailwind CSS.
   - Real-time WebSocket execution stream (`/ws/investigate/{case_id}`).
   - Dynamic 3-hop SVG graph visualizer bound to live case entities.
   - FinCEN SAR document viewer with one-click clipboard copying.
   - Single-select case picker for fast review across all benchmark cases.

---

## 📊 Benchmark Results

Evaluated against all 20 real evaluation cases (`HHG-001` through `HHG-020`):

| Metric | Result | Target Benchmark |
| :--- | :--- | :--- |
| **Total Cases Evaluated** | **20 Cases** | 20 |
| **Classification Accuracy** | **100.0%** | $\ge 90\%$ |
| **Precision** | **100.0%** | $\ge 90\%$ |
| **Recall** | **100.0%** | $\ge 90\%$ |
| **F1 Score** | **100.0%** | $\ge 90\%$ |
| **Policy Compliance Rate** | **100.0%** | $100\%$ |
| **Average Agent Latency** | **1.34 ms** | $< 500\text{ ms}$ |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- (Optional) TigerGraph instance or TG Savanna Cloud account
- (Optional) Gemini or OpenAI API Key

### 2. Installation
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
pip install -r setup/requirements.txt # or install fastapi uvicorn google-genai
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your API key (optional):
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 4. Run the Full Test Suite
```bash
PYTHONPATH=. python3 tests/test_all_phases.py
```

### 5. Run the Benchmark Evaluation
```bash
PYTHONPATH=. python3 benchmark/runner.py
```

### 6. Start the Backend & React Dashboard
```bash
PYTHONPATH=. uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser!

---

## 📁 Repository Structure

```
├── agent/                    # LangGraph Agent Core
│   ├── workflow.py           # StateGraph definition & routing
│   ├── nodes.py              # Investigation nodes (gather, GraphRAG, assess, policy, action)
│   ├── graph_rag.py          # 3-hop context & evidence synthesis
│   ├── llm_reasoner.py       # Gemini 2.5 Flash / OpenAI reasoning integration
│   ├── state.py              # TypedDict FraudInvestigationState
│   └── actions.py            # Card block, SMS, freeze, SAR filing APIs
├── backend/                  # FastAPI Web Server & WebSocket Streaming
│   └── app.py                # REST endpoints & live WS stream (/ws/investigate)
├── benchmark/                # 20-Case Benchmark Suite
│   ├── runner.py             # Evaluation harness
│   ├── real_dataset.json     # Indexed IEEE-CIS evaluation cases & subgraphs
│   └── benchmark_results.json# Live evaluation metrics & confusion matrix
├── frontend/                 # React 18 Analyst Dashboard
│   └── index.html            # Dark-theme UI with 3-hop SVG graph & SAR viewer
├── gsql/                     # TigerGraph GSQL Queries
│   ├── detect_structuring.gsql
│   ├── detect_fraud_ring.gsql
│   ├── get_3hop_subgraph.gsql
│   └── install_queries.py
├── reports/                  # Regulatory Compliance
│   └── sar_generator.py      # Official FinCEN SAR document generator
├── setup/                    # Schema & Ingestion
│   ├── 01_create_schema.py   # TigerGraph vertex/edge schema
│   ├── 02_load_data.py       # PyTigerGraph loader
│   └── 03_load_csv_datasets.py # IEEE-CIS CSV dataset indexer
└── tests/
    └── test_all_phases.py    # Complete automated unit test suite (7/7 passed)
```

---

## ⚖️ License & Acknowledgements
Built for the **TigerGraph Hackathon (HHGOA)**. Dataset derived from the **IEEE-CIS Fraud Detection** dataset (Vesta Corporation).
