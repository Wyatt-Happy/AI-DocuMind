import re
import jieba
from collections import defaultdict

class NERProcessor:
    def __init__(self):
        # 人员实体模式
        self.person_pattern = r'[\u4e00-\u9fa5]{2,4}(?:同志|先生|女士|老师|局长|处长|科长|主任)?'
        # 时间实体模式
        self.time_pattern = r'\d{4}(?:年|[-/]\d{1,2}(?:[-/]\d{1,2})?)'
        # 组织实体模式
        self.org_pattern = r'(?:公司|企业|机构|部门|局|处|科|室|中心|协会|委员会)[\u4e00-\u9fa5]{2,10}'
        # 职位实体模式
        self.position_pattern = r'(?:局长|处长|科长|主任|经理|总监|部长|院长|校长)[\u4e00-\u9fa5]{0,4}'
        # 实体标准化映射
        self.entity_mappings = {
            'persons': {
                '张三': ['张三', '张三同志', '张三先生'],
                '李四': ['李四', '李四同志', '李四女士']
                # 可以根据实际情况添加更多映射
            }
        }
        # 实体缓存
        self.entity_cache = defaultdict(set)
    
    def extract_person_entities(self, text):
        """提取文本中的人员实体"""
        persons = re.findall(self.person_pattern, text)
        # 标准化处理
        normalized_persons = []
        for person in persons:
            # 移除称谓
            normalized = re.sub(r'(同志|先生|女士|老师|局长|处长|科长|主任)$', '', person)
            if normalized and len(normalized) >= 2:
                # 应用标准化映射
                normalized = self.normalize_entity('persons', normalized)
                normalized_persons.append(normalized)
        return list(set(normalized_persons))
    
    def extract_time_entities(self, text):
        """提取文本中的时间实体"""
        # 匹配年份格式：2020年、2020-01、2020/01等
        time_pattern = r'\d{4}(?:年|[-/]\d{1,2}(?:[-/]\d{1,2})?)'
        times = re.findall(time_pattern, text)
        return times
    
    def extract_org_entities(self, text):
        """提取文本中的组织实体"""
        orgs = re.findall(self.org_pattern, text)
        return list(set(orgs))
    
    def extract_position_entities(self, text):
        """提取文本中的职位实体"""
        positions = re.findall(self.position_pattern, text)
        return list(set(positions))
    
    def normalize_entity(self, entity_type, entity):
        """标准化实体"""
        if entity_type in self.entity_mappings:
            for standard_entity, variations in self.entity_mappings[entity_type].items():
                if entity in variations:
                    return standard_entity
        return entity
    
    def add_entity_mapping(self, entity_type, standard_entity, variations):
        """添加实体映射"""
        if entity_type not in self.entity_mappings:
            self.entity_mappings[entity_type] = {}
        self.entity_mappings[entity_type][standard_entity] = variations
    
    def process_text(self, text):
        """处理文本，提取实体"""
        persons = self.extract_person_entities(text)
        times = self.extract_time_entities(text)
        orgs = self.extract_org_entities(text)
        positions = self.extract_position_entities(text)
        
        # 缓存实体
        for person in persons:
            self.entity_cache['persons'].add(person)
        for org in orgs:
            self.entity_cache['organizations'].add(org)
        for position in positions:
            self.entity_cache['positions'].add(position)
        
        return {
            'persons': persons,
            'times': times,
            'organizations': orgs,
            'positions': positions
        }
    
    def get_entity_cache(self):
        """获取实体缓存"""
        return dict(self.entity_cache)
