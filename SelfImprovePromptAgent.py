import json
import logging
from typing import Dict,List
from AgentUtils.Agent import Agent
from AgentUtils.PromptGen import PromptGen  # 导入PromptGen类

class SlefImproveAgent(Agent):
    def __init__(self, LLM_Client, span_mgr):
        super().__init__(LLM_Client, span_mgr)
        # 初始化PromptGen实例
        self.analysis_prompt_gen = self._init_analysis_prompt_gen()
        self.prompt_gen = self._init_prompt_gen()

    def _init_analysis_prompt_gen(self) -> PromptGen:
        """初始化第一轮分析的提示词生成器"""
        prompt_gen = PromptGen()
        
        # 设置基本属性
        prompt_gen.Role = "Information Analyst"
        prompt_gen.Situation = "analyzing bits and pieces of information to determine the best approach for answering a question"
        prompt_gen.Action = "extract key insights about who should answer, in what context, and what knowledge is required"

        # 设置任务步骤
        prompt_gen.Task_steps = [
            "Review the provided issue, answer, and cause",
            "Determine the best type of person/expert to answer this question",
            "Identify the scenarios where this question might be asked",
            "Analyze the thinking process behind the given answer",
            "Extract and summarize the key knowledge points from the thinking process"
        ]

        # 设置质量保证
        prompt_gen.Quality_assurance = [
            "Ensure the role identification is appropriate for the question type",
            "Verify the scenario context is realistic and relevant",
            "Check that all key knowledge points are extracted from the thinking process"
        ]

        # 设置输出结构
        prompt_gen.Output_structure = {
            "thinking_process": "str - the thinking process of the reason given by the person who answered this question",
            "role": "str - the best person to answer this question",
            "scene": "str - scenarios where this question might be asked",
            "knowledge": "list[str] - knowledge points that appear in the thinking process"
        }

        return prompt_gen

    def _init_prompt_gen(self) -> PromptGen:
        """初始化提示词生成器"""
        prompt_gen = PromptGen()
        
        # 设置基本属性
        prompt_gen.Role = "You are ${role}"
        prompt_gen.Situation = "You are in ${scene}"
        prompt_gen.Action = "You need to answer following question"

        # 设置任务步骤
        prompt_gen.Task_steps = [
            "Simply understand the difference between options",
            "Review relevant facts and knowledge, such as:\n${knowledge}",
            "Identify the points of study by connecting relevant facts and knowledge to the difference between options",
            "Please note that the descriptions in the question itself may contain mistakes or nits, so please answer based on the facts",
            "Analyze the ontology's points of investigation and assume an answer",
            "Compare and analyze the differences between the options based on the assumed options"
        ]

        # 设置质量保证
        prompt_gen.Quality_assurance = [
            "Ensure the answer is based on factual facts",
            "Verify that all steps have been logically followed",
            "Check that the output follows the specified JSON structure"
        ]

        # 设置输出结构
        prompt_gen.Output_structure = {
            "Thinking_process": "your thinking process, to show your followed steps to answer the question",
            "Explanation": "your reason",
            "Answer": "string, just from given options",
            "Confidence": "your confidence score between 0% and 100% for your answer"
        }

        return prompt_gen

    def _first_round_analysis(self, msg: str, answer: str, cause: str, span) -> dict:
        """第一轮分析：确定角色、场景和知识点"""
        # 更新分析阶段的变量
        self.analysis_prompt_gen.update_evaluate_vars({
            "issue": msg,
            "provided_answer": answer,
            "cause_explanation": cause
        })

        # 生成系统提示词
        system_prompt = self.analysis_prompt_gen.to_sys_prompt()
        
        # 生成任务提示词
        task_content = f"""issue\n{msg}

answer\n{answer}

cause\n{cause}

——————
The above is some bits and pieces of information"""
        
        task_prompt = self.analysis_prompt_gen.to_task_prompt(
            task_specific=task_content
        )

        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_prompt}
        ]

        response = self.talk_to_LLM_Json(messages, span)
        return json.loads(response.choices[0].message.content)

    def _format_knowledge(self, knowledge_list: List[str]) -> str:
        """格式化知识点列表"""
        return "\n".join([f"\t{item}" for item in knowledge_list])

    def _second_round_answer(self, msg: str, internal_data: dict, span) -> dict:
        """第二轮：基于分析结果回答问题"""
        # 更新评估变量
        self.prompt_gen.update_evaluate_vars({
            "role": internal_data["role"],
            "scene": internal_data["scene"],
            "knowledge": self._format_knowledge(internal_data["knowledge"])
        })

        # 生成系统提示词
        system_prompt = self.prompt_gen.to_sys_prompt()
        
        # 生成任务提示词
        task_prompt = self.prompt_gen.to_task_prompt(
            task_specific=f"Here is the question:\n{msg}"
        )

        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_prompt}
        ]

        response = self.talk_to_LLM_Json(messages, span)
        return json.loads(response.choices[0].message.content)

    def answer(self, msg: str, answer: str, cause: str, span) -> dict:
        """
        主回答方法
        
        参数:
            msg: 问题消息
            answer: 已有答案
            cause: 原因说明
            span: 跟踪span
            
        返回:
            dict: 包含思考过程、解释、答案和置信度的字典
        """
        try:
            # 第一轮：分析角色、场景和知识点
            logging.info("Starting first round analysis")
            internal_data = self._first_round_analysis(msg, answer, cause, span)
            
            # 第二轮：基于分析结果生成最终答案
            logging.info("Starting second round answer generation")
            final_answer = self._second_round_answer(msg, internal_data, span)
            
            return final_answer
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}")
            raise
        except Exception as e:
            logging.error(f"Error in answer generation: {e}")
            raise

    def get_current_prompt_vars(self) -> Dict[str, str]:
        """获取当前提示词变量（用于调试）"""
        return {
            "analysis_vars": self.analysis_prompt_gen.get_evaluate_vars(),
            "answer_vars": self.answer_prompt_gen.get_evaluate_vars()
        }