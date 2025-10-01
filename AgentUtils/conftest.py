import os
import tempfile
import time

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage


@pytest.fixture
def temp_file():
    """创建临时文件用于测试"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        yield f.name
    # 清理临时文件
    if os.path.exists(f.name):
        os.unlink(f.name)
    if os.path.exists(f.name + ".lock"):
        os.unlink(f.name + ".lock")


@pytest.fixture
def mock_chat_completion():
    """创建模拟的ChatCompletion对象"""
    message = ChatCompletionMessage(
        role="assistant", content="Hello, how can I help you?", name=None
    )
    return ChatCompletion(
        id="chatcmpl-123",
        object="chat.completion",
        created=int(time.time()),
        model="gpt-3.5-turbo",
        choices=[{"index": 0, "message": message, "finish_reason": "stop"}],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )


@pytest.fixture
def sample_data():
    """创建样本数据"""
    current_time = time.time()
    return {
        "_metadata": {"last_clean": current_time - 86400},  # 1天前清理过
        "data": {
            "key1": {
                "value": "value1",
                "timestamp": current_time - 86400,
                "_type": "string",
            },
            "key2": {
                "value": "value2",
                "timestamp": current_time - 43200,
                "_type": "string",
            },  # 半天前
            "expired_key": {
                "value": "expired_value",
                "timestamp": current_time - 8 * 86400,
                "_type": "string",
            },  # 8天前
        },
    }


@pytest.fixture
def sample_span_data():
    """创建样本Span数据"""
    current_time = time.time_ns()
    return {
        "spans": {
            "123456": {
                "create_time": current_time - 1000000000,  # 1秒前
                "end_time": current_time - 500000000,  # 0.5秒前
                "parent_hash": None,
                "children_hashes": [789012],
                "status": "closed",
                "content": "Root span",
            },
            "789012": {
                "create_time": current_time - 800000000,  # 0.8秒前
                "end_time": current_time - 300000000,  # 0.3秒前
                "parent_hash": 123456,
                "children_hashes": [],
                "status": "closed",
                "content": "Child span",
            },
        }
    }


# 模拟存储类
class MockStorage:
    def __init__(self):
        self.data = {}
        self.get_calls = []
        self.set_calls = []

    def get(self, key, update_timestamp=True):
        self.get_calls.append((key, update_timestamp))
        return self.data.get(key)

    def set(self, key, value):
        self.set_calls.append((key, value))
        self.data[key] = value

    def clear(self):
        self.data = {}
        self.get_calls = []
        self.set_calls = []


@pytest.fixture
def mock_storage():
    """创建模拟存储"""
    return MockStorage()
