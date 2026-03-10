from collections import defaultdict
import json
import os

class KnowledgeGraph:
    def __init__(self, storage_path="data/knowledge_graph"):
        self.storage_path = storage_path
        self.graph = defaultdict(dict)  # 存储实体关系
        self.entities = defaultdict(set)  # 存储实体类型
        os.makedirs(storage_path, exist_ok=True)
        self.load_from_disk()
    
    def add_relation(self, subject, predicate, object_, metadata=None):
        """添加实体关系
        
        Args:
            subject: 主体实体
            predicate: 关系类型
            object_: 对象实体
            metadata: 关系元数据，如来源、时间等
        """
        if subject not in self.graph:
            self.graph[subject] = {}
        if predicate not in self.graph[subject]:
            self.graph[subject][predicate] = []
        
        relation = {
            'object': object_,
            'metadata': metadata or {}
        }
        
        # 避免重复关系
        if relation not in self.graph[subject][predicate]:
            self.graph[subject][predicate].append(relation)
        
        # 更新实体类型
        self.entities['subjects'].add(subject)
        self.entities['objects'].add(object_)
    
    def get_relations(self, subject=None, predicate=None, object_=None):
        """查询实体关系
        
        Args:
            subject: 主体实体（可选）
            predicate: 关系类型（可选）
            object_: 对象实体（可选）
            
        Returns:
            符合条件的关系列表
        """
        results = []
        
        if subject:
            # 查询特定主体的所有关系
            if subject in self.graph:
                if predicate:
                    # 查询特定主体和关系类型的所有对象
                    if predicate in self.graph[subject]:
                        for relation in self.graph[subject][predicate]:
                            if not object_ or relation['object'] == object_:
                                results.append({
                                    'subject': subject,
                                    'predicate': predicate,
                                    'object': relation['object'],
                                    'metadata': relation['metadata']
                                })
                else:
                    # 查询特定主体的所有关系
                    for pred, relations in self.graph[subject].items():
                        for relation in relations:
                            if not object_ or relation['object'] == object_:
                                results.append({
                                    'subject': subject,
                                    'predicate': pred,
                                    'object': relation['object'],
                                    'metadata': relation['metadata']
                                })
        else:
            # 查询所有关系
            for subj, predicates in self.graph.items():
                for pred, relations in predicates.items():
                    for relation in relations:
                        if (not predicate or pred == predicate) and (not object_ or relation['object'] == object_):
                            results.append({
                                'subject': subj,
                                'predicate': pred,
                                'object': relation['object'],
                                'metadata': relation['metadata']
                            })
        
        return results
    
    def get_entity_relations(self, entity):
        """获取实体的所有关系
        
        Args:
            entity: 实体名称
            
        Returns:
            实体作为主体和对象的所有关系
        """
        results = []
        
        # 作为主体的关系
        if entity in self.graph:
            for predicate, relations in self.graph[entity].items():
                for relation in relations:
                    results.append({
                        'type': 'subject',
                        'predicate': predicate,
                        'object': relation['object'],
                        'metadata': relation['metadata']
                    })
        
        # 作为对象的关系
        for subject, predicates in self.graph.items():
            for predicate, relations in predicates.items():
                for relation in relations:
                    if relation['object'] == entity:
                        results.append({
                            'type': 'object',
                            'subject': subject,
                            'predicate': predicate,
                            'metadata': relation['metadata']
                        })
        
        return results
    
    def build_from_entities(self, entities, metadata=None):
        """从实体列表构建知识图谱
        
        Args:
            entities: 实体字典，包含persons、organizations、positions等
            metadata: 元数据，如来源、时间等
        """
        # 构建人员-组织关系
        if 'persons' in entities and 'organizations' in entities:
            for person in entities['persons']:
                for org in entities['organizations']:
                    self.add_relation(person, '所属组织', org, metadata)
        
        # 构建人员-职位关系
        if 'persons' in entities and 'positions' in entities:
            for person in entities['persons']:
                for position in entities['positions']:
                    self.add_relation(person, '担任职位', position, metadata)
        
        # 构建职位-组织关系
        if 'positions' in entities and 'organizations' in entities:
            for position in entities['positions']:
                for org in entities['organizations']:
                    self.add_relation(position, '所属组织', org, metadata)
    
    def save_to_disk(self):
        """保存知识图谱到磁盘"""
        # 将set转换为list以便JSON序列化
        entities_dict = {k: list(v) for k, v in self.entities.items()}
        data = {
            'graph': dict(self.graph),
            'entities': entities_dict
        }
        
        with open(os.path.join(self.storage_path, 'knowledge_graph.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_disk(self):
        """从磁盘加载知识图谱"""
        graph_file = os.path.join(self.storage_path, 'knowledge_graph.json')
        if os.path.exists(graph_file):
            try:
                with open(graph_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.graph = defaultdict(dict, data.get('graph', {}))
                    self.entities = defaultdict(set, {k: set(v) for k, v in data.get('entities', {}).items()})
                print(f"成功加载知识图谱: {len(self.graph)} 个实体")
            except json.JSONDecodeError as e:
                print(f"知识图谱文件损坏，重新创建: {e}")
                # 重新初始化
                self.graph = defaultdict(dict)
                self.entities = defaultdict(set)
                # 备份损坏的文件
                import shutil
                import time
                backup_file = os.path.join(self.storage_path, f"knowledge_graph_backup_{int(time.time())}.json")
                shutil.copy2(graph_file, backup_file)
                print(f"已备份损坏的文件到: {backup_file}")
            except Exception as e:
                print(f"加载知识图谱失败: {e}")
                self.graph = defaultdict(dict)
                self.entities = defaultdict(set)
        else:
            print("知识图谱文件不存在，创建新的")
            self.graph = defaultdict(dict)
            self.entities = defaultdict(set)
    
    def clear(self):
        """清空知识图谱"""
        self.graph = defaultdict(dict)
        self.entities = defaultdict(set)
        self.save_to_disk()
    
    def get_statistics(self):
        """获取知识图谱统计信息"""
        num_entities = len(self.entities.get('subjects', set())) + len(self.entities.get('objects', set()))
        num_relations = 0
        for subject, predicates in self.graph.items():
            for predicate, relations in predicates.items():
                num_relations += len(relations)
        
        return {
            'entities': num_entities,
            'relations': num_relations,
            'subjects': len(self.entities.get('subjects', set())),
            'objects': len(self.entities.get('objects', set()))
        }
