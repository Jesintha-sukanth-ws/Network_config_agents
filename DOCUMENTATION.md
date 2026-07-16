# Network Orchestration System - Complete Documentation

### Purpose
This is a **ServiceNow-integrated, AI-driven network automation platform** that converts high-level change requests into executed network configurations. It bridges ITSM workflows (ServiceNow) with network device management by using Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) to intelligently transform user intent into vendor-specific device configurations.

### Key Features
- **Natural Language Intent Processing**: LLM-based parsing of change descriptions into structured workflows
- **Intelligent Dependency Resolution**: Automatic topological sorting of configuration steps
- **Multi-Vendor Support**: Cisco IOS-XE, NX-OS, and extensible to other vendors
- **RAG-Powered Configuration**: Semantic search of device documentation for accurate payloads
- **State Validation**: Pre- and post-execution verification against live device state
- **ServiceNow Integration**: Bi-directional sync with Change Requests and Tasks
- **Audit Trail**: Comprehensive tracking of all changes with before/after state diffs
- **Real-time Dashboard**: Web UI for monitoring automation tasks

### Tech Stack
- **Framework**: FastAPI (Python web framework with async support)
- **LLM Engine**: Ollama (local model inference for privacy & speed)
- **Vector Database**: ChromaDB (semantic search over device documentation)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **ITSM Integration**: ServiceNow REST API
- **Network Protocols**: RESTCONF (preferred), NX-API (fallback)
- **Data Processing**: Pandas, OpenPyXL (Excel parsing)

---

## Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICENOW (ITSM)                            │
│              Tasks (SCTASK) + Change Requests (CHG)             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  POLLING SERVICE             │
        │  • Fetch open tasks          │
        │  • Parse Excel attachments   │
        │  • Enrich device data        │
        └──────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │  ORCHESTRATOR SERVICE        │
        │  4-Stage Pipeline:           │
        │  1. Plan (LLM intent)        │
        │  2. Prepare (state + RAG)    │
        │  3. Implement (config push)  │
        │  4. Verify (state check)     │
        └──────────┬───────────────────┘
                   │
        ┌──────────┴─────────────────────────────┐
        │                                        │
        ▼                                        ▼
    ┌──────────────────────┐         ┌──────────────────────┐
    │  INTENT SERVICE      │         │  DEPENDENCY PLANNER  │
    │  • LLM parsing       │         │  • Topo sort steps   │
    │  • Schema validate   │         │  • Capability graph  │
    │  • Extract workflow  │         │  • Circular dep check│
    └──────────┬───────────┘         └──────────┬───────────┘
               │                                 │
               └────────────┬────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  PAYLOAD GENERATION SERVICE   │
            │  • RAG retrieval (ChromaDB)   │
            │  • LLM payload generation    │
            │  • Parameter substitution    │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  CONFIG EXECUTION             │
            │  • RESTCONF/NX-API requests   │
            │  • Device authentication      │
            │  • Push to network devices    │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  EXECUTION VERIFICATION       │
            │  • Poll device state          │
            │  • Verify changes applied     │
            │  • Generate before/after diff │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  LIFECYCLE TRACKING           │
            │  • Update CR state machine    │
            │  • Generate work notes        │
            │  • Persist tracking data      │
            └───────────────────────────────┘
```

### Component Interaction Map

| Component | Responsibility | Key Dependencies |
|-----------|-----------------|------------------|
| **Polling Service** | Fetch and enrich tasks | ServiceNow API, Excel parser |
| **Intent Service** | Parse natural language → workflow | LLM (Ollama), Intent Registry |
| **Orchestrator** | Coordinate 4-stage pipeline | All services below |
| **Dependency Planner** | Resolve step order | Intent Registry schemas |
| **State Validator** | Verify device state matches intent | Device State Service |
| **Device State Service** | Query live device state | RESTCONF/NX-API |
| **RAG System** | Retrieve operation documentation | ChromaDB, Embeddings |
| **Payload Generation** | Create device payloads | LLM, RAG, Intent Registry |
| **Config Executor** | Push payloads to devices | RESTCONF/NX-API clients |
| **Status Verifier** | Confirm changes applied | RESTCONF/NX-API queries |
| **Lifecycle Agent** | Manage CR state machine | ServiceNow API, Narrative Service |
| **Narrative Service** | Generate audit trail work notes | LLM, Context |
| **Dashboard** | Real-time metrics & history | Tracking database, State Service |

---

## Installation & Setup

### Prerequisites
- Python 3.9+
- Ollama running locally (port 11434)
- Network access to ServiceNow instance
- Network access to target devices (RESTCONF/NX-API)
- Device credentials (SSH not required, uses HTTP APIs)

### Step 1: Clone & Environment Setup
```bash
# Clone repository
git clone <repo-url>
cd <project-directory>

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Create `.env` file in project root:

```bash
# ServiceNow Configuration
SERVICENOW_INSTANCE=https://dev123456.service-now.com/
SERVICENOW_USERNAME=your_username
SERVICENOW_PASSWORD=your_password
SERVICENOW_TIMEOUT=30
SERVICENOW_SSL_VERIFY=0  # Set to 1 for prod

# Device Credentials (Cisco example)
CISCO_USERNAME=admin
CISCO_PASSWORD=password123

# Ollama LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=180

# Model Selection
INTENT_MODEL=gpt-oss:120b-cloud              # Intent extraction
PAYLOAD_MODEL=qwen2.5:7b                      # Payload generation
SERVICENOW_FIELDS_MODEL=nemotron-3-ultra:cloud  # Field extraction

# RAG Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu  # or 'cuda' for GPU
RETRIEVAL_TOP_K=5
RAG_DISTANCE_THRESHOLD=1.5

# Execution Configuration
DEVICE_TIMEOUT=30
POLL_INTERVAL=30
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Advanced
NETWORK_GROUP_ID=<sys_id>  # ServiceNow group ID for filtering
TEST_MODE_QUERY=false       # Set true to bypass approval filters
LOG_LEVEL=INFO
DEVICE_DEBUG=0
```

### Step 3: Prepare Ollama Models
```bash
# Ensure models are available locally
ollama pull gpt-oss:120b-cloud
ollama pull qwen2.5:7b
ollama pull nemotron-3-ultra:cloud
ollama pull mistral:latest  # Fallback
```

### Step 4: Initialize Data Directories
```bash
# Creates data/chroma, data/logs, data/documents
python -c "from config.settings import *; print('Directories initialized')"
```

### Step 5: Ingest Device Documentation
```bash
# Add vendor documentation PDFs to data/documents/
# Then run ingestion
python ingest_documents.py
```

This populates ChromaDB with device-specific operation documentation.

### Step 6: Start Application
```bash
# Development (with auto-reload)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production (no reload, multi-worker)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

App starts polling ServiceNow immediately in background thread.

---

## Configuration

### Environment Variables Reference

**ServiceNow Settings:**
- `SERVICENOW_INSTANCE`: Full URL of ServiceNow instance (with trailing slash)
- `SERVICENOW_USERNAME`: Service account username with task/CR permissions
- `SERVICENOW_PASSWORD`: Service account password
- `SERVICENOW_TIMEOUT`: HTTP request timeout (seconds)
- `SERVICENOW_SSL_VERIFY`: 1 for HTTPS validation, 0 to disable
- `NETWORK_GROUP_ID`: Sys ID of "Network" assignment group (filters tasks to network team)
- `TEST_MODE_QUERY`: Set to 'true' to retrieve ALL open tasks regardless of approval state

**Device Configuration:**
- `DEVICE_TIMEOUT`: Timeout for device API calls (seconds)
- `DEVICE_CREDENTIALS`: Per-vendor credentials (Cisco in example, extend for others)
  - `CISCO_USERNAME` / `CISCO_PASSWORD`
  - `JUNIPER_USERNAME` / `JUNIPER_PASSWORD` (if supported)

**LLM Settings:**
- `OLLAMA_BASE_URL`: Ollama server endpoint (default: http://localhost:11434)
- `OLLAMA_TIMEOUT`: LLM inference timeout (seconds, default: 180)
- `INTENT_MODEL`: Model for extracting intent from task description
- `PAYLOAD_MODEL`: Model for generating device-specific payloads
- `SERVICENOW_FIELDS_MODEL`: Model for extracting ServiceNow CR field values
- `LLM_TEMPERATURE`: Sampling temperature (0-1, default: 0.1 for deterministic)
- `LLM_MAX_TOKENS`: Max tokens per LLM response (default: 1024)

**RAG Settings:**
- `EMBEDDING_MODEL`: Sentence-transformer model for doc embeddings
- `EMBEDDING_DEVICE`: CPU or CUDA for embedding inference
- `CHUNK_SIZE`: Document chunk size (default: 1000 chars)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200 chars)
- `RETRIEVAL_TOP_K`: Number of docs to retrieve (default: 5)
- `RAG_DISTANCE_THRESHOLD`: Cosine distance threshold for relevance (default: 1.5)

**Execution Settings:**
- `POLL_INTERVAL`: How often to check ServiceNow (seconds, default: 30)
- `MAX_CONTEXT_CHARS`: Max chars for RAG context in LLM prompt (default: 4000)
- `INGEST_BATCH_SIZE`: Batch size for document ingestion (default: 32)
- `LOG_LEVEL`: Python logging level (DEBUG, INFO, WARNING, ERROR)
- `DEVICE_DEBUG`: Set to 1 for verbose device API logging

### Device Capabilities Configuration

File: `app/devices/device_capabilities.json`

Defines vendor-specific capabilities and protocols:
```json
{
  "Cisco": {
    "IOS-XE": {
      "preferred_connection": "restconf",
      "default_port": 443,
      "yang_modules": ["Cisco-IOS-XE-native", "ietf-interfaces"],
      "state_endpoints": {"/data/Cisco-IOS-XE-native:native/interface"},
      "state_commands": ["show version", "show interfaces", "show vlan"]
    },
    "NX-OS": {
      "preferred_connection": "nxapi",
      "default_port": 8080,
      "api_path": "/ins",
      "state_endpoints": ["/stats/vlan"],
      "state_commands": ["show vlan", "show interface"]
    }
  }
}
```

Extend for new vendors by adding vendor + OS entries.

### Intent Registry Configuration

File: `app/registry/intent_registry.py`

Defines canonical operations and their schemas:
```python
CANONICAL_INTENT_SCHEMAS = {
    "create_vlan": {
        "description": "Provision a new VLAN",
        "required_parameters": ["vlan_id"],
        "optional_parameters": ["name"],
        "parameter_types": {"vlan_id": int, "name": str},
        "requires": [],  # Prerequisites
        "provides": ["vlan_exists:{vlan_id}"],  # Capabilities provided
        "sop_payload_contract": {"vlan_id": "", "vlan_name": ""}
    }
}
```

New intents must be registered here with dependency metadata.

---

## Core Components

### 1. Polling Service (`app/services/polling_service.py`)

**Purpose**: Long-running background thread that fetches open tasks from ServiceNow and routes them through orchestration.

**Key Functions:**
- `poll_servicenow(stop_event)`: Main loop, runs every POLL_INTERVAL seconds
- `get_next_open_task()`: Query for open, approved tasks
- `enrich_task_with_excel()`: Download & parse Excel attachment for device data
- `_normalize_os_type()`: Normalize OS strings ("Cisco IOS-XE 17.15" → "IOS-XE")
- `_map_excel_row_to_device_data()`: Extract device info from Excel columns

**Column Aliases Supported:**
- Device: device_name, hostname, name, device
- Vendor: vendor, manufacturer, make
- OS: os_type, os, operating_system, platform
- IP: management_host, mgmt_host, management_ip, ip_address, fqdn, host
- Credentials: username, user, login; password, pass, secret

**Flow:**
```
Query ServiceNow every 30s
  ↓
For each open task:
  ├─ Download Excel from task attachment
  ├─ Extract device data (vendor, OS, IP, credentials)
  ├─ Call CRLifecycleAgent.initialize_lifecycle(task)
  └─ Task marked as WIP (state: 2)
```

### 2. Intent Service (`app/services/intent_service.py`)

**Purpose**: Parse natural language task descriptions into structured workflow steps using LLM.

**Key Methods:**
- `parse(description: str) → List[Dict]`: Extract workflow from text
  - Returns: List of {intent_type, parameters, rag_type}
- Validates intent names against CANONICAL_INTENT_SCHEMAS
- Maps aliases (e.g., "add_vlan" → "create_vlan")
- Type-checks parameters (int, str, bool, etc.)

**Example Input/Output:**
```
Input:  "Create VLAN 100 named 'Production' and add Gi1/0/5 to it"

LLM Call:
  Model: INTENT_MODEL (gpt-oss:120b-cloud)
  System Prompt: [schema definitions]
  User Prompt: [task description]

Output: [
  {
    "intent_type": "create_vlan",
    "parameters": {"vlan_id": 100, "name": "Production"},
    "rag_type": "create_vlan"
  },
  {
    "intent_type": "configure_access_port",
    "parameters": {"interface": "Gi1/0/5", "vlan_id": 100},
    "rag_type": "configure_access_port"
  }
]
```

### 3. Orchestrator Service (`app/services/orchestrator_service.py`)

**Purpose**: Coordinates the entire 4-stage automation pipeline.

**4-Stage Pipeline:**

**Stage 1: PLAN**
```python
plan_task(task)
  ├─ IntentService.parse()
  │  └─ LLM extracts workflow steps
  ├─ SchemaValidator.validate()
  │  └─ Canonical names, required params, types
  ├─ WorkflowValidator.validate()
  │  └─ Device-level constraints (VLAN ranges, interface names)
  └─ Return: ordered_workflow[]
```

**Stage 2: PREPARE**
```python
prepare_change(device, ordered_workflow)
  ├─ DeviceStateService.get_device_state(device)
  │  ├─ Query device facts (vendor, OS, version)
  │  ├─ Get current VLANs (RESTCONF GET)
  │  └─ Get interfaces (RESTCONF GET)
  ├─ DependencyPlanner.plan(workflow, state)
  │  ├─ Extract state capabilities
  │  ├─ Build dependency graph
  │  ├─ Topological sort steps
  │  └─ Detect cycles & unsatisfied deps
  ├─ StateValidator.validate_state()
  │  └─ Ensure all step prerequisites met
  └─ Return: execution_plan[]
```

**Stage 3: IMPLEMENT**
```python
implement_change(execution_plan, device)
  └─ For each step:
     ├─ PayloadGenerationService.generate()
     │  ├─ RAG retrieval (vendor docs)
     │  ├─ LLM payload generation
     │  └─ JSON validation
     ├─ PushConfigExecutor.execute()
     │  ├─ Build RESTCONF/NX-API request
     │  ├─ Send to device
     │  └─ Track response
     └─ Record step result
```

**Stage 4: VERIFY**
```python
verify_change(device, execution_plan)
  └─ ExecutionStatusVerifier.verify()
     ├─ Poll device state (post-change)
     ├─ Compare with expected state
     ├─ Generate before/after diff
     └─ Return success/failure
```

### 4. Dependency Planner (`app/workflow/dependency_planner.py`)

**Purpose**: Automatically determine execution order based on capability dependencies.

**Core Algorithm:**
```
1. Extract Capabilities from Current State
   state: {vlans: [10, 20], interfaces: {Gi1/0/1, Gi1/0/5}}
   capabilities: {vlan_exists:10, vlan_exists:20, interface_exists:Gi1/0/1, ...}

2. Parse Step Requires/Provides
   Step 1: create_vlan(100)
     requires: []
     provides: [vlan_exists:100]
   
   Step 2: configure_access_port(Gi1/0/5, 100)
     requires: [vlan_exists:100]
     provides: [interface_config:Gi1/0/5]

3. Build Dependency Graph
   Step 1 → Step 2  (Step 2 depends on Step 1)

4. Topological Sort
   ordered: [Step 1, Step 2]

5. Detect Issues
   - Missing required capabilities? ERROR
   - Circular dependencies? ERROR
   - All ok? SUCCESS
```

**Returns:**
```python
{
    "valid": True/False,
    "ordered_workflow": List[Dict],       # Sorted steps
    "dependency_graph": Dict,              # Adjacency map
    "provided_capabilities": Set[str],     # All capabilities
    "errors": List[Dict],                  # Validation errors
    "reordered": bool                      # Whether order changed
}
```

### 5. Device State Service (`app/devices/device_state_service.py`)

**Purpose**: Query live device state via RESTCONF/NX-API.

**Key Methods:**
- `get_device_state(connection)`: Returns {device_info, vlans, interfaces}
- `get_vlans(connection)`: RESTCONF GET /data/Cisco-IOS-XE-native:native/vlan
- `get_interfaces(connection)`: RESTCONF GET /data/Cisco-IOS-XE-native:native/interface

**Example Response:**
```python
{
    "device_info": {
        "vendor": "Cisco",
        "os": "IOS-XE",
        "version": "17.15.01",
        "hostname": "router-1"
    },
    "vlans": {
        "10": {"name": "Management"},
        "20": {"name": "Users"},
        "100": {"name": "Production"}
    },
    "interfaces": {
        "Gi1/0/1": {"mode": "access", "access_vlan": 10},
        "Gi1/0/5": {"mode": "access", "access_vlan": 20}
    }
}
```

### 6. Payload Generation Service (`app/llm/payload_generation_service.py`)

**Purpose**: Use LLM + RAG to generate device-specific payloads.

**Flow:**
```
Input:
  - intent_type: "configure_access_port"
  - parameters: {interface: "Gi1/0/5", vlan_id: 100}
  - device: {vendor: "Cisco", os: "IOS-XE", version: "17.15.01"}

Step 1: RAG Retrieval
  - Query: "Cisco IOS-XE configure_access_port"
  - RetrievalService searches ChromaDB
  - Returns: Top 5 doc chunks (~2000 chars) with YANG/API examples

Step 2: Build Prompt
  - System: [payload generation instructions]
  - User: [intent + parameters + device + RAG context]

Step 3: LLM Inference
  - Model: PAYLOAD_MODEL (qwen2.5:7b)
  - Generate: JSON payload

Step 4: Validate & Return
  - Validate JSON structure
  - Confirm all params substituted
  - Return: {operation: "configure_access_port", payload: {...}}

Output:
  {
    "operation": "configure_access_port",
    "payload": {
      "interface": "Gi1/0/5",
      "vlan_id": 100,
      "mode": "access"
    }
  }
```

### 7. RAG System (`app/rag/`)

**Components:**

- **ChromaManager**: Vector DB management
  - Collections: cisco_iosxe, cisco_nxos (per vendor/OS)
  - Operations: upsert (insert/update), query, clear
  
- **EmbeddingService**: Vector encoding
  - Model: sentence-transformers/all-MiniLM-L6-v2
  - Normalizes embeddings for cosine distance
  
- **IngestionService**: Document processing
  - Reads PDFs from `data/documents/`
  - Chunks with configurable overlap
  - Generates embeddings
  - Stores in ChromaDB
  
- **RetrievalService**: Semantic search
  - Query by intent + vendor + OS
  - Returns top-K chunks by cosine distance
  - Optional distance threshold filtering

**Workflow:**
```
Documents/
  ├─ Cisco_IOS-XE_Config_Guide.pdf
  └─ Cisco_NX-OS_RESTCONF_API.pdf

→ DocumentParser (extract text)
→ ChunkingService (split into chunks)
→ EmbeddingService (create vectors)
→ ChromaManager.upsert()
   └─ Store in collection: cisco_iosxe

Later, at runtime:
  Query: "Cisco IOS-XE configure_access_port"
  → EmbeddingService.embed_query() [768-dim vector]
  → ChromaManager.query() [cosine distance search]
  → Returns top-5 chunks sorted by relevance
```

### 8. Lifecycle Agent (`app/services/cr_lifecycle_agent.py`)

**Purpose**: Manage ServiceNow Change Request state machine.

**CR State Machine:**
```
-4 (Assess)      Initial state after CR creation
  ↓ (waiting for approval)
-3 (Authorize)   CR approved by management
  ↓ (post approval narrative)
-2 (Scheduled)   Change window reached
  ↓ (auto-advance)
-1 (Implement)   Executing on devices
  ↓ (apply config)
 0 (Complete)    Success or 4 (Incomplete) if failed
```

**Key Methods:**
- `initialize_lifecycle(task)`: Create CR from task
- `reconcile_active_changes()`: Poll CR state & advance stages
- `create_change_request(task)`: POST to ServiceNow
- `post_approval_narrative(cr_id, narrative)`: Work notes
- `close_change_request(cr_id, success)`: Final state

### 9. Validation Services

**SchemaValidator** (`app/validation/schema_validator.py`)
- Validates intent names are canonical
- Checks required parameters present
- Verifies parameter types (int, str, bool)
- Maps aliases to canonical names

**WorkflowValidator** (`app/network_validation/workflow_validator.py`)
- VLAN parameter bounds (1-4094)
- Interface name format (Gi1/0/1, etc.)
- Device-specific constraints

**StateValidator** (`app/network_validation/state_validator.py`)
- Checks device state matches workflow requires[]
- Prevents operating on non-existent VLANs
- Validates interface exists before config

---

## API Endpoints

### Health & Status

**GET /health**
```
Response: {
  "status": "online",
  "services": {
    "api": "healthy",
    "orchestrator": "healthy",
    "polling": "running"
  }
}
```

### Task Execution

**POST /tasks/execute**
```
Request: {
  "device": {
    "vendor": "Cisco",
    "os_type": "IOS-XE",
    "management_host": "192.168.1.1",
    "credentials": {"username": "admin", "password": "pass"}
  },
  "short_description": "Create VLAN",
  "description": "Create VLAN 100 named Production"
}

Response: {
  "task_id": "sctask-12345",
  "status": "success",
  "workflow": [...],
  "state_before": {...},
  "state_after": {...}
}
```

### Dashboard API

**GET /dashboard/api/active**
Current task in progress
```
Response: {
  "sctask": "SCTASK0012345",
  "cr_id": "CHG0067890",
  "stage": "Implement",
  "started_at": "2024-01-15T10:30:00Z",
  "workflow": [...]
}
```

**GET /dashboard/api/history**
All completed tasks
```
Response: {
  "tasks": [
    {
      "sctask": "SCTASK0012345",
      "cr_id": "CHG0067890",
      "status": "Complete",
      "completed_at": "2024-01-15T11:45:00Z",
      "duration_seconds": 4500,
      "success_count": 2,
      "failure_count": 0
    }
  ]
}
```

**GET /dashboard/api/history/{sctask}**
Detailed task history
```
Response: {
  "sctask": "SCTASK0012345",
  "cr_id": "CHG0067890",
  "stages": [
    {"stage": "Plan", "status": "Complete", "duration": 120},
    {"stage": "Prepare", "status": "Complete", "duration": 240},
    {"stage": "Implement", "status": "Complete", "duration": 300}
  ],
  "state_diff": {
    "before": {"vlans": [10, 20]},
    "after": {"vlans": [10, 20, 100]}
  }
}
```

**GET /dashboard/api/metrics**
Automation metrics
```
Response: {
  "total_tasks": 45,
  "successful": 42,
  "failed": 3,
  "success_rate": 93.3,
  "avg_duration_seconds": 360,
  "most_common_intent": "create_vlan"
}
```

**GET /dashboard/api/pipeline/{sctask}**
Task stage progression
```
Response: {
  "sctask": "SCTASK0012345",
  "pipeline": [
    {"stage": "Plan", "status": "Complete", "timestamp": "..."},
    {"stage": "Prepare", "status": "Complete", "timestamp": "..."},
    {"stage": "Implement", "status": "In Progress", "timestamp": "..."}
  ]
}
```

**GET /dashboard/api/state-diff/{sctask}**
Before/after configuration diff
```
Response: {
  "device": "router-1",
  "before": {
    "vlans": ["10", "20"],
    "interfaces": {"Gi1/0/1": {mode: "access", vlan: 10}}
  },
  "after": {
    "vlans": ["10", "20", "100"],
    "interfaces": {"Gi1/0/1": {mode: "access", vlan: 10}}
  },
  "changes": [
    "Added VLAN 100"
  ]
}
```

---

## Workflows

### Complete Task Execution Flow

```
1. USER SUBMITS TASK IN SERVICENOW
   ├─ Create SCTASK
   ├─ Attach Excel with device data
   ├─ Submit for approval
   └─ Task State: 1 (Open)

2. POLLING SERVICE DISCOVERS TASK
   every 30 seconds:
   ├─ Query: state=1, approval=approved, assignment_group=NETWORK_GROUP_ID
   ├─ Download Excel attachment
   ├─ Extract device: {vendor: Cisco, os: IOS-XE, ip: 10.1.1.1}
   ├─ Task State → 2 (Work in Progress)
   └─ Call CRLifecycleAgent.initialize_lifecycle(task)

3. LIFECYCLE AGENT INITIALIZES
   ├─ Create Change Request (CR) in ServiceNow
   │  └─ CR State: -4 (Assess)
   ├─ Begin reconcile_active_changes() loop
   └─ Track in cr_tracking.json

4. ORCHESTRATOR STAGE 1: PLAN
   plan_task(task):
   ├─ IntentService.parse("Create VLAN 100")
   │  └─ LLM Call (INTENT_MODEL):
   │     Input: task description
   │     Output: [{intent_type: create_vlan, parameters: {vlan_id: 100}}]
   ├─ SchemaValidator.validate()
   │  └─ Check: create_vlan is canonical, vlan_id is int
   ├─ WorkflowValidator.validate()
   │  └─ Check: vlan_id 1-4094 range
   └─ Return: workflow = [{intent_type: create_vlan, ...}]

5. ORCHESTRATOR STAGE 2: PREPARE
   prepare_change():
   ├─ ConnectionService.connect(device)
   │  └─ Load device_capabilities.json → Cisco/IOS-XE/RESTCONF
   ├─ DeviceStateService.get_device_state()
   │  ├─ RESTCONF GET /api/v1/device/facts
   │  │  └─ vendor=Cisco, os=IOS-XE, version=17.15
   │  ├─ RESTCONF GET .../native/vlan
   │  │  └─ existing_vlans: [10, 20, 30]
   │  └─ RESTCONF GET .../native/interface
   │     └─ interfaces: {Gi1/0/1, Gi1/0/5, ...}
   ├─ DependencyPlanner.plan()
   │  ├─ Current capabilities: {vlan_exists:10, vlan_exists:20, ...}
   │  ├─ Step needs: create_vlan(100)
   │  │  requires: []
   │  │  provides: [vlan_exists:100]
   │  ├─ All requires[] satisfied? YES
   │  └─ Ordered workflow: [create_vlan(100)]
   ├─ StateValidator.validate()
   │  └─ All step prerequisites available? YES
   └─ Return: execution_plan ready

6. ORCHESTRATOR STAGE 3: IMPLEMENT
   implement_change():
   
   For step in execution_plan (create_vlan):
   ├─ PayloadGenerationService.generate()
   │  ├─ RetrievalService.retrieve()
   │  │  ├─ Query: "Cisco IOS-XE create_vlan"
   │  │  ├─ ChromaDB semantic search
   │  │  └─ Return: 5 doc chunks (Cisco VLAN config examples)
   │  ├─ Build prompt:
   │  │  System: "Generate Cisco IOS-XE RESTCONF payload..."
   │  │  User: "Create VLAN 100. Device: Cisco IOS-XE 17.15"
   │  │  Context: [RAG docs]
   │  ├─ LLM Call (PAYLOAD_MODEL):
   │  │  └─ Return JSON: {
   │  │       "operation": "create_vlan",
   │  │       "payload": {
   │  │         "vlan_id": 100,
   │  │         "vlan_name": "VLAN_100"
   │  │       }
   │  │     }
   │  └─ Validate JSON structure
   │
   ├─ PushConfigExecutor.execute(payload)
   │  ├─ Build RESTCONF request:
   │  │  PATCH /restconf/data/Cisco-IOS-XE-native:native/vlan
   │  │  Authorization: Basic admin:pass
   │  │  Body: {Cisco-IOS-XE-native:vlan: {vlan-id: [{id: 100}]}}
   │  ├─ Send to device 10.1.1.1:443
   │  └─ Response: 204 No Content (success)
   │
   └─ Record: {step: create_vlan, status: success, timestamp: ...}

7. ORCHESTRATOR STAGE 4: VERIFY
   verify_change():
   ├─ ExecutionStatusVerifier.verify()
   │  ├─ RESTCONF GET .../native/vlan
   │  │  └─ New state: [10, 20, 30, 100]
   │  ├─ Compare with expected: 100 present? YES
   │  └─ Generate diff: {before: [...], after: [...], added: [100]}
   └─ All verifications passed? YES

8. LIFECYCLE AGENT: CR STATE PROGRESSION
   reconcile_active_changes() loop:
   ├─ CR State -4 (Assess):
   │  ├─ Wait for approval (manual in ServiceNow)
   │  └─ Loop until -3
   ├─ CR State -3 (Authorize):
   │  ├─ Post approval narrative:
   │  │  "Workflow: [create_vlan]. Parameters: {vlan_id: 100}"
   │  ├─ Request approval from management
   │  └─ Auto-advance on approval
   ├─ CR State -2 (Scheduled):
   │  ├─ Scheduled window reached?
   │  ├─ Auto-advance → -1
   │  └─ Call implement_change()
   ├─ CR State -1 (Implement):
   │  ├─ Execution complete
   │  └─ Auto-advance → 0 (Complete)
   └─ CR State 0 (Complete):
      ├─ Update SCTASK state → 3 (Complete)
      ├─ Append completion narrative
      └─ End reconciliation

9. FINAL STATE
   ├─ SCTASK State: 3 (Complete)
   ├─ CR State: 0 (Complete)
   ├─ Task tracking persisted: cr_tracking.json
   ├─ Dashboard shows:
   │  ├─ Execution timeline
   │  ├─ Before/after state diff
   │  └─ Audit trail with work notes
   └─ Polling continues for next task
```

### Error Handling Flow

```
If validation fails:
  ├─ SchemaValidator error
  │  └─ Canonical intent not found → ABORT
  ├─ WorkflowValidator error
  │  └─ Parameter out of range → ABORT
  └─ Task marked Incomplete (state: 4)

If device unreachable:
  ├─ ConnectionService fails
  │  └─ Retry with exponential backoff (3 attempts)
  ├─ All retries exhausted
  └─ Task marked Incomplete, CR moved to "On Hold"

If LLM service offline:
  ├─ OllamaClient.generate() timeout
  │  └─ Fallback to previous model or cached response
  ├─ If no fallback available
  └─ Task marked Incomplete, operations queued for retry

If device state change fails:
  ├─ PushConfigExecutor gets 4xx/5xx response
  │  └─ Capture error, log to work notes
  ├─ Skip to next step or abort
  └─ CR state may be set to "On Hold" pending manual review
```

---

## Data Models

### Task Model (SCTASK from ServiceNow)

```python
{
    "number": "SCTASK0012345",
    "short_description": "Configure VLAN on access port",
    "description": "Create VLAN 100 and add interface Gi1/0/5",
    "state": 1,  # 1=Open, 2=WIP, 3=Complete, 4=Incomplete
    "approval": "approved",
    "assignment_group": "sys_id_of_network_team",
    "attachments": [
        {
            "filename": "device_data.xlsx",
            "file_id": "attachment_12345",
            "mime_type": "application/vnd.ms-excel"
        }
    ]
}
```

### Device Model (from Excel enrichment)

```python
{
    "device_name": "router-1",
    "vendor": "Cisco",
    "os_type": "IOS-XE",
    "model_number": "ASR 1001-X",
    "management_host": "10.1.1.1",
    "credentials": {
        "username": "admin",
        "password": "password123"
    }
}
```

### Intent Model (from LLM parsing)

```python
{
    "intent_type": "configure_access_port",  # Canonical name
    "parameters": {
        "interface": "Gi1/0/5",
        "vlan_id": 100
    },
    "rag_type": "configure_access_port"      # RAG lookup key
}
```

### Device State Model (from RESTCONF queries)

```python
{
    "device_info": {
        "vendor": "Cisco",
        "os": "IOS-XE",
        "version": "17.15.01",
        "hostname": "router-1",
        "serial_number": "ABC123456"
    },
    "vlans": {
        "10": {"name": "Management", "status": "active"},
        "20": {"name": "Users", "status": "active"},
        "100": {"name": "Production", "status": "active"}
    },
    "interfaces": {
        "Gi1/0/1": {
            "description": "Uplink",
            "mode": "trunk",
            "allowed_vlans": [10, 20, 100]
        },
        "Gi1/0/5": {
            "description": "Access port",
            "mode": "access",
            "access_vlan": 100,
            "status": "up"
        }
    }
}
```

### Execution Plan Model (from Dependency Planner)

```python
{
    "valid": True,
    "ordered_workflow": [
        {
            "index": 0,
            "intent_type": "create_vlan",
            "parameters": {"vlan_id": 100},
            "requires": [],
            "provides": ["vlan_exists:100"],
            "dependencies": []
        },
        {
            "index": 1,
            "intent_type": "configure_access_port",
            "parameters": {"interface": "Gi1/0/5", "vlan_id": 100},
            "requires": ["vlan_exists:100"],
            "provides": ["interface_configured:Gi1/0/5"],
            "dependencies": [0]  # depends on step 0
        }
    ],
    "dependency_graph": {
        0: [],
        1: [0]
    },
    "provided_capabilities": {
        "vlan_exists:10",
        "vlan_exists:20",
        "vlan_exists:100",
        "interface_configured:Gi1/0/5"
    },
    "errors": [],
    "reordered": False
}
```

### Payload Model (from LLM generation)

```python
{
    "operation": "configure_access_port",
    "payload": {
        "interface": "Gi1/0/5",
        "mode": "access",
        "vlan_id": 100,
        "description": "Production VLAN"
    },
    "restconf_path": "/restconf/data/Cisco-IOS-XE-native:native/interface/GigabitEthernet=1%2F0%2F5",
    "http_method": "PATCH"
}
```

### Change Request Model (CHG from ServiceNow)

```python
{
    "number": "CHG0067890",
    "task_id": "SCTASK0012345",
    "state": -1,  # -4=Assess, -3=Authorize, -2=Scheduled, -1=Implement, 0=Complete
    "description": "Configure VLAN on router-1",
    "implementation_plan": "...",
    "workflow_steps": 2,
    "created_at": "2024-01-15T10:30:00Z",
    "started_at": "2024-01-15T10:45:00Z",
    "completed_at": null,
    "work_notes": [
        {
            "timestamp": "2024-01-15T10:45:00Z",
            "note": "Workflow: [create_vlan, configure_access_port]"
        },
        {
            "timestamp": "2024-01-15T10:47:30Z",
            "note": "CR approved. Moving to Implement."
        }
    ]
}
```

### Tracking Data Model (cr_tracking.json)

```python
{
    "sctask_12345": {
        "sctask": "SCTASK0012345",
        "cr_id": "CHG0067890",
        "device": {
            "vendor": "Cisco",
            "os": "IOS-XE",
            "ip": "10.1.1.1"
        },
        "workflow": [
            {
                "intent": "create_vlan",
                "parameters": {"vlan_id": 100},
                "status": "success"
            },
            {
                "intent": "configure_access_port",
                "parameters": {"interface": "Gi1/0/5", "vlan_id": 100},
                "status": "success"
            }
        ],
        "state_before": {
            "vlans": ["10", "20"],
            "interfaces": {"Gi1/0/5": {"vlan": 20}}
        },
        "state_after": {
            "vlans": ["10", "20", "100"],
            "interfaces": {"Gi1/0/5": {"vlan": 100}}
        },
        "timestamps": {
            "created": "2024-01-15T10:30:00Z",
            "plan_completed": "2024-01-15T10:32:00Z",
            "prepare_completed": "2024-01-15T10:35:00Z",
            "implement_completed": "2024-01-15T10:48:00Z",
            "verify_completed": "2024-01-15T10:49:00Z"
        },
        "total_duration_seconds": 1140,
        "success": True
    }
}
```

---

## Troubleshooting

### Common Issues

**Issue 1: "Ollama service unreachable"**
```
Error: httpx.ConnectError: Unable to connect to http://localhost:11434

Solution:
1. Verify Ollama is running: ollama serve
2. Check port 11434 is open: netstat -an | grep 11434
3. Verify OLLAMA_BASE_URL in .env matches
4. Try: curl http://localhost:11434/api/version
```

**Issue 2: "Model not found in Ollama"**
```
Error: RuntimeError: Ollama inference failed: model 'gpt-oss:120b-cloud' not found

Solution:
1. List available models: ollama list
2. Pull missing model: ollama pull gpt-oss:120b-cloud
3. Verify model name matches exactly (case-sensitive)
4. Check disk space for model storage (~50GB for large models)
```

**Issue 3: "ServiceNow authentication failed"**
```
Error: 401 Unauthorized from SERVICENOW_INSTANCE

Solution:
1. Verify credentials: SERVICENOW_USERNAME, SERVICENOW_PASSWORD
2. Check user has ITIL admin role or equivalent
3. Verify SSL certificate (SERVICENOW_SSL_VERIFY=0 for dev)
4. Test manually: curl -u username:password https://instance.service-now.com/api/now/table/incident
```

**Issue 4: "Device connection refused"**
```
Error: RESTCONF connection refused to 10.1.1.1:443

Solution:
1. Verify device IP is correct and reachable: ping 10.1.1.1
2. Verify RESTCONF is enabled: show ip http server
3. Check device credentials are correct
4. Verify device certificate is valid (set DEVICE_SSL_VERIFY accordingly)
5. Ensure device supports RESTCONF (IOS-XE 16.12+, NX-OS 9.x+)
```

**Issue 5: "Intent not recognized"**
```
Error: SchemaValidator: 'add_vlna' not found in CANONICAL_INTENT_SCHEMAS

Solution:
1. Check spelling: did user mean 'add_vlan'?
2. Add alias in intent_registry.py:
   "aliases": ["add_vlna", "add_vlan", ...]
3. Rebuild alias map and restart app
```

**Issue 6: "Device capability not found"**
```
Error: ConnectionService: No capability for Cisco / Juniper-OS

Solution:
1. Verify vendor/OS in device_capabilities.json
2. Add new vendor entry:
   "Juniper": {
     "Juniper-OS": {
       "preferred_connection": "netconf",
       ...
     }
   }
3. Implement connection handler for new protocol
```

**Issue 7: "Dependency cycle detected"**
```
Error: DependencyPlanner: Circular dependency detected

Solution:
1. Review intent schemas:
   - Step A requires capability from Step B
   - Step B requires capability from Step A
2. Fix by:
   - Reordering workflow steps
   - Changing requires/provides declarations
   - Splitting one step into prerequisite steps
```

**Issue 8: "RAG retrieval returning irrelevant docs"**
```
Error: PayloadGenerationService: Generated payload is incorrect

Solution:
1. Increase RAG_DISTANCE_THRESHOLD to 2.0 (less strict)
2. Increase RETRIEVAL_TOP_K to 10 (more docs)
3. Verify documents are ingested: check data/chroma/ collection counts
4. Re-ingest documentation: python ingest_documents.py
5. Check document quality and relevance in source PDFs
```

### Debug Logging

**Enable verbose logging:**
```
.env:
LOG_LEVEL=DEBUG
DEVICE_DEBUG=1  # Extra device API logging
```

**Check logs:**
```
data/logs/app.log          # Application logs
data/logs/orchestrator.log # Orchestration pipeline logs
data/logs/device.log       # Device API logs
```

**Common debug commands:**
```bash
# Check ChromaDB collections
python -c "
from app.rag.chroma_manager import ChromaManager
mgr = ChromaManager()
for name, coll in mgr.collections.items():
    print(f'{name}: {coll.count()} docs')
"

# Test LLM connectivity
python -c "
from app.llm.ollama_client import OllamaClient
client = OllamaClient()
print(client.health_check())
"

# Test ServiceNow connectivity
python -c "
import requests
from config.settings import *
resp = requests.get(
    f'{SERVICENOW_INSTANCE}/api/now/table/sys_user',
    auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
    verify=SERVICENOW_SSL_VERIFY
)
print(resp.status_code)
"

# Test device connectivity
python -c "
from app.devices.device_state_service import DeviceStateService
from app.devices.connection_service import ConnectionService
svc = DeviceStateService(ConnectionService())
state = svc.get_device_state({
    'management_host': '10.1.1.1',
    'vendor': 'Cisco',
    'os_type': 'IOS-XE'
})
print(state['device_info'])
"
```

### Performance Tuning

**Slow LLM inference:**
```
.env:
- Reduce LLM_MAX_TOKENS (default 1024 → 512)
- Use faster model: PAYLOAD_MODEL=mistral:7b (vs qwen2.5:7b)
- Increase OLLAMA_TIMEOUT if needed (allow longer inference)
- Run on GPU: EMBEDDING_DEVICE=cuda, torch with CUDA support
```

**Slow RAG retrieval:**
```
.env:
- Reduce RETRIEVAL_TOP_K (5 → 3)
- Increase RAG_DISTANCE_THRESHOLD (1.5 → 2.0)
- Reduce CHUNK_SIZE (1000 → 500) for faster re-ingestion
- Verify ChromaDB performance: data/chroma/ size and index
```

**High memory usage:**
```
- Reduce INGEST_BATCH_SIZE (32 → 8) during ingestion
- Set EMBEDDING_DEVICE=cpu if GPU memory constrained
- Monitor with: ps aux | grep python
```

---

## Development Guide

### Project Structure

```
project_root/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── services/               # Business logic
│   │   ├── polling_service.py     # ServiceNow polling
│   │   ├── orchestrator_service.py # 4-stage pipeline
│   │   ├── intent_service.py      # LLM intent extraction
│   │   ├── cr_lifecycle_agent.py  # CR state machine
│   │   ├── itsm_narrative_service.py # Work note generation
│   │   └── display_service.py     # Terminal formatting
│   ├── llm/                    # LLM integration
│   │   ├── ollama_client.py       # Ollama wrapper
│   │   ├── payload_generation_service.py # Payload LLM
│   │   └── prompt_template.py     # LLM prompt builders
│   ├── rag/                    # Vector DB & retrieval
│   │   ├── chroma_manager.py      # ChromaDB wrapper
│   │   ├── embedding_service.py   # Vector encoding
│   │   ├── ingestion_service.py   # Document ingestion
│   │   ├── retrieval_service.py   # Semantic search
│   │   ├── document_parser.py     # PDF parsing
│   │   ├── chunking_service.py    # Text chunking
│   │   └── config.py              # RAG settings
│   ├── devices/                # Device management
│   │   ├── connection_service.py  # Connection resolve
│   │   ├── device_state_service.py # State queries
│   │   ├── device_capabilities.json # Vendor specs
│   │   └── __init__.py
│   ├── execution/              # Config execution
│   │   ├── push_config.py         # RESTCONF/NX-API
│   │   ├── execution_status.py    # Status verification
│   │   └── __init__.py
│   ├── network_validation/     # Intent validation
│   │   ├── base_validator.py      # Base class
│   │   ├── schema_validator.py    # Intent schema validation
│   │   ├── workflow_validator.py  # Workflow constraints
│   │   ├── state_validator.py     # Device state validation
│   │   ├── vlan_validator.py      # VLAN-specific rules
│   │   ├── interface_validator.py # Interface rules
│   │   └── __init__.py
│   ├── workflow/               # Dependency resolution
│   │   ├── dependency_planner.py  # Topo sort
│   │   └── __init__.py
│   ├── registry/               # Intent definitions
│   │   └── intent_registry.py     # CANONICAL_INTENT_SCHEMAS
│   ├── prompts/                # LLM prompts
│   │   ├── intent_prompt.py       # Intent extraction prompt
│   │   └── __init__.py
│   ├── dashboard/              # Web API
│   │   ├── routes.py              # /dashboard/* endpoints
│   │   └── __init__.py
│   ├── validation/             # Schema validation
│   │   └── schema_validator.py
│   └── utils/                  # Utilities
│       └── logger.py              # Custom logger
├── config/
│   └── settings.py             # Environment config
├── data/
│   ├── chroma/                 # ChromaDB vector store
│   ├── documents/              # Vendor documentation
│   ├── logs/                   # Application logs
│   ├── cr_tracking.json        # Task tracking
│   └── tracking/               # Archived tracking
├── ingest_documents.py         # Document ingestion script
├── start_dashboard.py          # Dashboard launcher
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── .env.example                # Environment template
├── README.md                   # Project overview
└── DOCUMENTATION.md            # This file
```

### Adding New Intents

**Step 1: Define Intent Schema**
```python
# app/registry/intent_registry.py

CANONICAL_INTENT_SCHEMAS = {
    ...
    "configure_interface_mtu": {
        "description": "Configure MTU on interface",
        "required_parameters": ["interface", "mtu"],
        "optional_parameters": [],
        "parameter_types": {"interface": str, "mtu": int},
        "aliases": ["set_mtu", "mtu"],
        "rag_type": "configure_interface_mtu",
        "keywords": ["mtu", "interface", "size"],
        "requires": ["interface_exists:{interface}"],
        "provides": ["interface_mtu_set:{interface}"],
        "sop_payload_contract": {
            "interface": "",
            "mtu": ""
        }
    }
}
```

**Step 2: Add Validation Rules (if needed)**
```python
# app/network_validation/interface_validator.py

def validate_mtu(mtu: int) -> bool:
    """MTU must be 68-65535 for Cisco IOS-XE"""
    return 68 <= mtu <= 65535
```

**Step 3: Add to Orchestrator**
```python
# app/services/orchestrator_service.py

_interface_validator = InterfaceValidator()

# In plan_task():
workflow_validator.validate(ordered_workflow)  # Will check MTU range
```

**Step 4: Prepare RAG Documentation**
- Add "Configure Interface MTU" section to Cisco docs PDF
- Ingest: `python ingest_documents.py`

**Step 5: Test**
```bash
# Trigger intent parsing
POST /tasks/execute
{
  "description": "Set MTU to 1500 on Gi1/0/1",
  ...
}

# Should extract:
{
  "intent_type": "configure_interface_mtu",
  "parameters": {"interface": "Gi1/0/1", "mtu": 1500}
}
```

### Adding New Vendors

**Step 1: Add Device Capabilities**
```json
// app/devices/device_capabilities.json

{
  "Juniper": {
    "JUNOS": {
      "preferred_connection": "netconf",
      "default_port": 830,
      "yang_modules": ["ietf-interfaces", "juniper-conf"],
      "state_endpoints": ["/data/juniper-conf:junos"],
      "state_commands": ["show version", "show interfaces"]
    }
  }
}
```

**Step 2: Implement Connection Handler**
```python
# app/devices/connection_service.py

def connect(self, device):
    ...
    if vendor.lower() == "juniper":
        connection["protocol"] = "netconf"
        connection["port"] = 830
        connection["username"] = credentials["username"]
        # SSH key instead of password
        connection["ssh_key"] = credentials.get("ssh_key_path")
```

**Step 3: Implement State Query**
```python
# app/devices/device_state_service.py

def get_device_state(self, connection):
    if connection["vendor"].lower() == "juniper":
        return self._get_juniper_state(connection)
    elif connection["vendor"].lower() == "cisco":
        return self._get_cisco_state(connection)
    ...

def _get_juniper_state(self, connection):
    # Use NETCONF instead of RESTCONF
    # RPC calls: <request-shell-execute command="show version"/>
    ...
```

**Step 4: Update Payload Generation**
```python
# app/llm/payload_generation_service.py

# LLM will use RAG docs to generate NETCONF/RPC payloads
# instead of RESTCONF JSON
```

### Running Tests

```bash
# Manual integration test
python -c "
from app.services.intent_service import IntentService
svc = IntentService()
workflow = svc.parse('Create VLAN 100')
print(workflow)
"

# Full pipeline test
python -m pytest tests/test_orchestrator.py -v

# Test specific component
python -m pytest tests/test_rag.py::test_retrieval -v
```

### Code Standards

- **Type hints**: All functions should have type hints
- **Docstrings**: All classes and public methods need docstrings
- **Error handling**: Use custom exceptions, log comprehensively
- **Logging**: Use app logger for events, not print()
- **Singleton pattern**: Heavy services use lazy initialization
- **No secrets in code**: All credentials from environment variables

### Performance Profiling

```bash
# Profile slow operations
python -m cProfile -s cumulative app/main.py

# Memory profiling
pip install memory-profiler
python -m memory_profiler app/main.py
```

---

## Summary

This Network Orchestration System is a production-ready platform for automating network device management through ITSM workflows. It combines:

1. **Intent Understanding**: LLM-based parsing of change requests
2. **Intelligent Orchestration**: Dependency resolution and state validation
3. **Safe Execution**: Multi-stage pipeline with verification
4. **Audit Trail**: Comprehensive tracking and narrative generation
5. **Extensibility**: Vendor/protocol abstraction for easy integration

For support or issues, refer to the Troubleshooting section or enable DEBUG logging for detailed diagnostics.

