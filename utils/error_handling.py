"""
Enhanced error handling utilities for better user experience and debugging.

Provides structured error handling with user-friendly messages and proper error classification.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Type, Union
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for better classification and handling."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    NETWORK = "network"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


class UserFriendlyError:
    """Structured error with user-friendly messaging."""
    
    def __init__(
        self,
        category: ErrorCategory,
        user_message: str,
        technical_details: str,
        suggestions: Optional[list[str]] = None,
        error_code: Optional[str] = None
    ):
        self.category = category
        self.user_message = user_message
        self.technical_details = technical_details
        self.suggestions = suggestions or []
        self.error_code = error_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": "error",
            "category": self.category.value,
            "message": self.user_message,
            "technical_details": self.technical_details,
            "suggestions": self.suggestions,
            "error_code": self.error_code
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ErrorClassifier:
    """Classifies exceptions into user-friendly error categories."""
    
    @staticmethod
    def classify_exception(exception: Exception) -> ErrorCategory:
        """Classify an exception into an appropriate category."""
        error_str = str(exception).lower()
        exception_type = type(exception).__name__
        
        # Validation errors
        if "validation" in error_str or "pydantic" in error_str:
            return ErrorCategory.VALIDATION
        if exception_type in ["ValidationError", "ValueError", "TypeError"]:
            return ErrorCategory.VALIDATION
        
        # Authentication/Permission errors
        if any(keyword in error_str for keyword in ["auth", "token", "key", "credential", "unauthorized"]):
            return ErrorCategory.AUTHENTICATION
        if any(keyword in error_str for keyword in ["permission", "access", "forbidden"]):
            return ErrorCategory.PERMISSION
        
        # Network errors
        if any(keyword in error_str for keyword in ["connection", "network", "timeout", "http", "ssl"]):
            return ErrorCategory.NETWORK
        if exception_type in ["ConnectionError", "TimeoutError", "HTTPError"]:
            return ErrorCategory.NETWORK
        
        # Resource errors
        if any(keyword in error_str for keyword in ["memory", "disk", "file not found", "no space"]):
            return ErrorCategory.RESOURCE
        if exception_type in ["FileNotFoundError", "MemoryError", "OSError"]:
            return ErrorCategory.RESOURCE
        
        # Configuration errors
        if any(keyword in error_str for keyword in ["config", "environment", "missing", "not found"]):
            return ErrorCategory.CONFIGURATION
        
        # Runtime errors
        if exception_type in ["RuntimeError", "ImportError", "ModuleNotFoundError"]:
            return ErrorCategory.RUNTIME
        
        return ErrorCategory.UNKNOWN
    
    @staticmethod
    def create_user_friendly_error(exception: Exception, context: str = "") -> UserFriendlyError:
        """Create a user-friendly error from an exception."""
        category = ErrorClassifier.classify_exception(exception)
        exception_type = type(exception).__name__
        error_str = str(exception)
        
        # Generate user-friendly message based on category
        if category == ErrorCategory.VALIDATION:
            user_message = "Invalid input provided"
            suggestions = [
                "Check that all required fields are provided",
                "Verify that field values are in the correct format",
                "Review the tool documentation for parameter requirements"
            ]
        elif category == ErrorCategory.AUTHENTICATION:
            user_message = "Authentication failed"
            suggestions = [
                "Check that your API keys are correctly configured",
                "Verify that your credentials haven't expired",
                "Ensure the API key has the necessary permissions"
            ]
        elif category == ErrorCategory.PERMISSION:
            user_message = "Access denied"
            suggestions = [
                "Check file and directory permissions",
                "Verify you have access to the requested resource",
                "Ensure the operation is allowed in your current context"
            ]
        elif category == ErrorCategory.NETWORK:
            user_message = "Network connection failed"
            suggestions = [
                "Check your internet connection",
                "Verify the service is available",
                "Try again in a few moments"
            ]
        elif category == ErrorCategory.RESOURCE:
            user_message = "Resource unavailable"
            suggestions = [
                "Check that the file or resource exists",
                "Verify sufficient disk space or memory",
                "Ensure the resource is accessible"
            ]
        elif category == ErrorCategory.CONFIGURATION:
            user_message = "Configuration error"
            suggestions = [
                "Check your environment variables and configuration files",
                "Verify all required settings are properly configured",
                "Review the setup documentation"
            ]
        elif category == ErrorCategory.RUNTIME:
            user_message = "Runtime error occurred"
            suggestions = [
                "Check that all dependencies are properly installed",
                "Verify the environment is correctly set up",
                "Try restarting the service"
            ]
        else:
            user_message = "An unexpected error occurred"
            suggestions = [
                "Try the operation again",
                "Check the logs for more details",
                "Contact support if the issue persists"
            ]
        
        # Add context to user message if provided
        if context:
            user_message = f"{user_message} in {context}"
        
        return UserFriendlyError(
            category=category,
            user_message=user_message,
            technical_details=f"{exception_type}: {error_str}",
            suggestions=suggestions,
            error_code=f"{category.value.upper()}_{exception_type.upper()}"
        )


def handle_tool_error(exception: Exception, tool_name: str, operation: str = "") -> str:
    """
    Handle tool errors with user-friendly messaging.
    
    Args:
        exception: The exception that occurred
        tool_name: Name of the tool where the error occurred
        operation: Optional description of the operation that failed
    
    Returns:
        JSON string with structured error information
    """
    context = f"{tool_name} tool"
    if operation:
        context += f" during {operation}"
    
    friendly_error = ErrorClassifier.create_user_friendly_error(exception, context)
    
    # Log the technical details for debugging
    logger.error(f"Error in {context}: {friendly_error.technical_details}", exc_info=True)
    
    return friendly_error.to_json()


def handle_validation_error(exception: Exception, field_name: str = "") -> str:
    """
    Handle validation errors with specific field information.
    
    Args:
        exception: The validation exception
        field_name: Optional name of the field that failed validation
    
    Returns:
        JSON string with structured validation error information
    """
    context = f"field '{field_name}'" if field_name else "input validation"
    
    # Extract Pydantic validation details if available
    suggestions = [
        "Check that all required fields are provided",
        "Verify that field values are in the correct format"
    ]
    
    if hasattr(exception, 'errors'):
        # Pydantic ValidationError
        try:
            errors = exception.errors()
            if errors:
                first_error = errors[0]
                field = ".".join(str(loc) for loc in first_error.get('loc', []))
                msg = first_error.get('msg', str(exception))
                suggestions.insert(0, f"Fix the '{field}' field: {msg}")
        except Exception:
            pass
    
    friendly_error = UserFriendlyError(
        category=ErrorCategory.VALIDATION,
        user_message=f"Invalid input for {context}",
        technical_details=str(exception),
        suggestions=suggestions,
        error_code="VALIDATION_ERROR"
    )
    
    logger.error(f"Validation error in {context}: {friendly_error.technical_details}")
    
    return friendly_error.to_json()
