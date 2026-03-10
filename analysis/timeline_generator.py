import os
import json
import re
from datetime import datetime
from collections import defaultdict

class TimelineGenerator:
    def __init__(self, data_dir="data/timelines"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def extract_events(self, text, person_id):
        """从文本中提取与指定人员相关的事件"""
        events = []
        
        # 分割文本为句子
        sentences = re.split(r'[。！？；;]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 检查句子是否包含人员ID
            if person_id in sentence:
                # 提取时间
                time_str = self.extract_time(sentence)
                
                # 提取事件类型
                event_type = self.extract_event_type(sentence)
                
                # 提取相关实体
                related_entities = self.extract_related_entities(sentence)
                
                events.append({
                    'content': sentence,
                    'time': time_str,
                    'event_type': event_type,
                    'related_entities': related_entities
                })
        
        return events
    
    def extract_time(self, text):
        """从文本中提取时间"""
        # 匹配年份格式：2020年、2020-01、2020/01等
        time_pattern = r'\d{4}(?:年|[-/]\d{1,2}(?:[-/]\d{1,2})?)'
        times = re.findall(time_pattern, text)
        return times[0] if times else ""
    
    def extract_event_type(self, text):
        """从文本中提取事件类型"""
        event_types = {
            'appointment': ['任命', '委任', '任职', '担任', '晋升', '提拔'],
            'resignation': ['辞职', '离职', '卸任', '退休'],
            'transfer': ['调动', '调任', '转任'],
            'reward': ['奖励', '表彰', '表扬', '嘉奖'],
            'punishment': ['处罚', '处分', '批评'],
            'meeting': ['会议', '参会', '出席', '主持'],
            'project': ['项目', '工程', '任务', '工作'],
            'other': []
        }
        
        for event_type, keywords in event_types.items():
            for keyword in keywords:
                if keyword in text:
                    return event_type
        
        return 'other'
    
    def extract_related_entities(self, text):
        """从文本中提取相关实体"""
        # 提取组织
        organizations = []
        org_pattern = r'(?:公司|企业|机构|部门|局|处|科|室|中心|协会|委员会)[\u4e00-\u9fa5]{2,10}'
        org_matches = re.findall(org_pattern, text)
        organizations.extend(org_matches)
        
        # 提取职位
        positions = []
        position_pattern = r'(?:局长|处长|科长|主任|经理|总监|部长|院长|校长)[\u4e00-\u9fa5]{0,4}'
        position_matches = re.findall(position_pattern, text)
        positions.extend(position_matches)
        
        return {
            'organizations': list(set(organizations)),
            'positions': list(set(positions))
        }
    
    def generate_timeline(self, person_id, documents):
        """为指定人员生成时间轴"""
        # 提取事件
        all_events = []
        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # 提取与人员相关的事件
            events = self.extract_events(content, person_id)
            
            # 添加来源信息
            for event in events:
                event['source'] = metadata.get('source', '未知')
                event['page'] = metadata.get('page', '未知')
                all_events.append(event)
        
        # 按时间排序
        sorted_events = sorted(all_events, key=lambda x: self.parse_time(x['time']))
        
        # 组织时间轴
        timeline = []
        for event in sorted_events:
            timeline.append({
                'time': event['time'],
                'event_type': event['event_type'],
                'content': event['content'],
                'source': event['source'],
                'page': event['page'],
                'related_entities': event['related_entities']
            })
        
        return timeline
    
    def parse_time(self, time_str):
        """解析时间字符串为 datetime 对象"""
        try:
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
        return datetime.min
    
    def save_timeline(self, person_id, timeline):
        """保存时间轴"""
        timeline_path = os.path.join(self.data_dir, f"{person_id}_timeline.json")
        with open(timeline_path, 'w', encoding='utf-8') as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)
        return timeline_path
    
    def load_timeline(self, person_id):
        """加载时间轴"""
        timeline_path = os.path.join(self.data_dir, f"{person_id}_timeline.json")
        if os.path.exists(timeline_path):
            with open(timeline_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
