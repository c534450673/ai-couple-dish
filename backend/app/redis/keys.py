def logout_blacklist_key(jti: str) -> str:
    if not jti or ":" in jti:
        raise ValueError("invalid jti")
    return f"logout:blacklist:{jti}"


def verify_code_key(phone: str) -> str:
    return f"user:verify:code:{phone}"


def couple_code_key(code: str) -> str:
    return f"couple:code:{code}"
