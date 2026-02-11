from __future__ import annotations

from datetime import datetime
from datetime import timezone
import base64
import hashlib
import json
import secrets
import time
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen
from uuid import uuid4
from urllib.parse import urlencode

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from pydantic import Field

from .async_bus import publish_domain_event
from .copilot.router import route_copilot_request
from .copilot.schemas import CopilotRouteRequest
from .copilot.schemas import CopilotRouteResponse
from .config import load_settings
from .observability import instrument_fastapi_app
from .observability import metrics_snapshot
from .observability import record_http_request
from .ontology.deps import create_repository
from .grpc.client import call_create_projection
from .ontology.engine import LinkTypeDefinition
from .ontology.engine import MigrationPlan
from .ontology.engine import MigrationPlanRequest
from .ontology.engine import ObjectTypeDefinition
from .ontology.engine import apply_migration_plan
from .ontology.engine import generate_migration_plan
from .ontology.engine import validate_link_type_definition
from .ontology.engine import validate_object_type_definition
from .ontology.schemas import ActionDispatch
from .ontology.schemas import DispatchDryRunResponse
from .ontology.schemas import DispatchTransactionRecord
from .ontology.schemas import LogicGateResult
from .ontology.schemas import ActionEvent
from .ontology.schemas import ObjectTypeCreate
from .ontology.schemas import ObjectTypeDTO
from .ontology.schemas import ProjectionSnapshot
from .ontology.schemas import RevertTransactionResponse
from .security.auth import AuthUser
from .security.auth import authenticate_user
from .security.auth import create_access_token
from .security.auth import create_refresh_token
from .security.auth import decode_access_token
from .security.auth import revoke_refresh_token
from .security.auth import rotate_refresh_token
from .security.abac import check_write_fields
from .security.abac import filter_read_fields
from .security.audit_signing import append_signed_audit_entry
from .services import AuthService
from .services import LinkService
from .services import NotificationService
from .services import ObjectService
from .services import OntologyService
from .services import SearchService
from .services import TimeTravelService
from .workers.celery_app import celery_app


command_app = FastAPI(title="Genesis Studio Command API", version="0.1.0")
security = HTTPBearer(auto_error=False)
_migration_plans: dict[str, MigrationPlan] = {}
_oidc_states: dict[str, dict[str, str | int]] = {}
_OIDC_STATE_TTL_SECONDS = 600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_proposals() -> dict[str, dict[str, str]]:
    now = _now_iso()
    return {
        "prop-ontology-opt-1": {
            "proposal_id": "prop-ontology-opt-1",
            "title": "Optimize ontology migration gates",
            "intent": "Improve schema migration safety checks",
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        },
        "prop-routing-hardening-1": {
            "proposal_id": "prop-routing-hardening-1",
            "title": "Harden event routing lineage",
            "intent": "Strengthen correlation and replay controls",
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        },
    }


_proposal_states: dict[str, dict[str, str]] = _seed_proposals()
instrument_fastapi_app(command_app, service_name="command-api")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class OidcConfigResponse(BaseModel):
    enabled: bool
    issuer_url: str
    client_id: str
    redirect_uri: str
    scope: str


class OidcAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class OidcCallbackRequest(BaseModel):
    code: str
    state: str
    iss: str | None = None


class OidcCallbackResponse(BaseModel):
    status: str
    detail: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    role: str | None = None


class ValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    hooks: list[dict[str, str | bool]] = Field(default_factory=list)


class MigrationApplyRequest(BaseModel):
    plan_id: str


class AsyncTaskResponse(BaseModel):
    task_id: str
    status: str


class ReplayProjectionRequest(BaseModel):
    from_event_id: str | None = None
    correlation_id: str | None = None
    traceparent: str | None = None


class GrpcProjectionRequest(BaseModel):
    actor: str


class SagaStateResponse(BaseModel):
    txn_id: str
    state: str
    steps: list[str]
    recoverable: bool
    compensation_event_id: str | None


class ProposalState(BaseModel):
    proposal_id: str
    title: str
    intent: str
    status: str
    created_at: str
    updated_at: str


class ProposalActionResponse(BaseModel):
    proposal_id: str
    status: str


class ServiceAdapterResponse(BaseModel):
    operation: str
    status: str
    service: str
    result: object


class ServiceOntologyValidateRequest(BaseModel):
    schema_version: str


class ServiceObjectUpsertRequest(BaseModel):
    object_id: str
    object_type: str


class ServiceLinkConnectRequest(BaseModel):
    source_id: str
    target_id: str
    link_type: str


class ServiceSnapshotRequest(BaseModel):
    entity_id: str
    at_ts: str


class ServiceSearchRequest(BaseModel):
    query: str


class ServiceIssueTokenRequest(BaseModel):
    subject: str
    role: str


class ServicePublishRequest(BaseModel):
    channel: str
    message: str


def _evaluate_dispatch_gates(payload: ActionDispatch, user: AuthUser) -> list[LogicGateResult]:
    source_target_ok = True
    if payload.source_id and payload.target_id:
        source_target_ok = payload.source_id != payload.target_id

    return [
        LogicGateResult(
            tier="L0",
            passed=payload.action_id.startswith("ACT_") and payload.action_id.isupper(),
            detail="action_id must start with ACT_ and use uppercase",
        ),
        LogicGateResult(
            tier="L1",
            passed=source_target_ok,
            detail="source_id and target_id cannot be equal",
        ),
        LogicGateResult(
            tier="L2",
            passed=len(payload.payload) <= 64,
            detail="payload field count must be <= 64",
        ),
        LogicGateResult(
            tier="L3",
            passed=user.role in {"Admin", "Designer", "Operator"},
            detail="role must satisfy action dispatch permissions",
        ),
    ]


def _current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing authorization")
    settings = load_settings()
    try:
        return decode_access_token(credentials.credentials, settings)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from exc


def _require_write_role(user: AuthUser) -> None:
    if user.role not in {"Admin", "Designer", "Operator"}:
        raise HTTPException(status_code=403, detail="insufficient role")


def _record_service_adapter_audit(*, actor: str, operation: str, detail: str) -> None:
    settings = load_settings()
    repo = create_repository(settings)
    try:
        repo.append_audit_log(actor, operation, detail)
    except Exception:
        pass
    finally:
        repo.close()

    try:
        _ = append_signed_audit_entry(
            {
                "event_type": "ServiceAdapterInvoked",
                "actor": actor,
                "service": "command-api",
                "correlation_id": f"{operation}:{detail}",
                "payload": {
                    "operation": operation,
                    "detail": detail,
                },
            }
        )
    except Exception:
        pass


def _oidc_role_from_userinfo(userinfo: dict[str, object]) -> str:
    raw = userinfo.get("role")
    if isinstance(raw, str):
        normalized = raw.strip().capitalize()
        if normalized in {"Admin", "Designer", "Operator", "Viewer"}:
            return normalized
    return "Viewer"


def _normalize_issuer(issuer: str) -> str:
    return issuer.rstrip("/")


def _build_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _create_oidc_state_context() -> tuple[str, dict[str, str | int]]:
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    context: dict[str, str | int] = {
        "nonce": nonce,
        "code_verifier": code_verifier,
        "created_at": int(time.time()),
        "code_challenge": _build_code_challenge(code_verifier),
    }
    return state, context


def _consume_oidc_state_context(state: str) -> dict[str, str]:
    raw_context = _oidc_states.pop(state, None)
    if raw_context is None:
        raise HTTPException(status_code=400, detail="invalid oidc state")

    created_at = int(raw_context.get("created_at") or 0)
    age_seconds = int(time.time()) - created_at
    if age_seconds > _OIDC_STATE_TTL_SECONDS:
        raise HTTPException(status_code=400, detail="expired oidc state")

    nonce = str(raw_context.get("nonce") or "")
    code_verifier = str(raw_context.get("code_verifier") or "")
    if not nonce or not code_verifier:
        raise HTTPException(status_code=400, detail="invalid oidc state context")

    return {
        "nonce": nonce,
        "code_verifier": code_verifier,
    }


def _oidc_exchange_code(settings, code: str, code_verifier: str) -> dict[str, object]:
    token_endpoint = settings.oidc_token_endpoint.strip() or f"{settings.oidc_issuer_url.rstrip('/')}/token"
    payload = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.oidc_client_id,
            "client_secret": settings.oidc_client_secret,
            "redirect_uri": settings.oidc_redirect_uri,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")
    req = Request(token_endpoint, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"oidc token exchange failed: {exc.code}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"oidc token exchange failed: {exc}") from exc

    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="oidc token exchange returned invalid json") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="oidc token exchange returned invalid payload")
    return parsed


def _oidc_fetch_userinfo(settings, access_token: str) -> dict[str, object]:
    userinfo_endpoint = settings.oidc_userinfo_endpoint.strip() or f"{settings.oidc_issuer_url.rstrip('/')}/userinfo"
    req = Request(userinfo_endpoint, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")

    try:
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"oidc userinfo failed: {exc.code}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"oidc userinfo failed: {exc}") from exc

    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="oidc userinfo returned invalid json") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="oidc userinfo returned invalid payload")
    return parsed


@command_app.get("/health")
def health() -> dict[str, str]:
    payload = {"status": "ok", "service": "command-api"}
    record_http_request("/health", 200)
    return payload


@command_app.get("/api/command/health")
def command_health() -> dict[str, str]:
    payload = {"status": "ok", "service": "command-api"}
    record_http_request("/api/command/health", 200)
    return payload


@command_app.get("/metrics")
def metrics() -> str:
    record_http_request("/metrics", 200)
    return metrics_snapshot()


@command_app.post("/api/auth/token", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    settings = load_settings()
    token = create_access_token(user, settings)
    response = LoginResponse(access_token=token, role=user.role)
    record_http_request("/api/auth/token", 200)
    return response


@command_app.post("/api/auth/token/pair", response_model=TokenPairResponse)
def login_with_refresh(payload: LoginRequest) -> TokenPairResponse:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    settings = load_settings()
    access_token = create_access_token(user, settings)
    refresh_token = create_refresh_token(user, settings)
    response = TokenPairResponse(access_token=access_token, refresh_token=refresh_token, role=user.role)
    record_http_request("/api/auth/token/pair", 200)
    return response


@command_app.post("/api/auth/refresh", response_model=TokenPairResponse)
def refresh_access_token(payload: RefreshTokenRequest) -> TokenPairResponse:
    settings = load_settings()
    try:
        user, rotated_refresh_token = rotate_refresh_token(payload.refresh_token, settings)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"invalid refresh token: {exc}") from exc

    access_token = create_access_token(user, settings)
    response = TokenPairResponse(
        access_token=access_token,
        refresh_token=rotated_refresh_token,
        role=user.role,
    )
    record_http_request("/api/auth/refresh", 200)
    return response


@command_app.post("/api/auth/logout")
def logout(payload: LogoutRequest) -> dict[str, str]:
    revoke_refresh_token(payload.refresh_token)
    record_http_request("/api/auth/logout", 200)
    return {"status": "ok"}


@command_app.get("/api/auth/oidc/config", response_model=OidcConfigResponse)
def oidc_config() -> OidcConfigResponse:
    settings = load_settings()
    enabled = bool(settings.oidc_issuer_url and settings.oidc_client_id and settings.oidc_redirect_uri)
    response = OidcConfigResponse(
        enabled=enabled,
        issuer_url=settings.oidc_issuer_url,
        client_id=settings.oidc_client_id,
        redirect_uri=settings.oidc_redirect_uri,
        scope=settings.oidc_scope,
    )
    record_http_request("/api/auth/oidc/config", 200)
    return response


@command_app.get("/api/auth/authorize", response_model=OidcAuthorizeResponse)
def oidc_authorize() -> OidcAuthorizeResponse:
    settings = load_settings()
    if not settings.oidc_issuer_url or not settings.oidc_client_id or not settings.oidc_redirect_uri:
        raise HTTPException(status_code=503, detail="oidc not configured")

    state, state_context = _create_oidc_state_context()
    _oidc_states[state] = state_context
    query = urlencode(
        {
            "client_id": settings.oidc_client_id,
            "response_type": "code",
            "scope": settings.oidc_scope,
            "redirect_uri": settings.oidc_redirect_uri,
            "state": state,
            "nonce": str(state_context["nonce"]),
            "code_challenge": str(state_context["code_challenge"]),
            "code_challenge_method": "S256",
        }
    )
    authorize_url = f"{settings.oidc_issuer_url.rstrip('/')}/authorize?{query}"
    response = OidcAuthorizeResponse(authorize_url=authorize_url, state=state)
    record_http_request("/api/auth/authorize", 200)
    return response


@command_app.post("/api/auth/callback", response_model=OidcCallbackResponse)
def oidc_callback(payload: OidcCallbackRequest) -> OidcCallbackResponse:
    settings = load_settings()
    if not settings.oidc_issuer_url or not settings.oidc_client_id or not settings.oidc_redirect_uri:
        raise HTTPException(status_code=503, detail="oidc not configured")

    state_context = _consume_oidc_state_context(payload.state)

    expected_issuer = _normalize_issuer(settings.oidc_issuer_url)
    if payload.iss and _normalize_issuer(payload.iss) != expected_issuer:
        raise HTTPException(status_code=400, detail="invalid oidc issuer")

    if not settings.oidc_client_secret:
        response = OidcCallbackResponse(status="pending", detail="oidc callback foundation enabled")
        record_http_request("/api/auth/callback", 200)
        return response

    token_payload = _oidc_exchange_code(settings, payload.code, state_context["code_verifier"])

    token_claims = token_payload.get("id_token_claims")
    if isinstance(token_claims, dict):
        claim_nonce = token_claims.get("nonce")
        if claim_nonce is not None and str(claim_nonce) != state_context["nonce"]:
            raise HTTPException(status_code=400, detail="invalid oidc nonce")

        claim_issuer = token_claims.get("iss")
        if isinstance(claim_issuer, str) and _normalize_issuer(claim_issuer) != expected_issuer:
            raise HTTPException(status_code=400, detail="invalid oidc issuer claim")

    idp_access_token = str(token_payload.get("access_token") or "")
    if not idp_access_token:
        raise HTTPException(status_code=502, detail="oidc token exchange missing access_token")

    userinfo = _oidc_fetch_userinfo(settings, idp_access_token)
    if isinstance(token_claims, dict):
        claim_sub = token_claims.get("sub")
        userinfo_sub = userinfo.get("sub")
        if claim_sub is not None and userinfo_sub is not None and str(claim_sub) != str(userinfo_sub):
            raise HTTPException(status_code=400, detail="oidc subject mismatch")

    username = str(userinfo.get("preferred_username") or userinfo.get("sub") or "oidc-user")
    role = _oidc_role_from_userinfo(userinfo)

    local_user = AuthUser(username=username, role=role)
    local_access_token = create_access_token(local_user, settings)
    local_refresh_token = create_refresh_token(local_user, settings)
    response = OidcCallbackResponse(
        status="authenticated",
        detail="oidc callback completed",
        access_token=local_access_token,
        refresh_token=local_refresh_token,
        token_type="bearer",
        role=role,
    )
    record_http_request("/api/auth/callback", 200)
    return response


@command_app.get("/api/command/dependencies")
def dependencies() -> dict[str, str | bool]:
    settings = load_settings()
    repo = create_repository(settings)
    try:
        return {
            "neo4j_uri": settings.neo4j_uri,
            "neo4j_available": repo.ping(),
        }
    except Exception:
        return {
            "neo4j_uri": settings.neo4j_uri,
            "neo4j_available": False,
        }
    finally:
        repo.close()


@command_app.post("/api/command/object-types", response_model=ObjectTypeDTO)
def create_object_type(payload: ObjectTypeCreate, user: AuthUser = Depends(_current_user)) -> ObjectTypeDTO:
    _require_write_role(user)
    decision = check_write_fields(
        role=user.role,
        resource="object_type",
        input_fields={"type_uri", "display_name", "parent_type", "tags"},
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=f"abac denied fields: {decision.denied_fields}")

    settings = load_settings()
    repo = create_repository(settings)
    try:
        result = repo.create_object_type(payload)
        repo.append_audit_log(user.username, "create_object_type", payload.type_uri)
        _ = publish_domain_event(
            {
                "event_type": "ObjectTypeCreated",
                "type_uri": payload.type_uri,
                "actor": user.username,
                "correlation_id": payload.type_uri,
                "causation_id": payload.type_uri,
            }
        )
        record_http_request("/api/command/object-types", 200)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"create failed: {exc}") from exc
    finally:
        repo.close()


@command_app.get("/api/command/object-types")
def list_object_types(user: AuthUser = Depends(_current_user)) -> list[dict[str, object]]:
    settings = load_settings()
    repo = create_repository(settings)
    try:
        rows = repo.list_object_types()
        result = [filter_read_fields(user.role, "object_type", row.model_dump(mode="json")) for row in rows]
        record_http_request("/api/command/object-types:get", 200)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"list failed: {exc}") from exc
    finally:
        repo.close()


@command_app.post("/api/command/dispatch", response_model=ActionEvent)
def dispatch_action(payload: ActionDispatch, user: AuthUser = Depends(_current_user)) -> ActionEvent:
    _require_write_role(user)
    pre_gates = _evaluate_dispatch_gates(payload, user)
    gate_errors = [f"{gate.tier}:{gate.detail}" for gate in pre_gates if not gate.passed]
    if gate_errors:
        raise HTTPException(status_code=400, detail=f"dispatch gate failed: {gate_errors}")

    txn_id = f"txn-{uuid4().hex}"
    settings = load_settings()
    repo = create_repository(settings)
    try:
        enriched_payload = payload.model_copy(update={"actor": user.username})
        result = repo.dispatch_action(enriched_payload)
        post_assert_passed = bool(result.event_id) and result.action_id == payload.action_id
        post_assert_gate = LogicGateResult(
            tier="L4",
            passed=post_assert_passed,
            detail="post assertion: persisted event matches dispatched action",
        )
        all_gates = [*pre_gates, post_assert_gate]
        if not post_assert_passed:
            raise HTTPException(status_code=500, detail="dispatch post assertion failed")

        _ = repo.create_dispatch_transaction(
            txn_id=txn_id,
            action_id=payload.action_id,
            actor=user.username,
            status="committed",
            event_id=result.event_id,
            compensation_event_id=None,
            gates=all_gates,
        )

        repo.append_audit_log(user.username, "dispatch_action", f"{payload.action_id}:{txn_id}")
        _ = publish_domain_event(
            {
                "event_id": result.event_id,
                "event_type": "ActionDispatched",
                "action_id": payload.action_id,
                "actor": user.username,
                "txn_id": txn_id,
                "correlation_id": txn_id,
                "causation_id": result.event_id,
                "traceparent": payload.payload.get("traceparent") if isinstance(payload.payload, dict) else None,
            }
        )
        record_http_request("/api/command/dispatch", 200)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dispatch failed: {exc}") from exc
    finally:
        repo.close()


@command_app.post("/api/command/dispatch/dry-run", response_model=DispatchDryRunResponse)
def dispatch_action_dry_run(payload: ActionDispatch, user: AuthUser = Depends(_current_user)) -> DispatchDryRunResponse:
    _require_write_role(user)
    pre_gates = _evaluate_dispatch_gates(payload, user)
    gates = [
        *pre_gates,
        LogicGateResult(
            tier="L4",
            passed=True,
            detail="post assertion deferred for dry-run",
        ),
    ]
    allowed = all(gate.passed for gate in pre_gates)
    response = DispatchDryRunResponse(
        allowed=allowed,
        txn_preview_id=f"dryrun-{uuid4().hex[:12]}",
        gates=gates,
        estimated_effects=[
            "append immutable domain event",
            "append signed audit log",
            "publish projection refresh signal",
        ],
    )
    record_http_request("/api/command/dispatch/dry-run", 200)
    return response


@command_app.get("/api/command/transactions", response_model=list[DispatchTransactionRecord])
def list_dispatch_transactions(user: AuthUser = Depends(_current_user)) -> list[DispatchTransactionRecord]:
    _require_write_role(user)
    settings = load_settings()
    repo = create_repository(settings)
    try:
        items = repo.list_dispatch_transactions()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"transactions failed: {exc}") from exc
    finally:
        repo.close()
    record_http_request("/api/command/transactions", 200)
    return items


@command_app.post("/api/command/revert/{txn_id}", response_model=RevertTransactionResponse)
def revert_dispatch_transaction(txn_id: str, user: AuthUser = Depends(_current_user)) -> RevertTransactionResponse:
    _require_write_role(user)
    settings = load_settings()
    repo = create_repository(settings)
    try:
        txn_record = repo.get_dispatch_transaction(txn_id)
        if txn_record is None:
            raise HTTPException(status_code=404, detail="transaction not found")
        if txn_record.status == "reverted":
            record_http_request("/api/command/revert", 200)
            return RevertTransactionResponse(
                txn_id=txn_id,
                status="reverted",
                compensation_event_id=txn_record.compensation_event_id,
            )
        if txn_record.status != "committed":
            raise HTTPException(status_code=409, detail="transaction is not revertible")

        compensation_payload = ActionDispatch(
            action_id="ACT_COMPENSATE",
            source_id=txn_record.action_id,
            target_id=txn_id,
            actor=user.username,
            payload={
                "original_txn_id": txn_id,
                "original_action_id": txn_record.action_id,
            },
        )
        compensation_event = repo.dispatch_action(compensation_payload)
        _ = repo.mark_dispatch_transaction_reverted(txn_id, compensation_event.event_id)
        repo.append_audit_log(user.username, "revert_transaction", txn_id)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=f"revert failed: {exc}") from exc
    finally:
        repo.close()
    _ = publish_domain_event(
        {
            "event_id": compensation_event.event_id,
            "event_type": "TransactionReverted",
            "txn_id": txn_id,
            "actor": user.username,
            "correlation_id": txn_id,
            "causation_id": compensation_event.event_id,
        }
    )
    record_http_request("/api/command/revert", 200)
    return RevertTransactionResponse(
        txn_id=txn_id,
        status="reverted",
        compensation_event_id=compensation_event.event_id,
    )


@command_app.get("/api/command/transactions/{txn_id}/saga", response_model=SagaStateResponse)
def transaction_saga_state(txn_id: str, user: AuthUser = Depends(_current_user)) -> SagaStateResponse:
    _require_write_role(user)
    settings = load_settings()
    repo = create_repository(settings)
    try:
        txn_record = repo.get_dispatch_transaction(txn_id)
        if txn_record is None:
            raise HTTPException(status_code=404, detail="transaction not found")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=f"saga state failed: {exc}") from exc
    finally:
        repo.close()

    if txn_record.status == "reverted":
        response = SagaStateResponse(
            txn_id=txn_id,
            state="COMPENSATED",
            steps=["dispatch_committed", "compensation_applied"],
            recoverable=False,
            compensation_event_id=txn_record.compensation_event_id,
        )
    else:
        response = SagaStateResponse(
            txn_id=txn_id,
            state="DISPATCHED",
            steps=["dispatch_committed"],
            recoverable=True,
            compensation_event_id=None,
        )
    record_http_request("/api/command/transactions/saga", 200)
    return response


@command_app.get("/api/command/events")
def list_events(user: AuthUser = Depends(_current_user)) -> list[dict[str, object]]:
    settings = load_settings()
    repo = create_repository(settings)
    try:
        rows = repo.list_events()
        result = [filter_read_fields(user.role, "event", row.model_dump(mode="json")) for row in rows]
        record_http_request("/api/command/events", 200)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"events failed: {exc}") from exc
    finally:
        repo.close()


@command_app.post("/api/command/project", response_model=ProjectionSnapshot)
def project_events(user: AuthUser = Depends(_current_user)) -> ProjectionSnapshot:
    _require_write_role(user)
    settings = load_settings()
    repo = create_repository(settings)
    try:
        snapshot = repo.create_projection_snapshot()
        repo.append_audit_log(user.username, "create_projection", snapshot.projection_id)
        _ = publish_domain_event(
            {
                "event_id": snapshot.projection_id,
                "event_type": "ProjectionCreated",
                "projection_id": snapshot.projection_id,
                "actor": user.username,
                "correlation_id": snapshot.projection_id,
                "causation_id": snapshot.projection_id,
            }
        )
        record_http_request("/api/command/project", 200)
        return snapshot
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"projection failed: {exc}") from exc
    finally:
        repo.close()


@command_app.post("/api/command/ontology/otd/validate", response_model=ValidationResponse)
def validate_otd(payload: ObjectTypeDefinition, user: AuthUser = Depends(_current_user)) -> ValidationResponse:
    _require_write_role(user)
    result = validate_object_type_definition(payload)
    response = ValidationResponse(
        valid=result.valid,
        errors=result.errors,
        hooks=[{"hook": hook.hook, "passed": hook.passed, "detail": hook.detail} for hook in result.hooks],
    )
    record_http_request("/api/command/ontology/otd/validate", 200)
    return response


@command_app.post("/api/command/ontology/ltd/validate", response_model=ValidationResponse)
def validate_ltd(payload: LinkTypeDefinition, user: AuthUser = Depends(_current_user)) -> ValidationResponse:
    _require_write_role(user)
    result = validate_link_type_definition(payload)
    response = ValidationResponse(
        valid=result.valid,
        errors=result.errors,
        hooks=[{"hook": hook.hook, "passed": hook.passed, "detail": hook.detail} for hook in result.hooks],
    )
    record_http_request("/api/command/ontology/ltd/validate", 200)
    return response


@command_app.post("/api/command/ontology/migration/plan", response_model=MigrationPlan)
def create_migration_plan(payload: MigrationPlanRequest, user: AuthUser = Depends(_current_user)) -> MigrationPlan:
    _require_write_role(user)
    plan = generate_migration_plan(payload)
    _migration_plans[plan.plan_id] = plan
    record_http_request("/api/command/ontology/migration/plan", 200)
    return plan


@command_app.post("/api/command/ontology/migration/apply")
def apply_migration(payload: MigrationApplyRequest, user: AuthUser = Depends(_current_user)) -> dict[str, str | bool | int | list[str]]:
    _require_write_role(user)
    plan = _migration_plans.get(payload.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="migration plan not found")
    result = apply_migration_plan(plan)
    _ = publish_domain_event(
        {
            "event_type": "MigrationApplied",
            "plan_id": plan.plan_id,
            "actor": user.username,
            "correlation_id": plan.plan_id,
            "causation_id": plan.plan_id,
        }
    )
    record_http_request("/api/command/ontology/migration/apply", 200)
    return result


@command_app.get("/api/command/proposals", response_model=list[ProposalState])
def list_proposals(user: AuthUser = Depends(_current_user)) -> list[ProposalState]:
    _require_write_role(user)
    rows = [ProposalState(**payload) for payload in _proposal_states.values()]
    rows.sort(key=lambda item: item.proposal_id)
    record_http_request("/api/command/proposals", 200)
    return rows


def _proposal_action(proposal_id: str, action: str, actor: str) -> ProposalActionResponse:
    proposal = _proposal_states.get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")

    status = proposal["status"]
    if action == "apply":
        status = "applied"
    elif action == "reject":
        status = "rejected"
    elif action == "rollback":
        if proposal["status"] != "applied":
            raise HTTPException(status_code=409, detail="proposal is not applied")
        status = "rolled_back"

    proposal["status"] = status
    proposal["updated_at"] = _now_iso()
    _ = publish_domain_event(
        {
            "event_type": "ProposalStateChanged",
            "proposal_id": proposal_id,
            "action": action,
            "status": status,
            "actor": actor,
            "correlation_id": proposal_id,
            "causation_id": f"{proposal_id}:{action}",
        }
    )
    return ProposalActionResponse(proposal_id=proposal_id, status=status)


@command_app.post("/api/command/proposals/{proposal_id}/apply", response_model=ProposalActionResponse)
def apply_proposal(proposal_id: str, user: AuthUser = Depends(_current_user)) -> ProposalActionResponse:
    _require_write_role(user)
    response = _proposal_action(proposal_id, "apply", user.username)
    record_http_request("/api/command/proposals/apply", 200)
    return response


@command_app.post("/api/command/proposals/{proposal_id}/reject", response_model=ProposalActionResponse)
def reject_proposal(proposal_id: str, user: AuthUser = Depends(_current_user)) -> ProposalActionResponse:
    _require_write_role(user)
    response = _proposal_action(proposal_id, "reject", user.username)
    record_http_request("/api/command/proposals/reject", 200)
    return response


@command_app.post("/api/command/proposals/{proposal_id}/rollback", response_model=ProposalActionResponse)
def rollback_proposal(proposal_id: str, user: AuthUser = Depends(_current_user)) -> ProposalActionResponse:
    _require_write_role(user)
    response = _proposal_action(proposal_id, "rollback", user.username)
    record_http_request("/api/command/proposals/rollback", 200)
    return response


@command_app.post("/api/command/services/ontology/validate", response_model=ServiceAdapterResponse)
def service_validate_ontology(
    payload: ServiceOntologyValidateRequest,
    user: AuthUser = Depends(_current_user),
) -> ServiceAdapterResponse:
    _require_write_role(user)
    service = OntologyService()
    result = service.validate_schema(payload.schema_version)
    _record_service_adapter_audit(
        actor=user.username,
        operation="service_validate_schema",
        detail=payload.schema_version,
    )
    published = publish_domain_event(
        {
            "event_type": "ServiceAdapterInvoked",
            "actor": user.username,
            "service": "command-api",
            "operation": "ontology.validate_schema",
            "correlation_id": payload.schema_version,
            "causation_id": payload.schema_version,
        }
    )
    record_http_request("/api/command/services/ontology/validate", 200)
    return ServiceAdapterResponse(
        operation="validate_schema",
        status="ok" if published else "event_publish_failed",
        service=service.service_name,
        result={**result, "event_published": published},
    )


@command_app.post("/api/command/services/object/upsert", response_model=ServiceAdapterResponse)
def service_object_upsert(
    payload: ServiceObjectUpsertRequest,
    user: AuthUser = Depends(_current_user),
) -> ServiceAdapterResponse:
    _require_write_role(user)
    decision = check_write_fields(
        role=user.role,
        resource="object_type",
        input_fields={"type_uri", "display_name", "tags"},
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=f"abac denied fields: {decision.denied_fields}")

    service = ObjectService()
    result = service.upsert_object(payload.object_id, payload.object_type)
    _record_service_adapter_audit(
        actor=user.username,
        operation="service_upsert_object",
        detail=payload.object_id,
    )
    record_http_request("/api/command/services/object/upsert", 200)
    return ServiceAdapterResponse(
        operation="upsert_object",
        status="ok",
        service=service.service_name,
        result=result,
    )


@command_app.post("/api/command/services/link/connect", response_model=ServiceAdapterResponse)
def service_link_connect(
    payload: ServiceLinkConnectRequest,
    user: AuthUser = Depends(_current_user),
) -> ServiceAdapterResponse:
    _require_write_role(user)
    service = LinkService()
    result = service.connect(payload.source_id, payload.target_id, payload.link_type)
    _record_service_adapter_audit(
        actor=user.username,
        operation="service_connect_link",
        detail=f"{payload.source_id}->{payload.target_id}",
    )
    record_http_request("/api/command/services/link/connect", 200)
    return ServiceAdapterResponse(
        operation="connect",
        status="ok",
        service=service.service_name,
        result=result,
    )


@command_app.post("/api/command/services/time-travel/snapshot", response_model=ServiceAdapterResponse)
def service_time_travel_snapshot(
    payload: ServiceSnapshotRequest,
    user: AuthUser = Depends(_current_user),
) -> ServiceAdapterResponse:
    service = TimeTravelService()
    result = service.snapshot(payload.entity_id, payload.at_ts)
    _record_service_adapter_audit(
        actor=user.username,
        operation="service_snapshot",
        detail=payload.entity_id,
    )
    record_http_request("/api/command/services/time-travel/snapshot", 200)
    return ServiceAdapterResponse(
        operation="snapshot",
        status="ok",
        service=service.service_name,
        result=result,
    )


@command_app.post("/api/command/services/search", response_model=ServiceAdapterResponse)
def service_search(
    payload: ServiceSearchRequest,
    user: AuthUser = Depends(_current_user),
) -> ServiceAdapterResponse:
    service = SearchService()
    result = service.search(payload.query)
    _record_service_adapter_audit(
        actor=user.username,
        operation="service_search",
        detail=payload.query,
    )
    record_http_request("/api/command/services/search", 200)
    return ServiceAdapterResponse(
        operation="search",
        status="ok",
        service=service.service_name,
        result=result,
    )


@command_app.post("/api/command/services/auth/issue-token", response_model=ServiceAdapterResponse)
def service_issue_token(
    payload: ServiceIssueTokenRequest,
    user: AuthUser = Depends(_current_user),
) -> ServiceAdapterResponse:
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="admin role required")
    service = AuthService()
    result = service.issue_service_token(payload.subject, payload.role)
    _record_service_adapter_audit(
        actor=user.username,
        operation="service_issue_token",
        detail=payload.subject,
    )
    record_http_request("/api/command/services/auth/issue-token", 200)
    return ServiceAdapterResponse(
        operation="issue_service_token",
        status="ok",
        service=service.service_name,
        result=result,
    )


@command_app.post("/api/command/services/notification/publish", response_model=ServiceAdapterResponse)
def service_publish_notification(
    payload: ServicePublishRequest,
    user: AuthUser = Depends(_current_user),
) -> ServiceAdapterResponse:
    _require_write_role(user)
    service = NotificationService()
    result = service.publish(payload.channel, payload.message)
    _record_service_adapter_audit(
        actor=user.username,
        operation="service_publish_notification",
        detail=payload.channel,
    )
    record_http_request("/api/command/services/notification/publish", 200)
    return ServiceAdapterResponse(
        operation="publish",
        status="ok",
        service=service.service_name,
        result=result,
    )


@command_app.post("/api/command/project/async", response_model=AsyncTaskResponse)
def project_events_async(user: AuthUser = Depends(_current_user)) -> AsyncTaskResponse:
    _require_write_role(user)
    task = celery_app.send_task("genesis.projection.refresh")
    record_http_request("/api/command/project/async", 200)
    return AsyncTaskResponse(task_id=task.id, status="queued")


@command_app.post("/api/command/project/replay", response_model=AsyncTaskResponse)
def replay_projection(payload: ReplayProjectionRequest, user: AuthUser = Depends(_current_user)) -> AsyncTaskResponse:
    _require_write_role(user)
    kwargs = {
        "from_event_id": payload.from_event_id,
        "correlation_id": payload.correlation_id,
        "traceparent": payload.traceparent,
        "requested_by": user.username,
    }
    task = celery_app.send_task("genesis.projection.replay", kwargs=kwargs)
    record_http_request("/api/command/project/replay", 200)
    return AsyncTaskResponse(task_id=task.id, status="queued")


@command_app.post("/api/copilot/route", response_model=CopilotRouteResponse)
def route_copilot(payload: CopilotRouteRequest, user: AuthUser = Depends(_current_user)) -> CopilotRouteResponse:
    _require_write_role(user)
    response = route_copilot_request(payload)
    record_http_request("/api/copilot/route", 200)
    return response


@command_app.post("/api/command/grpc/projection")
def grpc_projection(payload: GrpcProjectionRequest, user: AuthUser = Depends(_current_user)) -> dict[str, str]:
    _require_write_role(user)
    try:
        projection_id = call_create_projection(actor=payload.actor)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"grpc projection unavailable: {exc}") from exc
    record_http_request("/api/command/grpc/projection", 200)
    return {"projection_id": projection_id}
