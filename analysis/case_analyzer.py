import os
import json
import re
from datetime import datetime
from collections import defaultdict, Counter

class CaseAnalyzer:
    def __init__(self, data_dir="data/case_analysis"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def extract_case_info(self, text):
        """从文本中提取案件信息"""
        # 提取案件类型
        case_types = []
        case_type_patterns = [
            r'(合同纠纷|侵权纠纷|劳动争议|婚姻家庭|刑事案件|行政案件|民事案件)',
            r'(纠纷|争议|案件|诉讼|仲裁)'
        ]
        
        for pattern in case_type_patterns:
            matches = re.findall(pattern, text)
            case_types.extend(matches)
        
        # 提取案件编号
        case_number = None
        case_number_pattern = r'案件编号[:：]?\s*([A-Za-z0-9-]+)'
        match = re.search(case_number_pattern, text)
        if match:
            case_number = match.group(1)
        
        # 提取日期
        dates = []
        date_pattern = r'\d{4}(?:年|[-/]\d{1,2}(?:[-/]\d{1,2})?)'
        matches = re.findall(date_pattern, text)
        dates.extend(matches)
        
        # 提取当事人
        parties = []
        party_pattern = r'(原告|被告|申请人|被申请人|上诉人|被上诉人)[:：]?\s*([\u4e00-\u9fa5]{2,10}(?:、[\u4e00-\u9fa5]{2,10})*)'
        matches = re.findall(party_pattern, text)
        for role, name in matches:
            parties.append({'role': role, 'name': name})
        
        return {
            'case_types': list(set(case_types)),
            'case_number': case_number,
            'dates': dates,
            'parties': parties
        }
    
    def analyze_cases(self, documents):
        """分析案件数据"""
        # 初始化统计数据
        stats = {
            'case_type_distribution': Counter(),
            'temporal_distribution': defaultdict(int),
            'party_count': Counter(),
            'total_cases': 0
        }
        
        # 分析每个文档
        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # 提取案件信息
            case_info = self.extract_case_info(content)
            
            # 更新统计数据
            if case_info['case_types']:
                stats['total_cases'] += 1
                
                # 案件类型分布
                for case_type in case_info['case_types']:
                    stats['case_type_distribution'][case_type] += 1
                
                # 时间分布
                if case_info['dates']:
                    # 尝试解析第一个日期
                    for date_str in case_info['dates']:
                        try:
                            if '年' in date_str:
                                date = datetime.strptime(date_str, '%Y年')
                            elif '-' in date_str:
                                parts = date_str.split('-')
                                if len(parts) == 2:
                                    date = datetime.strptime(date_str, '%Y-%m')
                                else:
                                    date = datetime.strptime(date_str, '%Y-%m-%d')
                            elif '/' in date_str:
                                parts = date_str.split('/')
                                if len(parts) == 2:
                                    date = datetime.strptime(date_str, '%Y/%m')
                                else:
                                    date = datetime.strptime(date_str, '%Y/%m/%d')
                            
                            # 按年统计
                            year_key = str(date.year)
                            stats['temporal_distribution'][year_key] += 1
                            break
                        except:
                            continue
                
                # 当事人统计
                for party in case_info['parties']:
                    stats['party_count'][party['name']] += 1
        
        return stats
    
    def generate_trend_analysis(self, stats):
        """生成趋势分析"""
        # 生成年度趋势
        yearly_trends = []
        years = sorted(stats['temporal_distribution'].keys())
        for year in years:
            yearly_trends.append({
                'year': year,
                'count': stats['temporal_distribution'][year]
            })
        
        # 生成案件类型分布
        case_type_trends = []
        for case_type, count in stats['case_type_distribution'].most_common(10):
            case_type_trends.append({
                'case_type': case_type,
                'count': count,
                'percentage': round(count / stats['total_cases'] * 100, 2) if stats['total_cases'] > 0 else 0
            })
        
        # 生成当事人活跃度
        party_activity = []
        for party, count in stats['party_count'].most_common(10):
            party_activity.append({
                'party': party,
                'count': count
            })
        
        return {
            'yearly_trends': yearly_trends,
            'case_type_trends': case_type_trends,
            'party_activity': party_activity,
            'total_cases': stats['total_cases']
        }
    
    def save_analysis(self, analysis, filename="case_analysis.json"):
        """保存分析结果"""
        analysis_path = os.path.join(self.data_dir, filename)
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        return analysis_path
    
    def load_analysis(self, filename="case_analysis.json"):
        """加载分析结果"""
        analysis_path = os.path.join(self.data_dir, filename)
        if os.path.exists(analysis_path):
            with open(analysis_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
