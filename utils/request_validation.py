"""
Enhanced request validation utilities for comprehensive input validation.

Provides additional validation layers beyond the existing security validation.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class RequestSizeValidator:
    """Validates request sizes to prevent resource exhaustion."""
    
    # Size limits in bytes
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB total request
    MAX_FIELD_SIZE = 1 * 1024 * 1024     # 1MB per field
    MAX_ARRAY_LENGTH = 1000              # Max array elements
    MAX_STRING_LENGTH = 100_000          # Max string length
    
    @classmethod
    def validate_request_size(cls, request_data: Dict[str, Any]) -> Optional[str]:
        """
        Validate the overall size and structure of a request.

        Args:
            request_data: The request data to validate

        Returns:
            Error message if validation fails, None if valid
        """
        try:
            # Filter out non-serializable objects before JSON serialization
            serializable_data = cls._filter_serializable_data(request_data)

            # Check total request size
            request_json = json.dumps(serializable_data, ensure_ascii=False)
            request_size = len(request_json.encode('utf-8'))

            if request_size > cls.MAX_REQUEST_SIZE:
                return f"Request too large: {request_size:,} bytes (max: {cls.MAX_REQUEST_SIZE:,} bytes)"

            # Check individual fields (use original data for field validation)
            for key, value in request_data.items():
                # Skip internal/system fields that aren't user-provided
                if key.startswith('_'):
                    continue

                error = cls._validate_field(key, value)
                if error:
                    return error

            return None

        except Exception as e:
            logger.error(f"Error validating request size: {e}")
            return f"Request validation error: {str(e)}"

    @classmethod
    def _filter_serializable_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out non-serializable objects from request data.

        This method removes objects that cannot be JSON serialized, such as:
        - ModelContext objects
        - Provider objects
        - Other complex internal objects

        Args:
            data: Original request data

        Returns:
            Dictionary with only JSON-serializable data
        """
        serializable_data = {}

        for key, value in data.items():
            # Skip internal/system fields that start with underscore
            if key.startswith('_'):
                continue

            # Check if value is JSON serializable
            try:
                json.dumps(value, ensure_ascii=False)
                serializable_data[key] = value
            except (TypeError, ValueError):
                # Skip non-serializable values
                # Log for debugging but don't fail validation
                logger.debug(f"Skipping non-serializable field '{key}' of type {type(value).__name__}")
                continue

        return serializable_data

    @classmethod
    def _validate_field(cls, field_name: str, value: Any) -> Optional[str]:
        """Validate an individual field."""
        if isinstance(value, str):
            if len(value) > cls.MAX_STRING_LENGTH:
                return f"Field '{field_name}' too long: {len(value):,} characters (max: {cls.MAX_STRING_LENGTH:,})"
        
        elif isinstance(value, (list, tuple)):
            if len(value) > cls.MAX_ARRAY_LENGTH:
                return f"Field '{field_name}' has too many elements: {len(value):,} (max: {cls.MAX_ARRAY_LENGTH:,})"
            
            # Check each element in the array
            for i, item in enumerate(value):
                if isinstance(item, str) and len(item) > cls.MAX_FIELD_SIZE:
                    return f"Field '{field_name}[{i}]' too large: {len(item):,} bytes (max: {cls.MAX_FIELD_SIZE:,})"
        
        elif isinstance(value, dict):
            # Recursively validate nested objects
            for nested_key, nested_value in value.items():
                error = cls._validate_field(f"{field_name}.{nested_key}", nested_value)
                if error:
                    return error
        
        return None


class SimpleRateLimiter:
    """Simple in-memory rate limiter to prevent abuse."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> tuple[bool, Optional[str]]:
        """
        Check if a request is allowed for the given identifier.
        
        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        request_times = self.requests[identifier]
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # Check if limit exceeded
        if len(request_times) >= self.max_requests:
            return False, f"Rate limit exceeded: {len(request_times)} requests in {self.window_seconds}s (max: {self.max_requests})"
        
        # Add current request
        request_times.append(now)
        return True, None


class ContentValidator:
    """Validates content for potentially harmful patterns."""
    
    # Patterns that might indicate malicious input
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>',
        r'javascript:',
        r'data:text/html',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'eval\s*\(',
        r'exec\s*\(',
        r'system\s*\(',
        r'subprocess\s*\.',
        r'os\.system',
        r'__import__',
    ]
    
    @classmethod
    def validate_content_safety(cls, content: str, field_name: str = "content") -> Optional[str]:
        """
        Validate content for potentially harmful patterns.
        
        Args:
            content: Content to validate
            field_name: Name of the field being validated
            
        Returns:
            Error message if validation fails, None if valid
        """
        if not isinstance(content, str):
            return None
        
        import re
        
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Suspicious pattern detected in {field_name}: {pattern}")
                return f"Content in '{field_name}' contains potentially unsafe patterns"
        
        return None


class EnhancedRequestValidator:
    """Comprehensive request validator combining all validation types."""
    
    def __init__(self, enable_rate_limiting: bool = True):
        self.size_validator = RequestSizeValidator()
        self.content_validator = ContentValidator()
        self.rate_limiter = SimpleRateLimiter() if enable_rate_limiting else None
    
    def validate_request(
        self, 
        request_data: Dict[str, Any], 
        client_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Perform comprehensive request validation.
        
        Args:
            request_data: The request data to validate
            client_id: Optional client identifier for rate limiting
            
        Returns:
            Error message if validation fails, None if valid
        """
        # Rate limiting check
        if self.rate_limiter and client_id:
            allowed, error = self.rate_limiter.is_allowed(client_id)
            if not allowed:
                return error
        
        # Size validation
        size_error = self.size_validator.validate_request_size(request_data)
        if size_error:
            return size_error
        
        # Content safety validation
        for key, value in request_data.items():
            if isinstance(value, str):
                content_error = self.content_validator.validate_content_safety(value, key)
                if content_error:
                    return content_error
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        content_error = self.content_validator.validate_content_safety(item, f"{key}[{i}]")
                        if content_error:
                            return content_error
        
        return None


# Global validator instance
_global_validator = None

def get_request_validator() -> EnhancedRequestValidator:
    """Get the global request validator instance."""
    global _global_validator
    if _global_validator is None:
        # Check if rate limiting should be enabled
        import os
        enable_rate_limiting = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
        _global_validator = EnhancedRequestValidator(enable_rate_limiting=enable_rate_limiting)
    return _global_validator


def validate_tool_request(request_data: Dict[str, Any], client_id: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to validate a tool request.
    
    Args:
        request_data: The request data to validate
        client_id: Optional client identifier for rate limiting
        
    Returns:
        Error message if validation fails, None if valid
    """
    validator = get_request_validator()
    return validator.validate_request(request_data, client_id)
