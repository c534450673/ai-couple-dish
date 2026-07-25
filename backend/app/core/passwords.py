import bcrypt
import structlog

from app.core.errors import BusinessError

logger = structlog.get_logger()


def hash_password(password: str) -> str:
    try:
        encoded = password.encode("utf-8")
    except UnicodeEncodeError as error:
        logger.warning(
            "password_hash_rejected",
            module="auth",
            operation="hash_password",
            result="rejected",
            reason="invalid_utf8",
        )
        raise BusinessError(400, "密码长度不合法", http_status=400) from error
    if not encoded or len(encoded) > 72:
        logger.warning(
            "password_hash_rejected",
            module="auth",
            operation="hash_password",
            result="rejected",
            reason="invalid_byte_length",
        )
        raise BusinessError(400, "密码长度不合法", http_status=400)
    logger.info(
        "password_hash_started",
        module="auth",
        operation="hash_password",
        result="started",
        algorithm="bcrypt",
        rounds=12,
    )
    encoded_hash = bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("ascii")
    logger.info(
        "password_hash_completed",
        module="auth",
        operation="hash_password",
        result="completed",
        algorithm="bcrypt",
        rounds=12,
    )
    return encoded_hash


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        encoded = password.encode("utf-8")
        if not encoded or len(encoded) > 72:
            logger.warning(
                "password_verification_rejected",
                module="auth",
                operation="verify_password",
                result="rejected",
                reason="invalid_byte_length",
            )
            return False
        verified = bcrypt.checkpw(encoded, encoded_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        logger.warning(
            "password_verification_rejected",
            module="auth",
            operation="verify_password",
            result="rejected",
            reason="invalid_input",
        )
        return False
    logger.info(
        "password_verification_completed",
        module="auth",
        operation="verify_password",
        result="matched" if verified else "not_matched",
        algorithm="bcrypt",
    )
    return verified
