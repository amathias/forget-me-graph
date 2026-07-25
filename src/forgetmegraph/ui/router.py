from __future__ import annotations

import asyncio
import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi import Path as ApiPath
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from forgetmegraph.config import Settings
from forgetmegraph.context.datahub import DataHubIntegrationError
from forgetmegraph.demo.seed import DEMO_SECRET
from forgetmegraph.demo.workflow import prepare_demo_workflow, run_workflow

router = APIRouter()
UI_DIR = Path(__file__).resolve().parent
_demo_lock = asyncio.Lock()
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
_ALLOWED_EVIDENCE_FILES = frozenset(
    {
        "certificate.json",
        "certificate.md",
        "datahub-read-receipt.json",
        "datahub-write-receipt.json",
    }
)


class DemoPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
    selector_value: str = Field(min_length=1, max_length=18, pattern=r"^[0-9]+$", repr=False)


class DemoRunRequest(DemoPlanRequest):
    plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    approver: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9 ._@-]+$")
    approved: bool
    reset_synthetic_estate: bool = True
    require_datahub: bool = True


def _project_root() -> Path:
    candidates = (Path.cwd().resolve(), Path(__file__).resolve().parents[3])
    for candidate in candidates:
        if (candidate / "demo/metadata/graph.json").is_file():
            return candidate
    raise RuntimeError("project metadata is unavailable")


def _selector_secret() -> str:
    settings = Settings.from_env()
    if settings.selector_secret:
        return settings.selector_secret
    if settings.app_env in {"local", "test"}:
        return DEMO_SECRET
    raise RuntimeError("selector protection is not configured")


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_platform(urn: str) -> str:
    marker = "urn:li:dataPlatform:"
    if marker not in urn:
        return "datahub"
    return urn.split(marker, 1)[1].split(",", 1)[0]


def _evidence_summary(evidence_dir: Path) -> dict[str, object]:
    result: dict[str, object] = {}
    for name in sorted(_ALLOWED_EVIDENCE_FILES):
        path = evidence_dir / name
        if path.is_file():
            result[name] = {
                "sha256": _file_sha256(path),
                "download_url": f"/api/demo/evidence/{evidence_dir.name}/{name}",
            }
    write_path = evidence_dir / "datahub-write-receipt.json"
    if write_path.is_file():
        payload = _load_json(write_path)
        if isinstance(payload, dict):
            result["datahub_write_verified"] = bool(payload.get("verified"))
    read_path = evidence_dir / "datahub-read-receipt.json"
    if read_path.is_file():
        payload = _load_json(read_path)
        if isinstance(payload, dict):
            result["datahub_tools"] = sorted(payload.get("tools") or [])
    return result


@router.get("/", include_in_schema=False)
def judge_console() -> FileResponse:
    return FileResponse(UI_DIR / "index.html", media_type="text/html")


@router.get("/assets/{asset_name}", include_in_schema=False)
def ui_asset(
    asset_name: Annotated[str, ApiPath(pattern=r"^(app\.css|app\.js)$")],
) -> FileResponse:
    media_type = "text/css" if asset_name.endswith(".css") else "text/javascript"
    return FileResponse(UI_DIR / asset_name, media_type=media_type)


@router.get("/api/demo/overview")
def demo_overview() -> dict[str, object]:
    root = _project_root()
    graph = _load_json(root / "demo/metadata/graph.json")
    mapping_payload = _load_json(root / "demo/selector-mappings.json")
    coordinator_path = root / "examples/live-evidence-summary.json"
    coordinator_evidence = _load_json(coordinator_path) if coordinator_path.is_file() else None
    if not isinstance(graph, dict) or not isinstance(mapping_payload, dict):
        raise HTTPException(status_code=500, detail="demo metadata is unavailable")

    mappings = mapping_payload.get("mappings") or []
    mapping_by_edge = {
        (item["source_urn"], item["destination_urn"]): item
        for item in mappings
        if isinstance(item, dict)
    }
    nodes = [
        {
            "urn": artifact["urn"],
            "name": artifact["name"],
            "artifact_type": artifact["artifact_type"],
            "adapter": artifact["adapter"],
            "policy": artifact.get("policy", "required"),
            "platform": _artifact_platform(artifact["urn"]),
        }
        for artifact in graph.get("artifacts") or []
        if isinstance(artifact, dict)
    ]
    edges = []
    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        mapping = mapping_by_edge.get((edge["source_urn"], edge["destination_urn"]))
        edges.append(
            {
                **edge,
                "mapping_type": mapping.get("mapping_type") if mapping else None,
                "destination_field": mapping.get("destination_field") if mapping else None,
            }
        )
    return {
        "project": "Forget-Me-Graph",
        "mode": "synthetic_disposable_demo",
        "namespace": "forgetme.",
        "nodes": nodes,
        "edges": edges,
        "coordinator_evidence": coordinator_evidence,
        "claims": {
            "implemented": [
                "row purge",
                "derived rebuild",
                "vector deletion",
                "cache eviction",
                "export replacement",
                "clean-snapshot retraining",
                "independent verification",
                "DataHub write and immediate reread",
            ],
            "limitation": "Clean retraining is not formal proof of mathematical unlearning.",
        },
    }


@router.post("/api/demo/plan")
def demo_plan(request: DemoPlanRequest) -> dict[str, object]:
    try:
        prepared = prepare_demo_workflow(
            project_root=_project_root(),
            request_id=request.request_id,
            selector_value=request.selector_value,
            selector_secret=_selector_secret(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="the deterministic plan could not be built"
        ) from exc

    artifact_by_urn = {artifact.urn: artifact for artifact in prepared.artifacts}
    decisions = []
    for decision in prepared.plan.decisions:
        artifact = artifact_by_urn[decision.target_urn]
        decisions.append(
            {
                "target_urn": decision.target_urn,
                "artifact_name": artifact.name,
                "artifact_type": artifact.artifact_type.value,
                "action": decision.action.value,
                "status": decision.status.value,
                "selector_field": decision.selector_field,
                "lineage_path": decision.lineage_path,
                "reason": decision.reason,
            }
        )
    return {
        "request_id": prepared.plan.request_id,
        "selector": {
            "subject_type": prepared.selector.subject_type,
            "field": prepared.selector.field,
            "operator": prepared.selector.operator.value,
            "token": prepared.selector.token,
            "raw_value_persisted": False,
        },
        "entrypoint_urns": prepared.plan.entrypoint_urns,
        "plan_hash": prepared.plan.plan_hash,
        "decisions": decisions,
        "approval_required": True,
    }


@router.post("/api/demo/run")
async def demo_run(request: DemoRunRequest) -> dict[str, object]:
    if not request.approved:
        raise HTTPException(status_code=403, detail="explicit approval is required")
    settings = Settings.from_env()
    require_datahub = request.require_datahub or settings.app_env not in {"local", "test"}
    try:
        async with _demo_lock:
            certificate = await asyncio.to_thread(
                run_workflow,
                root=settings.demo_fixture_root,
                project_root=_project_root(),
                approver=request.approver,
                request_id=request.request_id,
                selector_value=request.selector_value,
                selector_secret=_selector_secret(),
                expected_plan_hash=request.plan_hash,
                seed=request.reset_synthetic_estate,
                require_datahub=require_datahub,
                settings=settings,
            )
    except DataHubIntegrationError as exc:
        raise HTTPException(status_code=503, detail="the live DataHub gate failed closed") from exc
    except ValueError as exc:
        if "plan hash" in str(exc):
            raise HTTPException(status_code=409, detail="the approved plan is stale") from exc
        raise HTTPException(status_code=400, detail="the approved workflow was refused") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="the workflow failed closed") from exc

    evidence_dir = settings.demo_fixture_root.resolve() / "evidence" / certificate.request_id
    return {
        "request_id": certificate.request_id,
        "selector_token": certificate.selector_token,
        "plan_hash": certificate.plan_hash,
        "status": certificate.status.value,
        "certificate_hash": certificate.certificate_hash,
        "generated_at": certificate.generated_at.isoformat(),
        "items": [item.model_dump(mode="json") for item in certificate.items],
        "datahub_required": require_datahub,
        "evidence": _evidence_summary(evidence_dir),
    }


@router.get("/api/demo/evidence/{request_id}/{file_name}")
def download_evidence(
    request_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")],
    file_name: str,
) -> FileResponse:
    if not _SAFE_REQUEST_ID.fullmatch(request_id) or file_name not in _ALLOWED_EVIDENCE_FILES:
        raise HTTPException(status_code=404, detail="evidence file not found")
    path = Settings.from_env().demo_fixture_root.resolve() / "evidence" / request_id / file_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="evidence file not found")
    media_type = "application/json" if file_name.endswith(".json") else "text/markdown"
    return FileResponse(path, media_type=media_type, filename=file_name)
