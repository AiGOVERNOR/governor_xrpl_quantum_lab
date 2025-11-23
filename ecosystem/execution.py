"""
ecosystem.execution
-------------------

Execution Planning Layer for Governor XRPL Quantum Lab.

This module is STILL:

  - READ-ONLY
  - PLANNING-ONLY
  - NON-SIGNING and NON-SUBMITTING

It takes:
  - an XRPL transaction intent
  - live VQM pipeline state (network_state, guardian, scheduler, fee_horizon)
  - router + protocol graph + quantum fusion outputs

and returns a *bundle* describing:

  - which protocol to use
  - safe fee to pay
  - when to send (or delay / batch)
  - exact offline XRPL Payment JSON to build

It NEVER sees seeds / private keys.
It NEVER signs.
It NEVER broadcasts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Defensive imports (self-healing / self-upgrading)
# ---------------------------------------------------------------------------

# We wrap imports in try/except so the planner can still return a *minimal*
# advisory bundle even if some subsystems are missing or upgraded.


def _safe_import() -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # VQM pipeline
    try:
        from ecosystem.pipeline_v5 import run_vqm_cycle_v5  # type: ignore

        out["run_vqm_cycle_v5"] = run_vqm_cycle_v5
    except Exception:
        out["run_vqm_cycle_v5"] = None

    # Intents + brain
    try:
        from ecosystem.tx.intents import TxIntent  # type: ignore

        out["TxIntent"] = TxIntent
    except Exception:
        out["TxIntent"] = None

    try:
        from ecosystem.tx.brain import tx_brain  # type: ignore

        out["tx_brain"] = tx_brain
    except Exception:
        out["tx_brain"] = None

    # Router V3
    try:
        from ecosystem.tx.router_v3 import TxRouterV3  # type: ignore

        out["TxRouterV3"] = TxRouterV3
    except Exception:
        out["TxRouterV3"] = None

    # Protocol graph
    try:
        from ecosystem.protocol_graph import (  # type: ignore
            build_default_graph,
            ProtocolSelector,
        )

        out["build_default_graph"] = build_default_graph
        out["ProtocolSelector"] = ProtocolSelector
    except Exception:
        out["build_default_graph"] = None
        out["ProtocolSelector"] = None

    # Quantum fusion
    try:
        from ecosystem.quantum_fusion import compute_quantum_signal  # type: ignore

        out["compute_quantum_signal"] = compute_quantum_signal
    except Exception:
        out["compute_quantum_signal"] = None

    return out


_IMPORTS = _safe_import()
run_vqm_cycle_v5 = _IMPORTS["run_vqm_cycle_v5"]
TxIntent = _IMPORTS["TxIntent"]
tx_brain = _IMPORTS["tx_brain"]
TxRouterV3 = _IMPORTS["TxRouterV3"]
build_default_graph = _IMPORTS["build_default_graph"]
ProtocolSelector = _IMPORTS["ProtocolSelector"]
compute_quantum_signal = _IMPORTS["compute_quantum_signal"]


# ---------------------------------------------------------------------------
# ExecutionPlanner
# ---------------------------------------------------------------------------


@dataclass
class ExecutionPlanner:
    """
    High-level execution planner.

    Self-healing:
      - If some subsystems fail, it falls back to conservative defaults
        instead of exploding.

    Self-upgrading:
      - It tolerates additional / missing fields from newer pipeline or
        router versions by always using `.get()` with defaults.
    """

    VERSION: str = "0.2.0"

    def __post_init__(self) -> None:
        # Lazily build optional subsystems
        self._router = TxRouterV3() if TxRouterV3 is not None else None

        if build_default_graph is not None and ProtocolSelector is not None:
            graph = build_default_graph()
            self._selector = ProtocolSelector(graph)
        else:
            self._selector = None

    # ------------------------------------------------------------------ #
    # Core public API
    # ------------------------------------------------------------------ #

    def plan_execution(self, intent: Optional[Any] = None) -> Dict[str, Any]:
        """
        Plan execution for a single XRPL intent.

        If `intent` is None and TxIntent is available, we build a demo
        simple_payment intent. This is used by demos / vqm_doctor.
        """
        if intent is None and TxIntent is not None:
            intent = TxIntent.new(
                kind="simple_payment",
                amount_drops=1_000_000,
                source_account="rSOURCE_ACCOUNT_PLACEHOLDER",
                destination_account="rDESTINATION_ACCOUNT_PLACEHOLDER",
                metadata={"note": "qxl_demo"},
            )

        # 1) Pull core state from pipeline
        (
            net_state,
            guardian,
            pipeline_raw,
            scheduler_band,
            fee_horizon,
        ) = self._safe_run_pipeline()

        median_fee = int(net_state.get("txn_median_fee", 10))
        recommended_fee = int(net_state.get("recommended_fee_drops", median_fee))

        # 2) Quantum fusion (or conservative fallback)
        quantum = self._safe_quantum(net_state, guardian, fee_horizon)
        band = quantum.get("band", scheduler_band or "normal")
        safe_fee = int(quantum.get("safe_fee_drops", int(median_fee * 1.1)))

        # 3) Transaction plan from brain
        tx_plan = self._safe_tx_plan(intent, net_state, guardian)

        # 4) Router decision
        router_decision = self._safe_router_decision(
            intent=intent,
            net_state=net_state,
            guardian=guardian,
            tx_plan=tx_plan,
        )

        # 5) Protocol graph choice (advisory)
        protocol_graph_choice = self._safe_protocol_graph_choice(
            intent_kind=self._intent_kind(intent),
            median_fee=median_fee,
            recommended_fee=recommended_fee,
            guardian_mode=self._guardian_mode(guardian),
        )

        # 6) Execution hints + offline instructions
        execution_hint = self._build_execution_hint(
            band=band,
            quantum=quantum,
        )
        offline_instructions = self._build_offline_instructions(
            intent_dict=self._intent_as_dict(intent),
            safe_fee=safe_fee,
        )

        # 7) Safety metadata
        safety = {
            "signing": "out_of_scope",
            "submission": "out_of_scope",
            "scope": "read_only_planning",
            "warnings": [
                "Do NOT paste seeds or private keys into this system.",
                "Engine output is advisory and must be reviewed by an operator.",
            ],
        }

        bundle: Dict[str, Any] = {
            "execution_version": self.VERSION,
            "protocol": tx_plan.get("protocol"),
            "intent": self._intent_as_dict(intent),
            "network_state": net_state,
            "guardian_mode": self._guardian_mode(guardian),
            "quantum": quantum,
            "scheduler_band": scheduler_band or band,
            "fee": {
                "median_fee_drops": median_fee,
                "recommended_fee_drops": recommended_fee,
                "safe_fee_drops": safe_fee,
            },
            "execution_hint": execution_hint,
            "offline_instructions": offline_instructions,
            "safety": safety,
            "raw": {
                "tx_plan": tx_plan,
                "router_decision": router_decision,
                "protocol_graph": protocol_graph_choice,
                "guardian": guardian,
                "pipeline_raw": pipeline_raw,
            },
        }

        return bundle

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _safe_run_pipeline(
        self,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], str, Dict[str, Any]]:
        """
        Run VQM pipeline safely. If anything fails, we fabricate a minimal,
        conservative snapshot.
        """
        net_state: Dict[str, Any]
        guardian: Dict[str, Any]
        pipeline_raw: Dict[str, Any]
        scheduler_band: str
        fee_horizon: Dict[str, Any]

        if run_vqm_cycle_v5 is None:
            # Hard fallback: no pipeline at all.
            net_state = {
                "ledger_seq": 0,
                "load_factor": 1.0,
                "txn_median_fee": 10,
                "recommended_fee_drops": 10,
                "txn_base_fee": 10,
            }
            guardian = {}
            pipeline_raw = {}
            scheduler_band = "normal"
            fee_horizon = {}
            return net_state, guardian, pipeline_raw, scheduler_band, fee_horizon

        state = run_vqm_cycle_v5()

        net_state = state.get("network_state", {}) or {}
        guardian = state.get("guardian", {}) or {}
        scheduler_block = state.get("scheduler", {}) or {}
        fee_horizon = state.get("fee_horizon", {}) or {}
        scheduler_band = scheduler_block.get("band", "normal")

        pipeline_raw = {
            "pipeline_version": state.get("pipeline_version"),
            "scheduler": scheduler_block,
            "timestamp": state.get("timestamp"),
            "fee_horizon": fee_horizon,
            "tools": state.get("tools", []),
        }

        return net_state, guardian, pipeline_raw, scheduler_band, fee_horizon

    def _safe_quantum(
        self,
        net_state: Dict[str, Any],
        guardian: Dict[str, Any],
        fee_horizon: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compute quantum signal; if the dedicated module is missing or
        crashes, gracefully fall back to a simple rule-based band.
        """
        median_fee = int(net_state.get("txn_median_fee", 10))
        recommended_fee = int(net_state.get("recommended_fee_drops", median_fee))

        if compute_quantum_signal is not None:
            try:
                return compute_quantum_signal(
                    network_state=net_state,
                    guardian=guardian,
                    fee_horizon=fee_horizon,
                )
            except Exception:
                # Fall back to heuristic below
                pass

        # Heuristic fallback (self-healing)
        if median_fee <= 20:
            band = "low"
        elif median_fee <= 200:
            band = "normal"
        elif median_fee <= 2000:
            band = "elevated"
        else:
            band = "extreme"

        safe_fee = int(max(median_fee, recommended_fee) * 1.1)

        return {
            "version": "fallback-0.1.0",
            "band": band,
            "median_fee_drops": median_fee,
            "recommended_fee_drops": recommended_fee,
            "safe_fee_drops": safe_fee,
            "pressure_score": 1.0 if band in ("elevated", "extreme") else 0.3,
            "guardian_mode": self._guardian_mode(guardian),
            "notes": [
                "Fallback quantum signal (compute_quantum_signal unavailable)."
            ],
        }

    def _safe_tx_plan(
        self,
        intent: Any,
        net_state: Dict[str, Any],
        guardian: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ask the TransactionProtocolBrain for a plan. If it's missing,
        default to a simple static payment-v1 style plan.
        """
        if tx_brain is not None:
            try:
                return tx_brain.plan_for_intent(intent, net_state, guardian)
            except Exception:
                pass

        # Minimal fallback plan
        return {
            "intent_kind": self._intent_kind(intent),
            "network_state": {
                "ledger_seq": net_state.get("ledger_seq"),
                "load_factor": net_state.get("load_factor"),
                "txn_median_fee": net_state.get("txn_median_fee"),
                "recommended_fee_drops": net_state.get(
                    "recommended_fee_drops", net_state.get("txn_median_fee", 10)
                ),
                "safe_fee_drops": int(
                    net_state.get("txn_median_fee", 10) * 1.1
                ),
            },
            "protocol": "simple_payment_v1",
            "risk": {
                "level": 1,
                "reasons": ["fallback_tx_plan"],
            },
            "steps": [
                {
                    "name": "check_accounts",
                    "details": {
                        "source": self._intent_field(intent, "source_account"),
                        "destination": self._intent_field(
                            intent, "destination_account"
                        ),
                    },
                },
                {
                    "name": "estimate_fee",
                    "details": {
                        "median_fee": net_state.get("txn_median_fee", 10),
                        "recommended_fee": net_state.get(
                            "recommended_fee_drops",
                            net_state.get("txn_median_fee", 10),
                        ),
                    },
                },
                {
                    "name": "prepare_payment_instruction",
                    "details": {
                        "amount_drops": self._intent_field(
                            intent, "amount_drops", default=0
                        ),
                    },
                },
            ],
        }

    def _safe_router_decision(
        self,
        intent: Any,
        net_state: Dict[str, Any],
        guardian: Dict[str, Any],
        tx_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ask TxRouterV3 for advice. Fallback: echo the tx_plan protocol.
        """
        if self._router is not None:
            try:
                return self._router.route(
                    intent=intent,
                    network_state=net_state,
                    guardian_hint=guardian,
                    tx_plan=tx_plan,
                )
            except Exception:
                pass

        # Fallback: emulate a single-candidate router decision
        protocol = tx_plan.get("protocol", "simple_payment_v1")
        risk = tx_plan.get("risk", {})
        base_level = risk.get("level", 1)
        final_level = max(base_level, 1)
        band = "normal"
        median_fee = int(net_state.get("txn_median_fee", 10))

        return {
            "candidates": [
                {
                    "protocol": protocol,
                    "reason": "fallback_router",
                    "risk": {"base_level": base_level, "final_level": final_level},
                    "score": 0.5,
                }
            ],
            "selected": {
                "protocol": protocol,
                "reason": "fallback_router",
                "risk": {"base_level": base_level, "final_level": final_level},
                "score": 0.5,
            },
            "meta": {
                "band": band,
                "guardian_mode": self._guardian_mode(guardian),
                "median_fee": median_fee,
                "recommended_fee": int(
                    net_state.get("recommended_fee_drops", median_fee)
                ),
                "load_factor": net_state.get("load_factor", 1.0),
                "notes": ["Fallback router decision (TxRouterV3 unavailable)."],
            },
        }

    def _safe_protocol_graph_choice(
        self,
        intent_kind: str,
        median_fee: int,
        recommended_fee: int,
        guardian_mode: str,
    ) -> Dict[str, Any]:
        """
        Advisory protocol graph selection. If ProtocolSelector is missing
        or fails, we emit a minimal advisory object.
        """
        if self._selector is not None:
            try:
                band = self._band_from_fee(median_fee)
                risk_budget = 3
                choice = self._selector.select_for_intent(
                    intent_kind=intent_kind,
                    band=band,
                    median_fee=median_fee,
                    recommended_fee=recommended_fee,
                    guardian_mode=guardian_mode,
                    risk_budget=risk_budget,
                )
                return choice
            except Exception:
                pass

        # Simple fallback choice: mimic schema
        return {
            "protocol": "simple_payment_v1",
            "reason": "fallback_protocol_graph",
            "risk_level": 1,
            "score": 0.25,
        }

    # ------------------------------------------------------------------ #
    # Execution hint + offline instructions
    # ------------------------------------------------------------------ #

    def _build_execution_hint(
        self,
        band: str,
        quantum: Dict[str, Any],
    ) -> Dict[str, Any]:
        pressure = float(quantum.get("pressure_score", 0.0))

        if band in ("extreme", "elevated") or pressure >= 0.9:
            mode = "delayed_or_batched"
            backoff = 60
            window = 15 * 60
            urgency = "high"
            notes = [
                f"Network band={band} or pressure>={pressure:.2f}.",
                "Avoid unnecessary transactions.",
                "Prefer batching / delaying non-critical flows.",
            ]
        elif band == "normal":
            mode = "normal"
            backoff = 0
            window = 0
            urgency = "normal"
            notes = [
                "Network in normal band.",
                "Standard execution acceptable.",
            ]
        else:
            mode = "aggressive"
            backoff = 0
            window = 0
            urgency = "low"
            notes = [
                f"Network band={band}.",
                "Fees inexpensive; safe to proceed for most flows.",
            ]

        return {
            "recommended_mode": mode,
            "backoff_seconds": backoff,
            "batch_window_seconds": window,
            "urgency": urgency,
            "notes": notes,
        }

    def _build_offline_instructions(
        self,
        intent_dict: Dict[str, Any],
        safe_fee: int,
    ) -> List[Dict[str, Any]]:
        src = intent_dict.get("source_account")
        dst = intent_dict.get("destination_account")
        amt = intent_dict.get("amount_drops", 0)

        return [
            {
                "step": "construct_payment_json",
                "details": {
                    "description": "Build XRPL Payment transaction JSON offline.",
                    "transaction": {
                        "TransactionType": "Payment",
                        "Account": src,
                        "Destination": dst,
                        "Amount": str(amt),
                        "Fee": str(safe_fee),
                        "Flags": 0x80000000,
                        "Sequence": "FILL_ME_FROM_ACCOUNT_INFO",
                        "SigningPubKey": "FILL_ME_WITH_WALLET_PUBKEY",
                        "TxnSignature": "FILL_ME_WITH_OFFLINE_SIGNATURE",
                    },
                },
            },
            {
                "step": "sign_offline",
                "details": {
                    "description": "Sign the transaction with a wallet/SDK you control.",
                    "constraints": [
                        "Signing MUST be done outside this engine.",
                        "Private keys MUST NEVER be provided to this system.",
                        "Use hardware wallet or secure signing device where possible.",
                    ],
                },
            },
            {
                "step": "submit_via_wallet_or_node",
                "details": {
                    "description": "Submit signed transaction via your own XRPL node or wallet provider.",
                    "note": "This engine does NOT submit or broadcast transactions.",
                },
            },
        ]

    # ------------------------------------------------------------------ #
    # Tiny utilities
    # ------------------------------------------------------------------ #

    @staticmethod
    def _intent_kind(intent: Any) -> str:
        if intent is None:
            return "unknown"
        return getattr(intent, "kind", None) or getattr(intent, "type", "unknown")

    @staticmethod
    def _intent_field(intent: Any, name: str, default: Any = None) -> Any:
        if intent is None:
            return default
        if hasattr(intent, name):
            return getattr(intent, name)
        # maybe dict-like
        if hasattr(intent, "get"):
            try:
                return intent.get(name, default)
            except Exception:
                return default
        return default

    @staticmethod
    def _intent_as_dict(intent: Any) -> Dict[str, Any]:
        if intent is None:
            return {}
        # TxIntent has as_dict()
        if hasattr(intent, "as_dict"):
            try:
                return intent.as_dict()
            except Exception:
                pass
        if hasattr(intent, "__dict__"):
            try:
                return dict(intent.__dict__)
            except Exception:
                pass
        if hasattr(intent, "get"):
            try:
                # assume mapping
                return dict(intent)  # type: ignore[arg-type]
            except Exception:
                pass
        return {}

    @staticmethod
    def _guardian_mode(guardian: Dict[str, Any]) -> str:
        if not guardian:
            return "unknown"
        llm = guardian.get("llm") or {}
        mode = llm.get("mode")
        if mode:
            return str(mode)
        mesh = guardian.get("mesh") or {}
        return str(mesh.get("mode", "unknown"))

    @staticmethod
    def _band_from_fee(median_fee: int) -> str:
        if median_fee <= 20:
            return "low"
        if median_fee <= 200:
            return "normal"
        if median_fee <= 2000:
            return "elevated"
        return "extreme"


# ---------------------------------------------------------------------------
# Module-level helper for callers that expect `plan_execution(...)`
# ---------------------------------------------------------------------------


def plan_execution(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Thin convenience wrapper so callers can simply:

        from ecosystem.execution import plan_execution
        bundle = plan_execution(intent)

    It instantiates an ExecutionPlanner and forwards all arguments.
    """
    planner = ExecutionPlanner()
    return planner.plan_execution(*args, **kwargs)
