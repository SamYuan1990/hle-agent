import logging
import threading
from typing import Dict, Tuple


class ThreadSafeCounter:
    """多线程安全的计数器"""

    def __init__(self, initial_value=0):
        self._value = initial_value
        self._lock = threading.Lock()

    def inc(self, amount=1):
        """增加计数器值"""
        with self._lock:
            self._value += amount

    def get_value(self):
        """获取当前计数器值"""
        with self._lock:
            return self._value


class ThreadSafeFloatCounter:
    """多线程安全的浮点计数器"""

    def __init__(self, initial_value=0.0):
        self._value = initial_value
        self._lock = threading.Lock()

    def inc(self, amount=1.0):
        """增加计数器值"""
        with self._lock:
            self._value += amount

    def get_value(self):
        """获取当前计数器值"""
        with self._lock:
            return self._value


class LabeledCounter:
    """带标签的计数器（模拟Prometheus的标签功能）"""

    def __init__(self):
        self._counters: Dict[Tuple[str, ...], ThreadSafeCounter] = {}
        self._lock = threading.Lock()

    def labels(self, **labels):
        """获取或创建具有特定标签的计数器"""
        # 将标签转换为可哈希的元组形式
        label_tuple = tuple(sorted(labels.items()))

        with self._lock:
            if label_tuple not in self._counters:
                self._counters[label_tuple] = ThreadSafeCounter()
            return self._counters[label_tuple]

    def get_all_values(self):
        """获取所有标签组合的计数器值"""
        with self._lock:
            return {
                labels: counter.get_value()
                for labels, counter in self._counters.items()
            }


# 全局计数器实例
LLM_RESPONSE_TIME = ThreadSafeFloatCounter()
LLM_TOKENS_USED = LabeledCounter()
Client_Cache = LabeledCounter()


def print_metrics():
    """打印当前指标"""
    try:
        logging.info("\n=== Current Metrics ===")
        logging.info(f"llm_response_time_seconds: {LLM_RESPONSE_TIME.get_value()}")

        # 打印带标签的token计数
        token_counts = LLM_TOKENS_USED.get_all_values()
        for labels, count in token_counts.items():
            label_str = ",".join([f'{k}="{v}"' for k, v in labels])
            logging.info(f"llm_tokens_used_total{{{label_str}}} {count}")

        logging.info("=================================\n")
    except Exception as e:
        logging.info(f"Error printing metrics: {str(e)}")
