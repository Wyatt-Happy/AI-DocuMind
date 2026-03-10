import re
from datetime import datetime

class RetrievalIntegration:
    def __init__(self, vector_store, knowledge_graph=None):
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
    
    def extract_time_from_text(self, text):
        """从文本中提取时间"""
        # 匹配年份格式：2020年、2020-01、2020/01等
        time_pattern = r'\d{4}(?:年|[-/]\d{1,2}(?:[-/]\d{1,2})?)'
        times = re.findall(time_pattern, text)
        return times[0] if times else ""
    
    def parse_time(self, time_str):
        """解析时间字符串为 datetime 对象"""
        try:
            # 尝试不同的时间格式
            if '年' in time_str:
                # 2020年格式
                return datetime.strptime(time_str, '%Y年')
            elif '-' in time_str:
                # 2020-01格式
                parts = time_str.split('-')
                if len(parts) == 2:
                    return datetime.strptime(time_str, '%Y-%m')
                elif len(parts) == 3:
                    return datetime.strptime(time_str, '%Y-%m-%d')
            elif '/' in time_str:
                # 2020/01格式
                parts = time_str.split('/')
                if len(parts) == 2:
                    return datetime.strptime(time_str, '%Y/%m')
                elif len(parts) == 3:
                    return datetime.strptime(time_str, '%Y/%m/%d')
        except:
            pass
        return None
    
    def search_by_person(self, person_id, query):
        """根据人员ID和查询内容搜索相关文本"""
        # 从知识图谱获取人员相关信息
        related_info = []
        if self.knowledge_graph:
            person_relations = self.knowledge_graph.get_entity_relations(person_id)
            for relation in person_relations:
                if relation['type'] == 'subject':
                    related_info.append(f"{relation['predicate']}: {relation['object']}")
                else:
                    related_info.append(f"{relation['subject']} {relation['predicate']}")
        
        # 构建混合查询
        combined_query = f"{person_id} {query} {' '.join(related_info)}"
        
        # 使用向量库搜索
        results = self.vector_store.search(combined_query, k=20)
        
        # 过滤和处理结果
        filtered_results = []
        for result in results:
            # 检查结果是否包含人员ID
            if person_id in result.page_content:
                # 提取时间
                time_str = self.extract_time_from_text(result.page_content)
                time_obj = self.parse_time(time_str)
                
                # 提取来源信息
                source = result.metadata.get('source', '未知')
                page = result.metadata.get('page', '未知')
                
                # 从知识图谱获取相关关系
                related_relations = []
                if self.knowledge_graph:
                    # 从结果内容中提取实体
                    import re
                    persons = re.findall(r'[\u4e00-\u9fa5]{2,4}(?:同志|先生|女士)?', result.page_content)
                    organizations = re.findall(r'(?:公司|企业|机构|部门|局|处|科|室|中心|协会|委员会)[\u4e00-\u9fa5]{2,10}', result.page_content)
                    
                    # 获取与这些实体相关的关系
                    for entity in persons + organizations:
                        entity_relations = self.knowledge_graph.get_entity_relations(entity)
                        for rel in entity_relations:
                            if person_id in [rel.get('subject', ''), rel.get('object', '')]:
                                related_relations.append(rel)
                
                filtered_results.append({
                    'content': result.page_content,
                    'time': time_str,
                    'time_obj': time_obj,
                    'source': source,
                    'page': page,
                    'relations': related_relations
                })
        
        # 按时间排序
        filtered_results.sort(key=lambda x: x['time_obj'] if x['time_obj'] else datetime.min)
        
        # 去重和合并重复信息
        unique_results = []
        seen_contents = set()
        
        for result in filtered_results:
            # 简单去重：基于内容的哈希
            content_hash = hash(result['content'])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def format_retrieval_results(self, results):
        """格式化检索结果"""
        formatted_results = []
        for result in results:
            formatted = f"{result['time']} - {result['content']}（{result['source']} - 页码 {result['page']}）"
            
            # 添加关系信息
            if 'relations' in result and result['relations']:
                relations_str = "\n相关关系："
                for relation in result['relations']:
                    if relation['type'] == 'subject':
                        relations_str += f"{relation['predicate']}: {relation['object']}; "
                    else:
                        relations_str += f"{relation['subject']} {relation['predicate']}; "
                formatted += relations_str.rstrip('; ')
            
            formatted_results.append(formatted)
        return formatted_results
