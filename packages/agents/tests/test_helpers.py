"""Tests for helper functions"""

from agent_framework import ChatMessage, Role

from dakora_agents.maf import to_message


class TestToMessageHelper:
    """Test suite for to_message() helper function"""
    
    def test_to_message_basic(self, sample_render_result):
        """Test basic conversion from RenderResult to ChatMessage"""
        message = to_message(sample_render_result)
        
        assert isinstance(message, ChatMessage)
        assert message.text == "Rendered template text"
        assert message.role == Role.USER  # Default role
    
    def test_to_message_with_custom_role(self, sample_render_result):
        """Test to_message with custom role"""
        message = to_message(sample_render_result, role=Role.SYSTEM)
        
        assert message.role == Role.SYSTEM
        assert message.text == "Rendered template text"
    
    def test_to_message_preserves_metadata(self, sample_render_result):
        """Test that Dakora context is attached to message"""
        message = to_message(sample_render_result)
        
        # Check that _dakora_context is attached
        assert hasattr(message, "_dakora_context")
        assert message._dakora_context["prompt_id"] == "test-prompt"
        assert message._dakora_context["version"] == "1.0"
        assert message._dakora_context["inputs"] == {"user": "Alice"}
        assert message._dakora_context["metadata"] == {"category": "greeting"}
    
    def test_to_message_with_assistant_role(self, sample_render_result):
        """Test conversion with assistant role"""
        message = to_message(sample_render_result, role=Role.ASSISTANT)
        
        assert message.role == Role.ASSISTANT
        assert hasattr(message, "_dakora_context")
    
    def test_to_message_handles_empty_metadata(self):
        """Test to_message when render result has no metadata"""
        from unittest.mock import MagicMock
        
        result = MagicMock()
        result.text = "Test text"
        result.prompt_id = "test-prompt"
        result.version = "1.0"
        result.inputs = {}
        result.metadata = {}
        
        message = to_message(result)
        
        assert message._dakora_context["metadata"] == {}
        assert message._dakora_context["inputs"] == {}
