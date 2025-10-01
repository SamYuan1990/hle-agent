import json
import os
import threading
import time

import pytest
from openai.types.chat import ChatCompletion

from .ExpiringDictStorage import ExpiringDictStorage


class TestExpiringDictStorage:

    def test_initialization_with_nonexistent_file(self, temp_file):
        """测试初始化时文件不存在的情况"""
        storage = ExpiringDictStorage(filename=temp_file)

        assert os.path.exists(temp_file)
        assert storage.data["_metadata"]["last_clean"] <= time.time()
        assert storage.data["data"] == {}

    def test_set_and_get_string_value(self, temp_file):
        """测试设置和获取字符串值"""
        storage = ExpiringDictStorage(filename=temp_file)

        # 测试设置和获取
        storage.set("test_key", "test_value")
        result = storage.get("test_key")

        assert result == "test_value"
        assert "test_key" in storage

    def test_set_and_get_chat_completion(self, temp_file, mock_chat_completion):
        """测试设置和获取ChatCompletion对象"""
        storage = ExpiringDictStorage(filename=temp_file)

        storage.set("chat_key", mock_chat_completion)
        result = storage.get("chat_key")

        assert isinstance(result, ChatCompletion)
        assert result.id == "chatcmpl-123"
        assert result.model == "gpt-3.5-turbo"

    def test_get_nonexistent_key(self, temp_file):
        """测试获取不存在的键"""
        storage = ExpiringDictStorage(filename=temp_file)

        result = storage.get("nonexistent_key")
        assert result is None

    def test_get_without_timestamp_update(self, temp_file):
        """测试获取值但不更新时间戳"""
        storage = ExpiringDictStorage(filename=temp_file)
        storage.set("test_key", "test_value")

        original_timestamp = storage.data["data"]["test_key"]["timestamp"]

        # 获取但不更新时间戳
        result = storage.get("test_key", update_timestamp=False)

        # 时间戳应该不变
        assert storage.data["data"]["test_key"]["timestamp"] == original_timestamp
        assert result == "test_value"

    def test_get_with_timestamp_update(self, temp_file):
        """测试获取值并更新时间戳"""
        storage = ExpiringDictStorage(filename=temp_file)
        original_time = time.time() - 100  # 100秒前
        storage.data["data"]["test_key"] = {
            "value": "test_value",
            "timestamp": original_time,
            "_type": "string",
        }

        # 获取并更新时间戳
        result = storage.get("test_key", update_timestamp=True)

        # 时间戳应该更新
        new_timestamp = storage.data["data"]["test_key"]["timestamp"]
        assert new_timestamp > original_time
        assert result == "test_value"

    def test_contains_operator(self, temp_file):
        """测试in操作符"""
        storage = ExpiringDictStorage(filename=temp_file)
        storage.set("existing_key", "value")

        assert "existing_key" in storage
        assert "nonexistent_key" not in storage

    def test_getitem_operator(self, temp_file):
        """测试[]操作符"""
        storage = ExpiringDictStorage(filename=temp_file)
        storage.set("test_key", "test_value")

        assert storage["test_key"] == "test_value"

    def test_setitem_operator(self, temp_file):
        """测试[]赋值操作符"""
        storage = ExpiringDictStorage(filename=temp_file)
        storage["test_key"] = "test_value"

        assert storage.get("test_key") == "test_value"

    def test_clean_expired_manual(self, temp_file):
        """测试手动清理过期数据"""
        storage = ExpiringDictStorage(filename=temp_file, expiry_days=1)

        # 添加过期数据（2天前）
        old_time = time.time() - 2 * 86400
        storage.data["data"]["expired_key"] = {
            "value": "expired_value",
            "timestamp": old_time,
            "_type": "string",
        }

        # 添加未过期数据
        storage.data["data"]["valid_key"] = {
            "value": "valid_value",
            "timestamp": time.time(),
            "_type": "string",
        }

        # 手动清理
        storage.clean_expired()

        # 检查结果
        assert "expired_key" not in storage.data["data"]
        assert "valid_key" in storage.data["data"]

    def test_corrupted_file_handling(self, temp_file):
        """测试处理损坏的JSON文件"""
        # 创建损坏的JSON文件
        with open(temp_file, "w") as f:
            f.write("invalid json content")

        # 应该能够正常初始化
        storage = ExpiringDictStorage(filename=temp_file)

        assert storage.data["_metadata"]["last_clean"] <= time.time()
        assert storage.data["data"] == {}

    def test_thread_safety(self, temp_file):
        """测试线程安全性"""
        storage = ExpiringDictStorage(filename=temp_file)

        results = []

        def worker(thread_id):
            for i in range(100):
                key = f"thread{thread_id}_key{i}"
                storage.set(key, f"value{i}")
                results.append(storage.get(key))

        # 创建多个线程同时操作
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 检查数据一致性
        assert len(results) == 500
        # 文件应该存在且可读
        assert os.path.exists(temp_file)

    def test_expiry_cleanup_on_load(self, temp_file):
        """测试加载时自动清理过期数据"""
        current_time = time.time()
        old_data = {
            "_metadata": {"last_clean": current_time - 10 * 86400},  # 10天前清理过
            "data": {
                "expired_key": {
                    "value": "expired_value",
                    "timestamp": current_time - 8 * 86400,  # 8天前
                    "_type": "string",
                },
                "valid_key": {
                    "value": "valid_value",
                    "timestamp": current_time - 3 * 86400,  # 3天前
                    "_type": "string",
                },
            },
        }

        # 写入测试数据
        with open(temp_file, "w") as f:
            json.dump(old_data, f)

        # 初始化存储（应该自动清理）
        storage = ExpiringDictStorage(filename=temp_file, expiry_days=7)

        # 检查结果
        assert "expired_key" not in storage.data["data"]
        assert "valid_key" in storage.data["data"]
        assert storage.data["_metadata"]["last_clean"] <= time.time()

    def test_different_expiry_periods(self, temp_file):
        """测试不同的过期时间设置"""
        # 测试1天过期
        storage_1day = ExpiringDictStorage(filename=temp_file + "_1day", expiry_days=1)
        storage_1day.set("test_key", "test_value")

        # 测试30天过期
        storage_30days = ExpiringDictStorage(
            filename=temp_file + "_30days", expiry_days=30
        )
        storage_30days.set("test_key", "test_value")

        assert storage_1day.expiry_days == 1
        assert storage_30days.expiry_days == 30

    def test_concurrent_access(self, temp_file):
        """测试并发访问"""
        storage = ExpiringDictStorage(filename=temp_file)

        def reader():
            for _ in range(100):
                storage.get("test_key")
                time.sleep(0.001)

        def writer():
            for i in range(100):
                storage.set(f"key{i}", f"value{i}")
                time.sleep(0.001)

        # 启动读写线程
        reader_thread = threading.Thread(target=reader)
        writer_thread = threading.Thread(target=writer)

        reader_thread.start()
        writer_thread.start()

        reader_thread.join()
        writer_thread.join()

        # 不应该出现数据损坏
        assert os.path.exists(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
