ALLOWED_IMAGE_MIME = {"image/png","image/jpeg"}
ALLOWED_TEXT_MIME = {"text/plain"}
ALLOWED_DOC_MIME = {"text/csv","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
MAX_FILE_MB = 20


def validate_file(content_type: str, size_bytes: int, allowed: set):
    if content_type not in allowed:
        return False, f"Unsupported content type: {content_type}"
    if size_bytes > MAX_FILE_MB * 1024 * 1024:
        return False, f"File too large (> {MAX_FILE_MB}MB)"
    return True, "ok"