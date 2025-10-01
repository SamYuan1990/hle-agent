import threading
import time

import pytest

from .span import Span_Mgr


class TestSpanManager:

    def test_manager_initialization(self, mock_storage):
        """测试管理器初始化"""
        manager = Span_Mgr(mock_storage)

        assert manager.root_spans == []
        assert manager.all_spans == {}
        assert mock_storage.get_calls[0] == ("span_data", False)

    def test_create_root_span(self, mock_storage):
        """测试创建根Span"""
        manager = Span_Mgr(mock_storage)
        span = manager.create_span("Root span")

        assert span in manager.root_spans
        assert span.hash in manager.all_spans
        assert span.parent is None
        assert len(mock_storage.set_calls) == 1

    def test_create_child_span(self, mock_storage):
        """测试创建子Span"""
        manager = Span_Mgr(mock_storage)
        parent = manager.create_span("Parent")
        child = manager.create_span("Child", parent.hash)

        assert child in manager.all_spans.values()
        assert child.parent == parent
        assert child in parent.children
        assert len(mock_storage.set_calls) == 2

    def test_get_span_by_hash(self, mock_storage):
        """测试通过hash获取Span"""
        manager = Span_Mgr(mock_storage)
        span = manager.create_span("Test span")

        found_span = manager.get_span_by_hash(span.hash)
        assert found_span == span

        # 测试不存在的hash
        assert manager.get_span_by_hash(999999) is None

    def test_end_span_success(self, mock_storage):
        """测试成功结束Span"""
        manager = Span_Mgr(mock_storage)
        span = manager.create_span("Test span")

        assert manager.end_span(span.hash)
        assert span.status == "closed"
        assert len(mock_storage.set_calls) == 2  # 创建 + 结束

    def test_end_span_failure(self, mock_storage):
        """测试结束Span失败"""
        manager = Span_Mgr(mock_storage)
        parent = manager.create_span("Parent")
        child = manager.create_span("Child", parent.hash)

        # 尝试结束父Span（应该失败，因为子Span未结束）
        assert not manager.end_span(parent.hash)
        assert parent.status == "open"

        # 结束子Span后，父Span可以结束
        assert manager.end_span(child.hash)
        assert manager.end_span(parent.hash)

    def test_get_recent_parent_spans(self, mock_storage):
        """测试获取最近的父Span"""
        manager = Span_Mgr(mock_storage)

        # 创建多个根Span
        span1 = manager.create_span("First")
        time.sleep(0.001)
        span2 = manager.create_span("Second")
        time.sleep(0.001)
        span3 = manager.create_span("Third")

        recent_spans = manager.get_recent_parent_spans()

        # 应该按创建时间倒序排列
        assert recent_spans[0] == span3
        assert recent_spans[1] == span2
        assert recent_spans[2] == span1

    def test_display_all_spans(self, mock_storage):
        """测试显示所有Span"""
        manager = Span_Mgr(mock_storage)
        parent = manager.create_span("Parent")
        manager.create_span("Child", parent.hash)

        display_output = manager.display_all_spans()

        assert "Parent" in display_output
        assert "Child" in display_output
        assert isinstance(display_output, str)

    # def test_load_from_storage(self, mock_storage, sample_span_data):
    #    """测试从存储加载数据"""
    #    mock_storage.data["span_data"] = sample_span_data
    #    manager = Span_Mgr(mock_storage)

    #    assert len(manager.all_spans) == 2
    #    assert len(manager.root_spans) == 1

    #    root_span = manager.root_spans[0]
    #    assert root_span.content == "Root span"
    #    assert len(root_span.children) == 1

    #    child_span = root_span.children[0]
    #    assert child_span.content == "Child span"

    def test_load_corrupted_data(self, mock_storage):
        """测试加载损坏的数据"""
        mock_storage.data["span_data"] = "invalid data"
        manager = Span_Mgr(mock_storage)

        # 应该优雅地处理损坏数据
        assert manager.root_spans == []
        assert manager.all_spans == {}

    def test_load_empty_data(self, mock_storage):
        """测试加载空数据"""
        mock_storage.data["span_data"] = None
        manager = Span_Mgr(mock_storage)

        assert manager.root_spans == []
        assert manager.all_spans == {}

    def test_concurrent_span_creation(self, mock_storage):
        """测试并发创建Span"""
        manager = Span_Mgr(mock_storage)
        spans = []

        def create_spans(thread_id):
            for i in range(50):
                span = manager.create_span(f"Span {thread_id}-{i}")
                spans.append(span)

        threads = []
        for i in range(4):
            thread = threading.Thread(target=create_spans, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 检查所有Span都被正确创建和管理
        assert len(manager.all_spans) == 200
        assert len(manager.root_spans) == 200

    # def test_span_relationships_after_load(self, mock_storage, sample_span_data):
    #    """测试加载后Span关系正确性"""
    #    mock_storage.data["span_data"] = sample_span_data
    #    manager = Span_Mgr(mock_storage)

    # 检查父子关系
    #    root_span = manager.root_spans[0]
    #    child_span = root_span.children[0]

    #    assert child_span.parent == root_span
    #    assert child_span in root_span.children

    def test_save_to_storage_format(self, mock_storage):
        """测试保存到存储的数据格式"""
        manager = Span_Mgr(mock_storage)
        parent = manager.create_span("Parent")
        child = manager.create_span("Child", parent.hash)

        # 检查保存的数据格式
        saved_data = mock_storage.set_calls[-1][1]
        assert "spans" in saved_data

        spans_data = saved_data["spans"]
        assert str(parent.hash) in spans_data
        assert str(child.hash) in spans_data

        parent_data = spans_data[str(parent.hash)]
        assert parent_data["content"] == "Parent"
        assert parent_data["parent_hash"] is None
        assert child.hash in parent_data["children_hashes"]

        child_data = spans_data[str(child.hash)]
        assert child_data["content"] == "Child"
        assert child_data["parent_hash"] == parent.hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
