from defer.sugarfree import defer as d


class Agent:
    def __init__(self, LLM_Client, span_mgr):
        self.LLM_Client = LLM_Client
        self.span_mgr = span_mgr

    def talk_to_LLM(self, messages, root_span):
        my_span = self.span_mgr.create_span(messages, root_span.hash)
        d(self.span_mgr.end_span, my_span.hash)
        return self.LLM_Client.talk(messages, False)

    def talk_to_LLM_Json(self, messages, root_span):
        my_span = self.span_mgr.create_span(messages, root_span.hash)
        d(self.span_mgr.end_span, my_span.hash)
        return self.LLM_Client.talk(messages, True)

    def dryRun(self):
        """获取干跑模式状态"""
        return self.LLM_Client.get_dryRun()

    def get_legal_info(self):
        return self.LLM_Client.get_legal_info()
