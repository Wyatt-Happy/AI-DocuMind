import os
import json
from jinja2 import Template

class DocumentProcessor:
    def __init__(self, template_dir="data/templates"):
        self.template_dir = template_dir
        os.makedirs(template_dir, exist_ok=True)
        self.templates = self.load_templates()
    
    def load_templates(self):
        """加载所有文书模板"""
        templates = {}
        for filename in os.listdir(self.template_dir):
            if filename.endswith('.json'):
                template_path = os.path.join(self.template_dir, filename)
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    templates[template_data['id']] = template_data
        return templates
    
    def save_template(self, template_data):
        """保存文书模板"""
        # 生成模板ID
        if 'id' not in template_data:
            template_data['id'] = f"template_{len(self.templates) + 1}"
        
        # 保存模板文件
        template_path = os.path.join(self.template_dir, f"{template_data['id']}.json")
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)
        
        # 更新模板列表
        self.templates[template_data['id']] = template_data
        return template_data['id']
    
    def get_template(self, template_id):
        """获取指定模板"""
        return self.templates.get(template_id)
    
    def list_templates(self):
        """列出所有模板"""
        return list(self.templates.values())
    
    def delete_template(self, template_id):
        """删除模板"""
        if template_id in self.templates:
            template_path = os.path.join(self.template_dir, f"{template_id}.json")
            if os.path.exists(template_path):
                os.remove(template_path)
            del self.templates[template_id]
            return True
        return False
    
    def generate_document(self, template_id, data):
        """根据模板生成文书"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        
        # 使用Jinja2渲染模板
        jinja_template = Template(template['content'])
        rendered_content = jinja_template.render(**data)
        
        return {
            'template_id': template_id,
            'template_name': template['name'],
            'content': rendered_content,
            'data': data
        }
    
    def create_default_templates(self):
        """创建默认模板"""
        default_templates = [
            {
                'id': 'template_1',
                'name': '案件受理通知书',
                'description': '案件受理通知书模板',
                'content': '''{{ title }}

尊敬的{{ party_name }}：

您于{{ submit_date }}提交的关于{{ case_type }}的案件材料已收悉。经审查，符合受理条件，现决定予以受理。

案件编号：{{ case_number }}
受理日期：{{ accept_date }}
承办人：{{ handler_name }}
联系电话：{{ contact_phone }}

特此通知。

{{ organization }}
{{ date }}
''',
                'fields': [
                    {'name': 'title', 'label': '标题', 'type': 'text', 'default': '案件受理通知书'},
                    {'name': 'party_name', 'label': '当事人姓名', 'type': 'text'},
                    {'name': 'submit_date', 'label': '提交日期', 'type': 'date'},
                    {'name': 'case_type', 'label': '案件类型', 'type': 'text'},
                    {'name': 'case_number', 'label': '案件编号', 'type': 'text'},
                    {'name': 'accept_date', 'label': '受理日期', 'type': 'date'},
                    {'name': 'handler_name', 'label': '承办人', 'type': 'text'},
                    {'name': 'contact_phone', 'label': '联系电话', 'type': 'text'},
                    {'name': 'organization', 'label': '组织机构', 'type': 'text', 'default': '某某单位'},
                    {'name': 'date', 'label': '日期', 'type': 'date'}
                ]
            },
            {
                'id': 'template_2',
                'name': '调查笔录',
                'description': '调查笔录模板',
                'content': '''调查笔录

时间：{{ date }} {{ time }}
地点：{{ location }}
调查人：{{ investigators }}
记录人：{{ recorder }}
被调查人：{{ interviewee_name }}
性别：{{ interviewee_gender }}
年龄：{{ interviewee_age }}
职业：{{ interviewee_occupation }}
联系电话：{{ interviewee_phone }}

问：{{ question1 }}
答：{{ answer1 }}

问：{{ question2 }}
答：{{ answer2 }}

问：{{ question3 }}
答：{{ answer3 }}

以上记录经被调查人核对无误。

被调查人（签字）：{{ interviewee_signature }}
调查人（签字）：{{ investigators_signature }}
记录人（签字）：{{ recorder_signature }}
''',
                'fields': [
                    {'name': 'date', 'label': '日期', 'type': 'date'},
                    {'name': 'time', 'label': '时间', 'type': 'text'},
                    {'name': 'location', 'label': '地点', 'type': 'text'},
                    {'name': 'investigators', 'label': '调查人', 'type': 'text'},
                    {'name': 'recorder', 'label': '记录人', 'type': 'text'},
                    {'name': 'interviewee_name', 'label': '被调查人姓名', 'type': 'text'},
                    {'name': 'interviewee_gender', 'label': '性别', 'type': 'text'},
                    {'name': 'interviewee_age', 'label': '年龄', 'type': 'text'},
                    {'name': 'interviewee_occupation', 'label': '职业', 'type': 'text'},
                    {'name': 'interviewee_phone', 'label': '联系电话', 'type': 'text'},
                    {'name': 'question1', 'label': '问题1', 'type': 'text'},
                    {'name': 'answer1', 'label': '回答1', 'type': 'text'},
                    {'name': 'question2', 'label': '问题2', 'type': 'text'},
                    {'name': 'answer2', 'label': '回答2', 'type': 'text'},
                    {'name': 'question3', 'label': '问题3', 'type': 'text'},
                    {'name': 'answer3', 'label': '回答3', 'type': 'text'},
                    {'name': 'interviewee_signature', 'label': '被调查人签字', 'type': 'text'},
                    {'name': 'investigators_signature', 'label': '调查人签字', 'type': 'text'},
                    {'name': 'recorder_signature', 'label': '记录人签字', 'type': 'text'}
                ]
            }
        ]
        
        for template in default_templates:
            self.save_template(template)
