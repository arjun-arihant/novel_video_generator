"""
Custom Exceptions for Novel Video Generator

Provides a comprehensive exception hierarchy for better error handling
and debugging throughout the pipeline.
"""


class NovelVideoError(Exception):
    """Base exception for all novel video generator errors."""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization."""
        return {
            'error': self.code,
            'message': self.message,
            'details': self.details
        }


class ConfigurationError(NovelVideoError):
    """Raised when there's a configuration issue."""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(
            message=message,
            code='CONFIGURATION_ERROR',
            details={'config_key': config_key} if config_key else {}
        )


class ValidationError(NovelVideoError):
    """Raised when input data validation fails."""
    
    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(
            message=message,
            code='VALIDATION_ERROR',
            details={
                'field': field,
                'value': str(value) if value is not None else None
            }
        )


class APIError(NovelVideoError):
    """Raised when an external API call fails."""
    
    def __init__(
        self, 
        message: str, 
        service: str = None,
        status_code: int = None,
        response_text: str = None,
        retryable: bool = False
    ):
        super().__init__(
            message=message,
            code='API_ERROR',
            details={
                'service': service,
                'status_code': status_code,
                'response_preview': response_text[:200] if response_text else None,
                'retryable': retryable
            }
        )
        self.service = service
        self.status_code = status_code
        self.retryable = retryable


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, service: str, retry_after: int = None):
        super().__init__(
            message=f'Rate limit exceeded for {service}',
            service=service,
            status_code=429,
            retryable=True
        )
        self.details['retry_after'] = retry_after


class SceneExtractionError(NovelVideoError):
    """Raised when scene extraction fails."""
    
    def __init__(self, message: str, chapter_number: int = None):
        super().__init__(
            message=message,
            code='SCENE_EXTRACTION_ERROR',
            details={'chapter_number': chapter_number}
        )


class ImageGenerationError(NovelVideoError):
    """Raised when image generation fails."""
    
    def __init__(
        self, 
        message: str, 
        scene_index: int = None,
        prompt: str = None
    ):
        super().__init__(
            message=message,
            code='IMAGE_GENERATION_ERROR',
            details={
                'scene_index': scene_index,
                'prompt_preview': prompt[:100] if prompt else None
            }
        )


class AudioGenerationError(NovelVideoError):
    """Raised when audio/TTS generation fails."""
    
    def __init__(
        self,
        message: str,
        scene_index: int = None,
        voice: str = None
    ):
        super().__init__(
            message=message,
            code='AUDIO_GENERATION_ERROR',
            details={
                'scene_index': scene_index,
                'voice': voice
            }
        )


class VideoCompositionError(NovelVideoError):
    """Raised when video composition fails."""
    
    def __init__(
        self,
        message: str,
        scene_count: int = None,
        output_path: str = None
    ):
        super().__init__(
            message=message,
            code='VIDEO_COMPOSITION_ERROR',
            details={
                'scene_count': scene_count,
                'output_path': output_path
            }
        )


class ResourceNotFoundError(NovelVideoError):
    """Raised when a required resource (file, model, etc.) is not found."""
    
    def __init__(self, message: str, resource_path: str = None):
        super().__init__(
            message=message,
            code='RESOURCE_NOT_FOUND',
            details={'resource_path': resource_path}
        )


class PipelineError(NovelVideoError):
    """Raised when pipeline execution fails."""
    
    def __init__(
        self,
        message: str,
        step: str = None,
        context: dict = None
    ):
        super().__init__(
            message=message,
            code='PIPELINE_ERROR',
            details={
                'step': step,
                'context': context or {}
            }
        )


class TimeoutError(NovelVideoError):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, operation: str = None, timeout_seconds: float = None):
        super().__init__(
            message=message,
            code='TIMEOUT_ERROR',
            details={
                'operation': operation,
                'timeout_seconds': timeout_seconds
            }
        )


class CancelledError(NovelVideoError):
    """Raised when an operation is cancelled."""
    
    def __init__(self, message: str = 'Operation was cancelled'):
        super().__init__(
            message=message,
            code='CANCELLED'
        )


def format_exception_for_logging(exc: Exception) -> dict:
    """
    Format any exception for logging.
    
    Args:
        exc: The exception to format
        
    Returns:
        Dictionary with error details
    """
    if isinstance(exc, NovelVideoError):
        return exc.to_dict()
    
    return {
        'error': exc.__class__.__name__,
        'message': str(exc),
        'details': {}
    }
