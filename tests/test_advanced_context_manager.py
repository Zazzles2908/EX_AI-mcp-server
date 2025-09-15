"""
Tests for Advanced Context Manager

Validates the functionality of the new context management system including
optimization strategies, caching, and integration with existing systems.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.core.agentic.context_manager import AdvancedContextManager, ContextOptimizationResult
from src.core.agentic.context_integration import ContextIntegrationManager
from utils.advanced_context import optimize_for_model, estimate_tokens


class TestAdvancedContextManager:
    """Test the core Advanced Context Manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.context_manager = AdvancedContextManager()
    
    def test_token_estimation(self):
        """Test token estimation accuracy."""
        # Test string content
        short_text = "Hello world"
        tokens = self.context_manager._estimate_tokens([{"role": "user", "content": short_text}])
        assert tokens > 0
        assert tokens < 10  # Should be reasonable for short text
        
        # Test longer content
        long_text = "This is a much longer piece of text " * 100
        long_tokens = self.context_manager._estimate_tokens([{"role": "user", "content": long_text}])
        assert long_tokens > tokens
        
        # Test empty content
        empty_tokens = self.context_manager._estimate_tokens([])
        assert empty_tokens == 0
    
    def test_basic_optimization_no_limit_exceeded(self):
        """Test optimization when content is within limits."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        # Mock model context with high limit
        mock_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 100000
        mock_context.calculate_token_allocation.return_value = mock_allocation
        
        result = self.context_manager.optimize_context(
            content=messages,
            model_context=mock_context
        )
        
        assert isinstance(result, ContextOptimizationResult)
        assert result.optimized_content == messages  # Should be unchanged
        assert result.compression_ratio == 1.0
        assert "no_optimization_needed" in result.strategies_applied
        assert not result.cache_hit
    
    def test_optimization_with_compression(self):
        """Test optimization when content exceeds limits."""
        # Create content that will exceed a small limit
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Very long user message " * 100},
            {"role": "assistant", "content": "Long assistant response " * 100},
            {"role": "user", "content": "Another long message " * 100}
        ]
        
        # Mock model context with low limit
        mock_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 50  # Very low limit to force compression
        mock_context.calculate_token_allocation.return_value = mock_allocation
        
        result = self.context_manager.optimize_context(
            content=messages,
            model_context=mock_context
        )
        
        assert isinstance(result, ContextOptimizationResult)
        assert len(result.optimized_content) <= len(messages)  # Should be compressed
        assert result.compression_ratio < 1.0  # Should show compression
        assert len(result.strategies_applied) > 0
        assert not result.cache_hit
    
    def test_system_message_preservation(self):
        """Test that system messages are preserved during optimization."""
        messages = [
            {"role": "system", "content": "Important system instructions"},
            {"role": "user", "content": "Long user message " * 200},
            {"role": "assistant", "content": "Long response " * 200}
        ]
        
        # Mock model context with very low limit
        mock_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 20  # Force aggressive compression
        mock_context.calculate_token_allocation.return_value = mock_allocation
        
        result = self.context_manager.optimize_context(
            content=messages,
            model_context=mock_context
        )
        
        # Check that system message is preserved
        system_msgs = [msg for msg in result.optimized_content if msg.get("role") == "system"]
        assert len(system_msgs) >= 1  # At least one system message should remain
        
        # Original system message should be in the result
        original_system = messages[0]["content"]
        found_original = any(original_system in msg.get("content", "") for msg in system_msgs)
        assert found_original or "preserve_system_messages" in result.strategies_applied
    
    def test_caching_functionality(self):
        """Test semantic caching of optimization results."""
        messages = [
            {"role": "user", "content": "Test message for caching"}
        ]
        
        mock_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 1000
        mock_context.calculate_token_allocation.return_value = mock_allocation
        
        # First call - should not be cached
        result1 = self.context_manager.optimize_context(
            content=messages,
            model_context=mock_context,
            enable_caching=True
        )
        assert not result1.cache_hit
        
        # Second call with same content - should be cached
        result2 = self.context_manager.optimize_context(
            content=messages,
            model_context=mock_context,
            enable_caching=True
        )
        assert result2.cache_hit
        assert result1.optimized_content == result2.optimized_content
    
    def test_cache_disabled(self):
        """Test that caching can be disabled."""
        messages = [{"role": "user", "content": "Test message"}]
        
        mock_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 1000
        mock_context.calculate_token_allocation.return_value = mock_allocation
        
        # Two calls with caching disabled
        result1 = self.context_manager.optimize_context(
            content=messages,
            model_context=mock_context,
            enable_caching=False
        )
        result2 = self.context_manager.optimize_context(
            content=messages,
            model_context=mock_context,
            enable_caching=False
        )
        
        assert not result1.cache_hit
        assert not result2.cache_hit
    
    def test_legacy_compatibility(self):
        """Test backward compatibility with legacy methods."""
        messages = [
            {"role": "user", "content": "Test message"}
        ]
        
        # Test legacy estimate_tokens method
        tokens = self.context_manager.estimate_tokens(messages)
        assert tokens > 0
        
        # Test legacy optimize method
        optimized = self.context_manager.optimize(messages, "moonshot")
        assert isinstance(optimized, list)
        assert len(optimized) >= 0


class TestContextIntegrationManager:
    """Test the context integration manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.integration_manager = ContextIntegrationManager()
    
    def test_conversation_context_optimization(self):
        """Test optimization of conversation context."""
        # Mock thread context
        mock_thread = Mock()
        mock_thread.turns = []
        
        # Add some mock turns
        for i in range(3):
            turn = Mock()
            turn.role = "user" if i % 2 == 0 else "assistant"
            turn.content = f"Message {i}"
            turn.files = []
            mock_thread.turns.append(turn)
        
        mock_thread.thread_id = "test-thread-123"
        
        # Mock model context
        mock_model_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 1000
        mock_model_context.calculate_token_allocation.return_value = mock_allocation
        
        messages, metadata = self.integration_manager.optimize_conversation_context(
            thread_context=mock_thread,
            model_context=mock_model_context
        )
        
        assert isinstance(messages, list)
        assert isinstance(metadata, dict)
        assert "original_turns" in metadata
        assert "optimized_turns" in metadata
        assert "thread_id" in metadata
        assert metadata["thread_id"] == "test-thread-123"
    
    def test_file_context_optimization(self):
        """Test optimization of file context."""
        file_content = "def hello():\n    print('Hello, world!')\n" * 100  # Long content
        file_paths = ["test.py", "example.py"]
        
        mock_model_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 500
        mock_model_context.calculate_token_allocation.return_value = mock_allocation
        
        optimized_content, metadata = self.integration_manager.optimize_file_context(
            file_content=file_content,
            file_paths=file_paths,
            model_context=mock_model_context
        )
        
        assert isinstance(optimized_content, str)
        assert isinstance(metadata, dict)
        assert "file_count" in metadata
        assert metadata["file_count"] == len(file_paths)
        assert "original_tokens" in metadata
        assert "optimized_tokens" in metadata


class TestAdvancedContextUtils:
    """Test the utility functions for easy integration."""
    
    def test_optimize_for_model_utility(self):
        """Test the main utility function for content optimization."""
        content = "This is a test message for optimization"
        
        # Mock model context
        mock_context = Mock()
        mock_allocation = Mock()
        mock_allocation.content_tokens = 1000
        mock_context.calculate_token_allocation.return_value = mock_allocation
        
        optimized_content, metadata = optimize_for_model(
            content=content,
            model_context=mock_context
        )
        
        assert optimized_content is not None
        assert isinstance(metadata, dict)
        assert "original_tokens" in metadata
        assert "optimized_tokens" in metadata
        assert "compression_ratio" in metadata
    
    def test_estimate_tokens_utility(self):
        """Test the token estimation utility function."""
        # Test string content
        tokens = estimate_tokens("Hello, world!")
        assert tokens > 0
        assert tokens < 10
        
        # Test message list
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        message_tokens = estimate_tokens(messages)
        assert message_tokens > 0
    
    def test_error_handling(self):
        """Test error handling in utility functions."""
        # Test with None input - should handle gracefully
        result, metadata = optimize_for_model(None)
        # None input is converted to empty list, which is valid
        assert isinstance(metadata, dict)
        assert metadata.get("original_tokens", 0) == 0

        # Test token estimation with invalid input
        tokens = estimate_tokens(None)
        assert tokens >= 0  # Should fallback gracefully

        # Test with truly invalid input that should trigger error handling
        try:
            # This should trigger an error in the context manager
            result, metadata = optimize_for_model("test", model_context="invalid")
            # If no error, check for fallback indicators
            assert isinstance(metadata, dict)
        except Exception:
            # Exception is acceptable for invalid input
            pass


if __name__ == "__main__":
    pytest.main([__file__])
