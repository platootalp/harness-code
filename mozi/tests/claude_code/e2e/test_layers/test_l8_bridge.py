"""E2E 测试 - L8: Bridge 层

验证 IDE 协议通信。
直接测试 Bridge 协议组件。
"""

from __future__ import annotations

import pytest


class TestBridgeProtocol:
    """测试 Bridge 协议."""

    def test_bridge_protocol_import(self):
        """验证 Bridge 协议可以导入."""
        from claude_code.bridge.protocol import BridgeMessage, BridgeProtocol
        assert BridgeMessage is not None
        assert BridgeProtocol is not None

    def test_bridge_message_creation(self):
        """验证 BridgeMessage 创建."""
        from claude_code.bridge.protocol import BridgeMessage

        msg = BridgeMessage(
            type="user",
            payload={"message": {"content": "hello"}},
            id="test-123",
        )
        assert msg.type == "user"
        assert msg.id == "test-123"
        assert msg.payload["message"]["content"] == "hello"

    def test_bridge_protocol_serialization(self):
        """验证消息序列化."""
        from claude_code.bridge.protocol import BridgeMessage, BridgeProtocol

        protocol = BridgeProtocol()
        msg = BridgeMessage(
            type="user",
            payload={"message": {"content": "hello"}},
        )

        # 序列化
        encoded = protocol.serialize_message(msg)
        assert isinstance(encoded, bytes)
        assert b"user" in encoded

    def test_bridge_protocol_deserialization(self):
        """验证消息反序列化."""
        from claude_code.bridge.protocol import BridgeProtocol

        protocol = BridgeProtocol()
        data = b'{"type": "user", "payload": {"message": {"content": "hello"}}, "version": "1.0"}'

        # 反序列化
        msg = protocol.parse_message(data)
        assert msg is not None
        assert msg.type == "user"
        assert msg.payload["message"]["content"] == "hello"


class TestBridgeMessageTypes:
    """测试 Bridge 消息类型."""

    def test_user_message_type(self):
        """验证用户消息类型."""
        from claude_code.bridge.protocol import BridgeMessageType

        assert BridgeMessageType.USER.value == "user"

    def test_assistant_message_type(self):
        """验证助手消息类型."""
        from claude_code.bridge.protocol import BridgeMessageType

        assert BridgeMessageType.ASSISTANT.value == "assistant"

    def test_result_message_type(self):
        """验证结果消息类型."""
        from claude_code.bridge.protocol import BridgeMessageType

        assert BridgeMessageType.RESULT.value == "result"
