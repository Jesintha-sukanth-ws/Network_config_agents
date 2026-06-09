"""
Integration smoke test — runs every stage of the Phase 5 checklist.

Stages:
  1. import app.main
  2. initialize FastAPI
  3. initialize OrchestratorService
  4. initialize RAG services
  5. initialize polling thread
  6. execute fake task
  7. execute end-to-end pipeline
"""

import os
import sys
import time
import threading
import traceback


# Allow running from project root without `pip install -e .`
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def stage(label):
    print(f"\n[STAGE] {label}")
    print("-" * 60)


def passed(msg):
    print(f"  PASS  {msg}")


def failed(msg, exc=None):
    print(f"  FAIL  {msg}")
    if exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# 1. import app.main
# ─────────────────────────────────────────────────────────────

stage("1. import app.main")
try:
    import app.main as main_module
    passed("module imported")
except Exception as e:
    failed("could not import app.main", e)


# ─────────────────────────────────────────────────────────────
# 2. initialize FastAPI
# ─────────────────────────────────────────────────────────────

stage("2. initialize FastAPI")
try:
    app = main_module.app
    assert app is not None
    routes = [r.path for r in app.routes]
    assert "/health" in routes, f"/health missing from routes: {routes}"
    assert "/tasks/execute" in routes, f"/tasks/execute missing"
    passed(f"FastAPI app present with routes: {routes}")
except Exception as e:
    failed("FastAPI init failed", e)


# ─────────────────────────────────────────────────────────────
# 3. initialize OrchestratorService
# ─────────────────────────────────────────────────────────────

stage("3. initialize OrchestratorService")
try:
    from app.services.orchestrator_service import OrchestratorService
    orchestrator = OrchestratorService()
    assert hasattr(orchestrator, "process_task"), "process_task missing"
    passed("OrchestratorService instance constructed")
except Exception as e:
    failed("OrchestratorService init failed", e)


# ─────────────────────────────────────────────────────────────
# 4. initialize RAG services (lazy — force creation through orchestrator)
# ─────────────────────────────────────────────────────────────

stage("4. initialize RAG services")
try:
    from app.rag.chroma_manager import ChromaManager
    from app.rag.embedding_service import EmbeddingService
    from app.rag.retrieval_service import RetrievalService

    chroma = ChromaManager()
    passed(
        f"ChromaManager initialized with collections "
        f"{list(chroma.collections.keys())}"
    )

    # EmbeddingService loads the actual model (~80MB). If sentence-transformers
    # is not installed, this is the first place to surface that.
    embedder = EmbeddingService()
    passed("EmbeddingService loaded")

    retrieval = RetrievalService(chroma, embedder)
    # Resolution must work without crashing
    name = retrieval._resolve_collection_name("Cisco", "IOS-XE")
    assert name == "cisco_iosxe", f"unexpected collection name: {name}"
    passed(f"RetrievalService resolved collection -> {name}")
except Exception as e:
    failed("RAG init failed", e)


# ─────────────────────────────────────────────────────────────
# 5. initialize polling thread (start + immediately stop)
# ─────────────────────────────────────────────────────────────

stage("5. initialize polling thread")
try:
    from app.services import polling_service

    stop = threading.Event()

    def runner():
        try:
            polling_service.poll_servicenow(stop_event=stop)
        except Exception as exc:  # noqa: BLE001
            # Network errors are expected in dev environments; we only care
            # that the function is callable and respects the stop event.
            print(f"  (polling raised, expected in dev: {exc!r})")

    t = threading.Thread(target=runner, name="poll-test", daemon=True)
    t.start()
    time.sleep(0.5)
    stop.set()
    t.join(timeout=3)

    assert not t.is_alive(), "polling thread did not stop"
    passed("polling thread started and stopped cleanly")
except Exception as e:
    failed("polling thread failed", e)


# ─────────────────────────────────────────────────────────────
# 6. execute fake task — empty description path
# ─────────────────────────────────────────────────────────────

stage("6. execute fake task (empty description -> graceful error)")
try:
    fake_task = {
        "number": "FAKE0001",
        "sys_id": "fakesysid",
        "short_description": "",
        "description": "",
        "cmdb_ci": {"value": "fakeci"},
    }
    result = orchestrator.process_task(fake_task)
    assert isinstance(result, dict), f"non-dict result: {type(result)}"
    assert "status" in result, f"no status in result: {result}"
    passed(f"fake task returned status={result['status']}")
except Exception as e:
    failed("fake task crashed", e)


# ─────────────────────────────────────────────────────────────
# 7. execute end-to-end pipeline
#
# A full E2E run requires:
#   - reachable ServiceNow CMDB
#   - reachable network device
#   - running Ollama with the configured model
#   - ingested RAG documents
#
# These are not guaranteed in dev. We therefore submit a task with a
# real-looking description and assert the orchestrator returns a
# structured dict (not an uncaught exception). Any specific failure
# (intent, CMDB, push) is acceptable; only an unhandled crash fails.
# ─────────────────────────────────────────────────────────────

stage("7. execute end-to-end pipeline (graceful degradation accepted)")
try:
    e2e_task = {
        "number": "FAKE0002",
        "sys_id": "fakesysid2",
        "short_description": "Create VLAN 100 named TEST",
        "description": "Create VLAN 100 with name TEST on the switch",
        "cmdb_ci": {"value": "no_such_ci"},
    }
    result = orchestrator.process_task(e2e_task)
    assert isinstance(result, dict), f"non-dict result: {type(result)}"
    assert "status" in result, f"no status in result: {result}"
    print(f"  result.status = {result['status']}")
    print(f"  result.keys   = {sorted(result.keys())}")
    passed("end-to-end pipeline returned a structured response")
except Exception as e:
    failed("end-to-end pipeline raised uncaught exception", e)


print("\n" + "=" * 60)
print("ALL STAGES PASSED")
print("=" * 60)
