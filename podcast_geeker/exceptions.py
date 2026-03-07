class PodcastGeekerError(Exception):
    """Base exception class for Podcast Geeker errors."""

    pass


class DatabaseOperationError(PodcastGeekerError):
    """Raised when a database operation fails."""

    pass


class UnsupportedTypeException(PodcastGeekerError):
    """Raised when an unsupported type is provided."""

    pass


class InvalidInputError(PodcastGeekerError):
    """Raised when invalid input is provided."""

    pass


class NotFoundError(PodcastGeekerError):
    """Raised when a requested resource is not found."""

    pass


class AuthenticationError(PodcastGeekerError):
    """Raised when there's an authentication problem."""

    pass


class ConfigurationError(PodcastGeekerError):
    """Raised when there's a configuration problem."""

    pass


class ExternalServiceError(PodcastGeekerError):
    """Raised when an external service (e.g., AI model) fails."""

    pass


class RateLimitError(PodcastGeekerError):
    """Raised when a rate limit is exceeded."""

    pass


class FileOperationError(PodcastGeekerError):
    """Raised when a file operation fails."""

    pass


class NetworkError(PodcastGeekerError):
    """Raised when a network operation fails."""

    pass


class NoTranscriptFound(PodcastGeekerError):
    """Raised when no transcript is found for a video."""

    pass
