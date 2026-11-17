from typing import Dict, Any, Optional


class IncuBrixException(Exception):
    """Base exception for all IncuBrix engine errors."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}


class InvalidInputException(IncuBrixException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="INVALID_INPUT",
            message=message,
            status_code=400,
            retryable=False,
            details=details
        )


class AudioValidationException(IncuBrixException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="AUDIO_VALIDATION_ERROR",
            message=message,
            status_code=422,
            retryable=False,
            details=details
        )


class SilentAudioException(IncuBrixException):
    def __init__(self, message: str = "Audio contains no detectable speech or is completely silent.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SILENT_AUDIO_ERROR",
            message=message,
            status_code=422,
            retryable=False,
            details=details
        )


class MusicOnlyAudioException(IncuBrixException):
    def __init__(self, message: str = "Audio appears to be music-only without intelligible narration speech.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="MUSIC_ONLY_AUDIO_ERROR",
            message=message,
            status_code=422,
            retryable=False,
            details=details
        )


class AudioCorruptedException(IncuBrixException):
    def __init__(self, message: str = "Audio file is corrupt or unreadable.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="AUDIO_CORRUPTED_ERROR",
            message=message,
            status_code=422,
            retryable=False,
            details=details
        )


class AudioTooLongException(IncuBrixException):
    def __init__(self, message: str = "Audio duration exceeds maximum allowed limit (10 minutes).", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="AUDIO_TOO_LONG",
            message=message,
            status_code=413,
            retryable=False,
            details=details
        )


class SSRException(IncuBrixException):
    def __init__(self, message: str = "URL target is forbidden or resolves to private/loopback network address.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SSRF_FORBIDDEN",
            message=message,
            status_code=400,
            retryable=False,
            details=details
        )


class NotFoundException(IncuBrixException):
    def __init__(self, message: str = "Requested resource not found.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=message,
            status_code=404,
            retryable=False,
            details=details
        )


class ProviderException(IncuBrixException):
    def __init__(self, message: str, retryable: bool = True, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="PROVIDER_ERROR",
            message=message,
            status_code=502,
            retryable=retryable,
            details=details
        )


class RenderingException(IncuBrixException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RENDERING_ERROR",
            message=message,
            status_code=500,
            retryable=True,
            details=details
        )
