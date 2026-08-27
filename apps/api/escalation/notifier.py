"""
escalation/notifier.py — Family/emergency contact SMS alert.

Simulated SMS provider for hackathon build.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def send_family_alert(destination_number: str, call_id: str, verdict: str, message: str) -> dict:
    """
    Send an SMS alert to a family/emergency contact.
    """
    if verdict != "CRITICAL":
        return {"status": "skipped", "reason": "not critical"}
        
    # SIMULATED — no real SMS provider wired (no free tier available
    # without a card). Swap in a real provider here later if needed.
    log_entry = {
        "to": destination_number,
        "message": message,
        "status": "simulated",
        "ts": datetime.utcnow().isoformat()
    }
    logger.info(f"[SIMULATED SMS] To: {destination_number} | {message}")
    return log_entry
