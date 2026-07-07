"""Deterministic, fail-closed compliance gate.

DESIGN PRINCIPLE — the security core of ConsentGuard:
    LLM agents ADVISE. This code DECIDES.

The gate re-derives every verdict from ledger facts. Agent outputs enter only
as `verifier_confirmed_violations`, which can TIGHTEN the gate (block a send
whose facts look clean) but can NEVER OPEN it (no agent text can authorize a
send the ledger facts don't support). This is the structural defense against
prompt injection and hallucination: a compromised agent gains nothing, because
the gate never takes an agent's word for consent.

Rule windows below encode the CASL rule pack (skills/casl-rule-pack). Swapping
jurisdictions = swapping the RulePack constants, not rewriting the gate.
This module is pure stdlib and fully unit-tested (tests/test_gate.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class ConsentBasis(str, Enum):
    """Recognized consent bases, ordered roughly strongest → none."""

    EXPRESS = "express"                  # explicit opt-in; no expiry until withdrawn
    IMPLIED_PURCHASE = "implied_purchase"  # existing business relationship: purchase
    IMPLIED_INQUIRY = "implied_inquiry"    # existing business relationship: inquiry
    WITHDRAWN = "withdrawn"              # unsubscribed / consent revoked
    NONE = "none"                        # no record — fail-closed default


@dataclass(frozen=True)
class RulePack:
    """Jurisdiction-specific time windows (days). Defaults = CASL (Canada).

    CASL: implied consent via purchase lasts 2 years; via inquiry, 6 months.
    Express consent does not expire (until withdrawn). Consent is
    channel-specific: email consent does not cover SMS, and vice versa.
    """

    name: str = "CASL"
    purchase_window_days: int = 730
    inquiry_window_days: int = 183
    express_expires: bool = False


CASL = RulePack()


@dataclass(frozen=True)
class ConsentEvidence:
    """The LATEST consent record for a contact × channel, straight from the ledger.

    `wording` and `source` exist because CASL requires keeping the exact
    consent language and provenance as evidence (3-year retention).
    """

    contact_id: str
    channel: str                      # channel the consent applies to
    basis: ConsentBasis
    granted_at: datetime | None       # None only when basis is NONE
    source: str = ""                  # e.g. "web_form_v3", "pos_purchase"
    wording: str = ""                 # exact opt-in language shown to the contact


@dataclass(frozen=True)
class MessageChecks:
    """Deterministic content checks for the message variant assigned to a recipient."""

    has_sender_identity: bool         # sender name + mailing address + contact method
    has_unsubscribe: bool             # visible, functional unsubscribe mechanism


@dataclass
class GateDecision:
    contact_id: str
    allowed: bool
    reasons: list[str] = field(default_factory=list)  # plain-English, audit-ready

    def as_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "verdict": "PASS" if self.allowed else "BLOCK",
            "reasons": self.reasons,
        }


def consent_is_valid(
    evidence: ConsentEvidence,
    campaign_channel: str,
    now: datetime,
    rules: RulePack = CASL,
) -> tuple[bool, str]:
    """Evaluate one consent record against the rule pack. Returns (valid, reason)."""
    # Channel-specific consent: evidence for another channel is no evidence at all.
    if evidence.channel != campaign_channel:
        return False, (
            f"channel mismatch: consent on '{evidence.channel}' does not cover "
            f"'{campaign_channel}' ({rules.name} consent is channel-specific)"
        )

    if evidence.basis is ConsentBasis.WITHDRAWN:
        return False, "consent withdrawn (unsubscribe on record)"

    if evidence.basis is ConsentBasis.NONE or evidence.granted_at is None:
        return False, "no consent evidence on record (fail-closed)"

    age = now - evidence.granted_at

    if evidence.basis is ConsentBasis.EXPRESS:
        # Express consent persists until withdrawn under CASL.
        return True, f"express consent via {evidence.source or 'unknown source'}"

    if evidence.basis is ConsentBasis.IMPLIED_PURCHASE:
        if age <= timedelta(days=rules.purchase_window_days):
            return True, (
                f"implied consent (purchase {age.days}d ago, within "
                f"{rules.purchase_window_days}d window)"
            )
        return False, (
            f"implied consent EXPIRED (purchase {age.days}d ago exceeds "
            f"{rules.purchase_window_days}d window)"
        )

    if evidence.basis is ConsentBasis.IMPLIED_INQUIRY:
        if age <= timedelta(days=rules.inquiry_window_days):
            return True, (
                f"implied consent (inquiry {age.days}d ago, within "
                f"{rules.inquiry_window_days}d window)"
            )
        return False, (
            f"implied consent EXPIRED (inquiry {age.days}d ago exceeds "
            f"{rules.inquiry_window_days}d window)"
        )

    return False, f"unrecognized consent basis '{evidence.basis}' (fail-closed)"


def evaluate_recipient(
    evidence: ConsentEvidence,
    checks: MessageChecks,
    campaign_channel: str,
    verifier_confirmed_violations: list[str] | None = None,
    now: datetime | None = None,
    rules: RulePack = CASL,
) -> GateDecision:
    """Final, fail-closed verdict for one recipient.

    PASS requires ALL of:
      1. valid consent for this exact channel (from ledger facts),
      2. message carries sender identity AND unsubscribe,
      3. zero verifier-confirmed violations.

    Note the asymmetry (the load-bearing security property):
      - verifier CONFIRMED violations force a BLOCK even if facts pass;
      - verifier opinions can never force a PASS — facts alone gate the send.
    """
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    allowed = True

    ok, reason = consent_is_valid(evidence, campaign_channel, now, rules)
    reasons.append(reason)
    if not ok:
        allowed = False

    if not checks.has_sender_identity:
        allowed = False
        reasons.append("message missing sender identification (name/address/contact)")
    if not checks.has_unsubscribe:
        allowed = False
        reasons.append("message missing functional unsubscribe mechanism")

    for violation in verifier_confirmed_violations or []:
        allowed = False  # agents may tighten the gate — never open it
        reasons.append(f"verifier-confirmed violation: {violation}")

    return GateDecision(contact_id=evidence.contact_id, allowed=allowed, reasons=reasons)
