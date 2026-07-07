"""Unit tests for the deterministic gate — the invariants the whole system rests on.

Run: uv run pytest
Pure stdlib + app.gate: these must be green before any agent work happens.
"""

from datetime import datetime, timedelta, timezone

from app.gate import (
    ConsentBasis,
    ConsentEvidence,
    MessageChecks,
    evaluate_recipient,
)

NOW = datetime(2026, 7, 2, tzinfo=timezone.utc)
CLEAN_MSG = MessageChecks(has_sender_identity=True, has_unsubscribe=True)


def _evidence(basis, days_ago=None, channel="email", contact="c_x"):
    granted = NOW - timedelta(days=days_ago) if days_ago is not None else None
    return ConsentEvidence(contact, channel, basis, granted, "test", "test wording")


def test_express_consent_passes():
    d = evaluate_recipient(_evidence(ConsentBasis.EXPRESS, 600), CLEAN_MSG, "email", now=NOW)
    assert d.allowed


def test_implied_purchase_within_window_passes():
    d = evaluate_recipient(_evidence(ConsentBasis.IMPLIED_PURCHASE, 180), CLEAN_MSG, "email", now=NOW)
    assert d.allowed


def test_implied_inquiry_expired_blocks():
    # CASL inquiry window is 183 days — 224 days ago must block.
    d = evaluate_recipient(_evidence(ConsentBasis.IMPLIED_INQUIRY, 224), CLEAN_MSG, "email", now=NOW)
    assert not d.allowed
    assert any("EXPIRED" in r for r in d.reasons)


def test_withdrawn_blocks():
    d = evaluate_recipient(_evidence(ConsentBasis.WITHDRAWN, 30), CLEAN_MSG, "email", now=NOW)
    assert not d.allowed


def test_no_record_fails_closed():
    d = evaluate_recipient(_evidence(ConsentBasis.NONE), CLEAN_MSG, "email", now=NOW)
    assert not d.allowed
    assert any("fail-closed" in r for r in d.reasons)


def test_channel_mismatch_blocks():
    # SMS consent must not authorize an email send.
    d = evaluate_recipient(
        _evidence(ConsentBasis.EXPRESS, 100, channel="sms"), CLEAN_MSG, "email", now=NOW
    )
    assert not d.allowed
    assert any("channel mismatch" in r for r in d.reasons)


def test_missing_unsubscribe_blocks_even_with_express_consent():
    msg = MessageChecks(has_sender_identity=True, has_unsubscribe=False)
    d = evaluate_recipient(_evidence(ConsentBasis.EXPRESS, 10), msg, "email", now=NOW)
    assert not d.allowed


def test_verifier_confirmed_violation_tightens_gate():
    # Facts pass, but a verifier-confirmed violation must still block.
    d = evaluate_recipient(
        _evidence(ConsentBasis.EXPRESS, 10), CLEAN_MSG, "email",
        verifier_confirmed_violations=["consent wording did not name the sender"],
        now=NOW,
    )
    assert not d.allowed


def test_agent_opinion_cannot_open_gate():
    # THE core security property: no agent input exists that flips a facts-fail
    # to PASS. Empty violations list + failing facts must still block.
    d = evaluate_recipient(
        _evidence(ConsentBasis.NONE), CLEAN_MSG, "email",
        verifier_confirmed_violations=[],  # verifier says "all clear"
        now=NOW,
    )
    assert not d.allowed
