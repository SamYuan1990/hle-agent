import json
import time

import pytest
from openai.types.chat import ChatCompletion

from .ExpiringDictStorage import ExpiringDictStorage


class TestIntegration:

    def test_complete_workflow(self, temp_file):
        """测试完整的工作流程"""
        # 初始化存储
        storage = ExpiringDictStorage(filename=temp_file, expiry_days=7)

        # 添加各种类型的数据
        storage.set("string_key", "string_value")
        storage.set("dict_key", {"name": "test", "value": 123})
        storage.set("list_key", [1, 2, 3, 4, 5])

        # 验证数据存在
        assert "string_key" in storage
        assert "dict_key" in storage
        assert "list_key" in storage

        # 验证数据正确性
        assert storage.get("string_key") == "string_value"
        assert storage.get("dict_key") == {"name": "test", "value": 123}
        assert storage.get("list_key") == [1, 2, 3, 4, 5]

        # 测试操作符
        assert storage["string_key"] == "string_value"
        storage["new_key"] = "new_value"
        assert storage["new_key"] == "new_value"

        # 手动清理（不应该清理任何数据）
        storage.clean_expired()
        assert "string_key" in storage

        # 重新加载存储
        storage2 = ExpiringDictStorage(filename=temp_file, expiry_days=7)

        # 验证数据持久化
        assert storage2.get("string_key") == "string_value"
        assert storage2.get("new_key") == "new_value"

    def test_expiry_workflow(self, temp_file):
        """测试过期数据清理流程"""
        # 创建包含过期数据的文件
        current_time = time.time()
        test_data = {
            "_metadata": {"last_clean": current_time - 10 * 86400},
            "data": {
                "expired_1": {
                    "value": "expired_1",
                    "timestamp": current_time - 8 * 86400,
                    "_type": "string",
                },
                "expired_2": {
                    "value": "expired_2",
                    "timestamp": current_time - 9 * 86400,
                    "_type": "string",
                },
                "valid_1": {
                    "value": "valid_1",
                    "timestamp": current_time - 3 * 86400,
                    "_type": "string",
                },
            },
        }

        with open(temp_file, "w") as f:
            json.dump(test_data, f)

        # 初始化存储（应该自动清理过期数据）
        storage = ExpiringDictStorage(filename=temp_file, expiry_days=7)

        # 验证清理结果
        assert "expired_1" not in storage
        assert "expired_2" not in storage
        assert "valid_1" in storage
        assert storage.get("valid_1") == "valid_1"

    def test_chat_completion_integration(self, temp_file, mock_chat_completion):
        """测试ChatCompletion对象的完整集成"""
        storage = ExpiringDictStorage(filename=temp_file)

        # 存储ChatCompletion对象
        storage.set("chat_response", mock_chat_completion)

        # 检索并验证
        retrieved = storage.get("chat_response")

        assert isinstance(retrieved, ChatCompletion)
        assert retrieved.id == "chatcmpl-123"
        assert retrieved.model == "gpt-3.5-turbo"
        assert len(retrieved.choices) == 1
        assert retrieved.choices[0].message.content == "Hello, how can I help you?"

        # 重新加载验证持久化
        storage2 = ExpiringDictStorage(filename=temp_file)
        retrieved2 = storage2.get("chat_response")

        assert retrieved2.id == retrieved.id
        assert retrieved2.model == retrieved.model

    def test_mixed_data_types(self, temp_file, mock_chat_completion):
        """测试混合数据类型存储"""
        storage = ExpiringDictStorage(filename=temp_file)

        # 存储多种类型数据
        test_data = [
            "string_value",
            123,
            45.67,
            True,
            None,
            {"key": "value", "number": 42},
            [1, 2, 3, "four", True],
            mock_chat_completion,
        ]

        for i, data in enumerate(test_data):
            storage.set(f"key_{i}", data)

        # 验证所有数据都能正确检索
        for i, expected_data in enumerate(test_data):
            retrieved = storage.get(f"key_{i}")

            if isinstance(expected_data, ChatCompletion):
                assert isinstance(retrieved, ChatCompletion)
                assert retrieved.id == expected_data.id
            else:
                assert retrieved == expected_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
