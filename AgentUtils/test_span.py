import threading
import time

import pytest

from .span import Span


class TestSpan:

    def test_span_creation(self):
        """测试Span创建"""
        span = Span("Test content")

        assert span.content == "Test content"
        assert span.status == "open"
        assert span.parent is None
        assert span.children == []
        assert span.end_time is None
        assert isinstance(span.hash, int)
        assert isinstance(span.create_time, int)
        assert span.create_time > 0

    def test_span_with_parent(self):
        """测试带父Span的创建"""
        parent_span = Span("Parent content")
        child_span = Span("Child content", parent_span)

        assert child_span.parent == parent_span
        assert child_span in parent_span.children
        assert len(parent_span.children) == 1

    def test_span_content_conversion(self):
        """测试内容类型转换"""
        # 测试数字
        span1 = Span(123)
        assert span1.content == "123"

        # 测试字典
        span2 = Span({"key": "value"})
        assert span2.content == "{'key': 'value'}"

        # 测试列表
        span3 = Span([1, 2, 3])
        assert span3.content == "[1, 2, 3]"

        # 测试None
        span4 = Span(None)
        assert span4.content == "None"

    def test_span_end_success(self):
        """测试成功结束Span"""
        span = Span("Test content")
        assert span.end()

        assert span.status == "closed"
        assert span.end_time is not None
        assert span.end_time > span.create_time

    def test_span_end_failure_with_children(self):
        """测试有未结束子Span时结束失败"""
        parent_span = Span("Parent")
        child_span = Span("Child", parent_span)

        # 尝试结束父Span（应该失败）
        assert not parent_span.end()
        assert parent_span.status == "open"
        assert parent_span.end_time is None

        # 结束子Span后，父Span可以结束
        assert child_span.end()
        assert parent_span.end()

    def test_get_duration(self):
        """测试获取持续时间"""
        span = Span("Test content")

        # 未结束时应返回None
        assert span.get_duration() is None

        # 结束后应返回持续时间
        time.sleep(0.001)  # 短暂等待
        span.end()
        duration = span.get_duration()

        assert duration is not None
        assert duration > 0

    def test_display_method(self):
        """测试显示方法"""
        span = Span("Test content")
        display_output = span.display()

        assert "Span(hash=" in display_output
        assert "Content: Test content" in display_output
        assert "Status=open" in display_output

    def test_display_with_children(self):
        """测试带子Span的显示"""
        parent = Span("Parent")
        Span("Child", parent)

        display_output = parent.display()

        assert "Parent" in display_output
        assert "Child" in display_output
        assert "  " in display_output  # 检查缩进

    def test_to_dict(self):
        """测试转换为字典"""
        parent = Span("Parent")
        child = Span("Child", parent)
        child.end()

        parent_dict = parent.to_dict()
        child_dict = child.to_dict()

        assert parent_dict["hash"] == parent.hash
        assert parent_dict["content"] == "Parent"
        assert parent_dict["parent_hash"] is None
        assert len(parent_dict["children"]) == 1

        assert child_dict["hash"] == child.hash
        assert child_dict["content"] == "Child"
        assert child_dict["parent_hash"] == parent.hash
        assert child_dict["status"] == "closed"

    def test_from_dict(self, mock_storage):
        """测试从字典创建Span"""
        current_time = time.time_ns()
        span_data = {
            "hash": 123456,
            "create_time": current_time,
            "end_time": current_time + 1000000000,
            "children": [],
            "parent_hash": None,
            "status": "closed",
            "content": "Test span",
        }

        # 创建模拟的span_mgr
        class MockSpanManager:
            def get_span_by_hash(self, hash_val):
                return None

        span_mgr = MockSpanManager()
        span = Span.from_dict(span_data, span_mgr)

        assert span.hash == 123456
        assert span.content == "Test span"
        assert span.status == "closed"
        assert span.end_time == current_time + 1000000000

    def test_thread_safety(self):
        """测试线程安全"""
        span = Span("Test")
        results = []

        def add_child(thread_id):
            for i in range(100):
                child = Span(f"Child {thread_id}-{i}", span)
                results.append(child)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_child, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 检查所有子Span都被正确添加
        assert len(span.children) == 500
        assert len(results) == 500

    def test_str_method(self):
        """测试字符串表示"""
        span = Span("Test content")
        span_str = str(span)

        assert isinstance(span_str, str)
        assert "Span(hash=" in span_str
        assert "Content: Test content" in span_str

    def test_end_multiple_times(self):
        """测试多次调用end方法"""
        span = Span("Test")

        # 第一次结束应该成功
        assert span.end()
        original_end_time = span.end_time

        # 第二次结束应该返回False且不修改end_time
        assert not span.end()
        assert span.end_time == original_end_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
