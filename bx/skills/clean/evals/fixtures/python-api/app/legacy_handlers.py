def handle_v1_request(payload: dict) -> dict:
    return {"status": "ok", "echo": payload}


def handle_v1_error(code: int) -> dict:
    return {"status": "error", "code": code}
