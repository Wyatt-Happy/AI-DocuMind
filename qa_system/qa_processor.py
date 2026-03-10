try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_community.chat_models import ChatOpenAI
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.retrievers import BaseRetriever
    from langchain_community.vectorstores import FAISS
    HAS_LANGCHAIN = True
except Exception as e:
    print(f"导入 LangChain 失败: {e}")
    HAS_LANGCHAIN = False

import requests
import json
import os
from core.ner_processor import NERProcessor
from core.knowledge_graph import KnowledgeGraph

class QAProcessor:
    def __init__(self, vector_store, knowledge_graph=None):
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.ner_processor = NERProcessor()
        
        # 千问百炼API配置
        self.qwen_api_key = os.environ.get("DASHSCOPE_API_KEY")  # 从环境变量中读取API密钥
        self.qwen_api_endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"  # 千问百炼API端点
        
        # 初始化提示模板（如果 LangChain 可用）
        if HAS_LANGCHAIN:
            self.prompt_template = ChatPromptTemplate.from_template("""
            你是一个智能档案系统的助手，负责回答用户关于档案内容的问题。
            
            以下是相关的档案信息：
            {context}
            
            请根据以上信息回答用户的问题：
            {question}
            
            回答要求：
            1. 基于提供的档案信息，不要编造内容
            2. 回答要准确、简洁、专业
            3. 如果信息不足，明确说明无法回答
            4. 提供信息来源（文件名和页码）
            """)
        else:
            self.prompt_template = None
    
    def analyze_question(self, question):
        """分析问题，提取实体和意图"""
        # 提取问题中的实体
        entities = self.ner_processor.process_text(question)
        
        # 简单的意图识别
        intent = "general"
        if any(keyword in question for keyword in ["履历", "经历", "工作", "职务"]):
            intent = "career"
        elif any(keyword in question for keyword in ["案件", "案例", "事件"]):
            intent = "case"
        elif any(keyword in question for keyword in ["会议", "记录", "纪要"]):
            intent = "meeting"
        elif any(keyword in question for keyword in ["统计", "分析", "趋势"]):
            intent = "statistics"
        
        return {
            'entities': entities,
            'intent': intent
        }
    
    def retrieve_relevant_info(self, question, entities, intent, k=5):
        """检索相关信息"""
        # 构建查询
        query = question
        
        # 添加实体到查询
        if entities.get('persons'):
            query += ' ' + ' '.join(entities['persons'])
        if entities.get('organizations'):
            query += ' ' + ' '.join(entities['organizations'])
        if entities.get('positions'):
            query += ' ' + ' '.join(entities['positions'])
        
        # 使用向量存储检索
        results = self.vector_store.search(query, k=k)
        
        # 从知识图谱获取相关信息
        kg_info = []
        if self.knowledge_graph:
            # 检查是否有人员实体
            if entities.get('persons'):
                for person in entities['persons']:
                    relations = self.knowledge_graph.get_entity_relations(person)
                    if relations:
                        kg_info.append(f"{person}的相关关系：")
                        for relation in relations:
                            if relation['type'] == 'subject':
                                kg_info.append(f"  - {relation['predicate']}: {relation['object']}")
                            else:
                                kg_info.append(f"  - {relation['subject']} {relation['predicate']}")
        
        # 格式化检索结果
        context = []
        for result in results:
            source = result.metadata.get('source', '未知')
            page = result.metadata.get('page', '未知')
            context.append(f"来源：{source}（页码：{page}）\n内容：{result.page_content}")
        
        # 添加知识图谱信息
        if kg_info:
            context.append("\n知识图谱信息：")
            context.extend(kg_info)
        
        return '\n\n'.join(context)
    
    def generate_answer(self, question, context):
        """生成回答"""
        # 简单的基于规则的回答生成
        # 在实际项目中，可以使用LLM生成更复杂的回答
        
        # 检查是否有足够的信息
        if not context or "来源：" not in context:
            return "抱歉，我无法回答这个问题，因为没有找到相关的档案信息。"
        
        # 构建回答
        answer = f"根据档案信息，我为您回答如下：\n\n"
        
        # 提取关键信息
        sources = []
        content_parts = []
        
        for part in context.split("\n\n"):
            if "来源：" in part:
                # 提取来源信息
                source_match = part.split("\n")[0]
                sources.append(source_match)
                
                # 提取内容
                content = '\n'.join(part.split("\n")[1:])
                if content and "内容：" in content:
                    content = content.replace("内容：", "")
                    content_parts.append(content)
            elif "知识图谱信息：" in part:
                # 添加知识图谱信息
                answer += "\n相关关系信息：\n"
                for line in part.split("\n")[1:]:
                    if line.strip():
                        answer += f"- {line.strip()}\n"
        
        # 添加内容摘要
        if content_parts:
            answer += "\n档案内容摘要：\n"
            for i, content in enumerate(content_parts):
                answer += f"{i+1}. {content}\n"
        
        # 添加信息来源
        if sources:
            answer += "\n信息来源：\n"
            for source in sources:
                answer += f"- {source}\n"
        
        return answer
    
    def generate_answer_with_qwen(self, question, context):
        """使用千问百炼API生成更优质的回答"""
        # 检查API密钥是否配置
        if not self.qwen_api_key or self.qwen_api_key == "your_api_key":
            # 如果API密钥未配置，使用默认的回答生成
            return self.generate_answer(question, context)
        
        # 检查是否有足够的信息
        if not context or "来源：" not in context:
            return "抱歉，我无法回答这个问题，因为没有找到相关的档案信息。"
        
        try:
            # 构建千问百炼API请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.qwen_api_key}"
            }
            
            # 构建提示
            prompt = f"你是一个智能档案系统的助手，负责回答用户关于档案内容的问题。请基于提供的档案信息回答问题，不要编造内容，回答要准确、简洁、专业，如果信息不足，明确说明无法回答，并提供信息来源（文件名和页码）。\n\n以下是相关的档案信息：\n{context}\n\n请根据以上信息回答用户的问题：{question}"
            
            # 构建请求体（千问百炼API格式）
            payload = {
                "model": "qwen-plus",  # 千问模型
                "input": {
                    "prompt": prompt
                },
                "parameters": {
                    "temperature": 0.3,  # 较低的温度值，保证回答的准确性
                    "max_tokens": 2000,  # 足够的最大令牌数
                    "top_p": 0.9
                }
            }
            
            # 发送请求
            response = requests.post(self.qwen_api_endpoint, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # 检查响应状态
            
            # 解析响应
            result = response.json()
            answer = result["output"]["text"]
            
            return answer
        except Exception as e:
            print(f"调用千问百炼API时出错: {e}")
            # 如果API调用失败，使用默认的回答生成
            return self.generate_answer(question, context)
    
    def process_question(self, question):
        """处理用户问题"""
        # 检查问题是否为空
        if not question or not question.strip():
            return {
                'question': question,
                'analysis': {'entities': {}, 'intent': 'general'},
                'context': '',
                'answer': '请输入有效的问题'
            }
        
        try:
            # 分析问题
            analysis = self.analyze_question(question)
            
            # 检索相关信息
            context = self.retrieve_relevant_info(question, analysis['entities'], analysis['intent'])
            
            # 生成回答（使用千问百炼API）
            answer = self.generate_answer_with_qwen(question, context)
            
            return {
                'question': question,
                'analysis': analysis,
                'context': context,
                'answer': answer
            }
        except Exception as e:
            print(f"处理问题时出错: {e}")
            import traceback
            traceback.print_exc()
            return {
                'question': question,
                'analysis': {'entities': {}, 'intent': 'general'},
                'context': '',
                'answer': f'处理问题时出错: {str(e)}'
            }
