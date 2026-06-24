import httpx
import logging

log = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:8000"


def post_session(session_data: dict) -> bool:
    """POST parsed session data to the backend. Returns True on success."""
    try:
        resp = httpx.post(f"{BACKEND_URL}/api/sessions", json=session_data, timeout=30)
        if resp.status_code == 409:
            log.info(f"Session already exists, skipping: {session_data.get('filename')}")
            return True
        resp.raise_for_status()
        log.info(f"Session uploaded: {session_data.get('filename')} → id {resp.json().get('id')}")
        return True
    except Exception as e:
        log.error(f"Failed to upload session {session_data.get('filename')}: {e}")
        return False
