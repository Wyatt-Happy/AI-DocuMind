import os
import json
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import requests

class SmartDocumentGenerator:
    """智能文书生成器
    
    遵循「模板结构化 → 信息精准抽取 → LLM 填充润色 → 可视化编辑溯源」的路线
    """
    
    def __init__(self, template_dir="data/smart_templates", ner_processor=None):
        self.template_dir = template_dir
        os.makedirs(template_dir, exist_ok=True)
        self.templates = self.load_templates()
        self.ner_processor = ner_processor
        
        # 千问百炼API配置
        self.qwen_api_key = os.environ.get("DASHSCOPE_API_KEY")
        self.qwen_api_endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    def load_templates(self) -> Dict:
        """加载所有智能文书模板"""
        templates = {}
        if not os.path.exists(self.template_dir):
            return templates
            
        for filename in os.listdir(self.template_dir):
            if filename.endswith('.json'):
                template_path = os.path.join(self.template_dir, filename)
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        templates[template_data['id']] = template_data
                except Exception as e:
                    print(f"加载模板失败 {filename}: {e}")
        return templates
    
    def analyze_document_structure(self, content: str) -> Dict:
        """分析文档结构，识别可复用和不可复用部分
        
        使用千问百炼API分析文档，识别：
        1. 可复用部分（模板化内容）
        2. 不可复用部分（需要人工填写的变量）
        
        Args:
            content: 文档内容
            
        Returns:
            文档结构分析结果，包含可复用和不可复用部分
        """
        # 使用千问百炼API分析文档
        try:
            analysis = self._analyze_with_llm(content)
            return analysis
        except Exception as e:
            print(f"LLM分析失败，使用规则分析: {e}")
            return self._analyze_with_rules(content)
    
    def _analyze_with_llm(self, content: str) -> Dict:
        """使用千问百炼API分析文档结构"""
        if not self.qwen_api_key:
            raise ValueError("未配置千问百炼API密钥")
        
        prompt = f"""请分析以下法律文书，识别可复用和不可复用部分。

文档内容：
{content[:3000]}  # 限制长度避免超出token限制

请按以下JSON格式返回分析结果：
{{
    "reusable_parts": [
        {{
            "id": "part_1",
            "content": "可复用的文本内容",
            "description": "这部分内容的说明"
        }}
    ],
    "variable_parts": [
        {{
            "id": "var_1",
            "name": "variable_name",
            "description": "变量描述（如：当事人姓名）",
            "example": "示例值",
            "position": "这部分在文档中的位置描述"
        }}
    ],
    "structure": [
        {{
            "type": "title|salutation|body|closing|signature",
            "content": "段落内容",
            "is_reusable": true/false,
            "variables": ["var_1", "var_2"]
        }}
    ]
}}

要求：
1. 可复用部分：文档中固定不变的内容，如格式、通用表述等
2. 不可复用部分：需要根据实际情况填写的信息，如人名、日期、案号、金额等
3. 为每个不可复用部分提供清晰的描述和示例
4. 保持文档的原始结构和顺序"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.qwen_api_key}"
        }
        
        payload = {
            "model": "qwen-plus",
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "temperature": 0.2,
                "max_tokens": 4000,
                "top_p": 0.9
            }
        }
        
        response = requests.post(self.qwen_api_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        llm_output = result["output"]["text"]
        
        # 解析JSON结果
        try:
            # 尝试从输出中提取JSON
            json_match = re.search(r'\{[\s\S]*\}', llm_output)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = json.loads(llm_output)
            
            # 添加元数据
            analysis['paragraph_count'] = len(analysis.get('structure', []))
            analysis['variable_count'] = len(analysis.get('variable_parts', []))
            analysis['reusable_count'] = len(analysis.get('reusable_parts', []))
            
            return analysis
        except json.JSONDecodeError as e:
            print(f"解析LLM输出失败: {e}")
            print(f"LLM输出: {llm_output[:500]}")
            raise
    
    def _analyze_with_rules(self, content: str) -> Dict:
        """使用规则分析文档结构（备用方案）"""
        # 使用NER提取实体
        entities = {}
        if self.ner_processor:
            entities = self.ner_processor.process_text(content)
        
        # 识别文档中的变量部分
        variable_patterns = {
            'person': r'[\u4e00-\u9fa5]{2,4}(?:同志|先生|女士|老师|局长|处长|科长|主任)?',
            'date': r'\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{2}-\d{2}',
            'case_number': r'案号[：:]\s*[^\n]+',
            'organization': r'(?:公司|企业|机构|部门|局|处|科|室|中心|协会|委员会)[\u4e00-\u9fa5]{2,10}'
        }
        
        variables = {}
        for var_type, pattern in variable_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                variables[var_type] = list(set(matches))
        
        # 构建可复用和不可复用部分
        reusable_parts = []
        variable_parts = []
        structure = []
        
        paragraphs = content.split('\n\n')
        
        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue
            
            para_type = self._classify_paragraph(para)
            has_variables = any(var in para for var_list in variables.values() for var in var_list)
            
            if has_variables:
                # 不可复用部分
                var_ids = []
                for var_type, var_list in variables.items():
                    for var in var_list:
                        if var in para:
                            var_id = f"{var_type}_{len(variable_parts)}"
                            variable_parts.append({
                                "id": var_id,
                                "name": var_id,
                                "description": f"{var_type}类型的变量",
                                "example": var,
                                "position": f"第{i+1}段"
                            })
                            var_ids.append(var_id)
                
                structure.append({
                    "type": para_type,
                    "content": para,
                    "is_reusable": False,
                    "variables": var_ids
                })
            else:
                # 可复用部分
                part_id = f"part_{len(reusable_parts)}"
                reusable_parts.append({
                    "id": part_id,
                    "content": para,
                    "description": f"第{i+1}段"
                })
                
                structure.append({
                    "type": para_type,
                    "content": para,
                    "is_reusable": True,
                    "variables": []
                })
        
        return {
            "reusable_parts": reusable_parts,
            "variable_parts": variable_parts,
            "structure": structure,
            "paragraph_count": len(structure),
            "variable_count": len(variable_parts),
            "reusable_count": len(reusable_parts),
            "entities": entities
        }
    
    def _classify_paragraph(self, text: str) -> str:
        """分类段落类型"""
        text = text.strip()
        
        # 标题
        if len(text) < 50 and ('通知' in text or '决定' in text or '报告' in text or '书' in text[-3:]):
            return 'title'
        
        # 称呼
        if text.startswith('尊敬的') or text.startswith('敬爱的') or '：' in text[:20]:
            return 'salutation'
        
        # 落款
        if any(keyword in text for keyword in ['特此通知', '此致', '敬礼']):
            return 'closing'
        
        # 签名
        if len(text) < 100 and any(keyword in text for keyword in ['年', '月', '日']) and len(re.findall(r'[\u4e00-\u9fa5]{2,10}', text)) <= 3:
            return 'signature'
        
        # 正文
        return 'body'
    
    def _extract_variables_from_text(self, text: str, variables: Dict) -> List[Dict]:
        """从文本中提取变量"""
        found_variables = []
        
        for var_type, var_list in variables.items():
            for var in var_list:
                if var in text:
                    found_variables.append({
                        'type': var_type,
                        'value': var,
                        'position': text.find(var)
                    })
        
        return found_variables
    
    def create_template_from_document(self, content: str, template_name: str, 
                                     business_type: str = "") -> Dict:
        """从文档创建智能模板
        
        Args:
            content: 文档内容
            template_name: 模板名称
            business_type: 业务类型
            
        Returns:
            创建的模板信息
        """
        # 分析文档结构
        analysis = self.analyze_document_structure(content)
        
        # 生成模板ID
        template_id = f"smart_template_{len(self.templates) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 构建模板结构
        template_structure = []
        template_variables = []
        
        for para in analysis['structure']:
            para_info = {
                'index': para['index'],
                'type': para['type'],
                'original_content': para['content'],
                'has_variables': para['has_variables']
            }
            
            if para['has_variables']:
                # 替换变量为占位符
                processed_content = para['content']
                for var in para['variables']:
                    var_type = var['type']
                    var_index = len(template_variables)
                    placeholder = "{{" + f"{var_type}_{var_index}" + "}}"
                    processed_content = processed_content.replace(var['value'], placeholder)
                    
                    template_variables.append({
                        'name': f"{var_type}_{var_index}",
                        'type': var_type,
                        'example': var['value'],
                        'description': f"{var_type}类型的变量",
                        'required': True,
                        'editable': True
                    })
                
                para_info['template_content'] = processed_content
            else:
                para_info['template_content'] = para['content']
                para_info['reusable'] = True
            
            template_structure.append(para_info)
        
        # 创建模板
        template = {
            'id': template_id,
            'name': template_name,
            'business_type': business_type,
            'created_at': datetime.now().isoformat(),
            'structure': template_structure,
            'variables': template_variables,
            'original_analysis': analysis,
            'usage_count': 0,
            'last_used': None
        }
        
        # 保存模板
        self._save_template(template)
        self.templates[template_id] = template
        
        return template
    
    def _save_template(self, template: Dict):
        """保存模板到文件"""
        template_path = os.path.join(self.template_dir, f"{template['id']}.json")
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """获取指定模板"""
        return self.templates.get(template_id)
    
    def list_templates(self, business_type: str = None) -> List[Dict]:
        """列出所有模板"""
        templates = list(self.templates.values())
        if business_type:
            templates = [t for t in templates if t.get('business_type') == business_type]
        return templates
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id in self.templates:
            template_path = os.path.join(self.template_dir, f"{template_id}.json")
            if os.path.exists(template_path):
                os.remove(template_path)
            del self.templates[template_id]
            return True
        return False
    
    def fill_template_with_llm(self, template_id: str, user_inputs: Dict, 
                               context: str = "") -> Dict:
        """使用LLM填充和润色模板
        
        Args:
            template_id: 模板ID
            user_inputs: 用户输入的变量值
            context: 上下文信息
            
        Returns:
            生成的文档和溯源信息
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        
        # 构建提示
        prompt = self._build_generation_prompt(template, user_inputs, context)
        
        # 调用LLM生成内容
        generated_content = self._call_llm(prompt)
        
        # 更新模板使用统计
        template['usage_count'] += 1
        template['last_used'] = datetime.now().isoformat()
        self._save_template(template)
        
        # 构建溯源信息
        traceability = {
            'template_id': template_id,
            'template_name': template['name'],
            'user_inputs': user_inputs,
            'generated_at': datetime.now().isoformat(),
            'llm_used': True,
            'original_structure': template['structure'],
            'filled_variables': list(user_inputs.keys())
        }
        
        return {
            'content': generated_content,
            'traceability': traceability,
            'template_info': {
                'id': template_id,
                'name': template['name'],
                'business_type': template.get('business_type', '')
            }
        }
    
    def _build_generation_prompt_from_analysis(self, analysis: Dict, user_inputs: Dict,
                                               context: str) -> str:
        """根据分析结果构建LLM生成提示"""
        reusable_parts = analysis.get('reusable_parts', [])
        variable_parts = analysis.get('variable_parts', [])
        structure = analysis.get('structure', [])

        prompt = """你是一个专业的法律文书生成助手。请根据以下文档结构和用户输入的信息，生成一份完整的法律文书。

## 可复用部分（模板固定内容）
"""
        for part in reusable_parts:
            prompt += f"\n[{part['id']}] {part['description']}\n{part['content']}\n"

        prompt += "\n## 需要填写的变量\n"
        for var in variable_parts:
            var_value = user_inputs.get(var['id'], '[未填写]')
            prompt += f"\n- {var['description']}: {var_value}"

        if context:
            prompt += f"\n\n## 上下文信息\n{context}"

        prompt += """

## 生成要求
1. 保持文档的整体结构和格式
2. 将用户输入的信息准确填入对应位置
3. 对内容进行适当的润色，使其更加专业和通顺
4. 确保法律术语的准确性和规范性
5. 生成的文档应该完整、连贯、符合法律文书的标准格式
6. 将可复用部分和填写的变量部分自然融合

请生成完整的法律文书内容："""

        return prompt

    def _build_generation_prompt(self, template: Dict, user_inputs: Dict,
                                context: str) -> str:
        """构建LLM生成提示"""
        # 构建模板结构描述
        structure_desc = []
        for para in template['structure']:
            if para['has_variables']:
                structure_desc.append(f"[{para['type']}] {para['template_content'][:100]}...")
            else:
                structure_desc.append(f"[{para['type']}] {para['template_content'][:100]}... (可复用)")
        
        prompt = f"""你是一个专业的法律文书生成助手。请根据以下模板结构和用户输入的信息，生成一份完整的法律文书。

## 模板信息
模板名称：{template['name']}
业务类型：{template.get('business_type', '通用')}

## 模板结构
"""
        for desc in structure_desc:
            prompt += f"- {desc}\n"
        
        prompt += f"""
## 用户输入的信息
"""
        for key, value in user_inputs.items():
            prompt += f"- {key}: {value}\n"
        
        if context:
            prompt += f"""
## 上下文信息
{context}
"""
        
        prompt += """
## 生成要求
1. 保持模板的整体结构和格式
2. 将用户输入的信息准确填入对应位置
3. 对内容进行适当的润色，使其更加专业和通顺
4. 确保法律术语的准确性和规范性
5. 生成的文档应该完整、连贯、符合法律文书的标准格式

请生成完整的法律文书内容："""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM生成内容"""
        if not self.qwen_api_key:
            # 如果没有API密钥，使用简单的模板填充
            return f"[LLM未配置]\n\n{prompt[:500]}..."
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.qwen_api_key}"
            }
            
            payload = {
                "model": "qwen-plus",
                "input": {
                    "prompt": prompt
                },
                "parameters": {
                    "temperature": 0.3,
                    "max_tokens": 3000,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(self.qwen_api_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["output"]["text"]
        except Exception as e:
            print(f"调用LLM失败: {e}")
            return f"[生成失败]\n\n{prompt[:500]}..."
    
    def edit_generated_document(self, generated_content: str, edits: List[Dict]) -> str:
        """编辑生成的文档
        
        Args:
            generated_content: 生成的文档内容
            edits: 编辑操作列表
            
        Returns:
            编辑后的文档内容
        """
        content = generated_content
        
        for edit in edits:
            edit_type = edit.get('type')
            if edit_type == 'replace':
                old_text = edit.get('old_text', '')
                new_text = edit.get('new_text', '')
                content = content.replace(old_text, new_text)
            elif edit_type == 'insert':
                position = edit.get('position', 0)
                text = edit.get('text', '')
                content = content[:position] + text + content[position:]
            elif edit_type == 'delete':
                start = edit.get('start', 0)
                end = edit.get('end', len(content))
                content = content[:start] + content[end:]
        
        return content
    
    def extract_fillable_fields(self, content: str) -> List[Dict]:
        """从文档内容中提取可填写字段
        
        Args:
            content: 文档内容
            
        Returns:
            可填写字段列表
        """
        fields = []
        
        # 使用NER提取实体作为可填写字段
        if self.ner_processor:
            entities = self.ner_processor.process_text(content)
            
            # 人员字段
            for person in entities.get('persons', []):
                fields.append({
                    'name': f'person_{len(fields)}',
                    'label': '人员',
                    'type': 'person',
                    'example': person,
                    'required': True
                })
            
            # 时间字段
            for time in entities.get('times', []):
                fields.append({
                    'name': f'time_{len(fields)}',
                    'label': '时间',
                    'type': 'date',
                    'example': time,
                    'required': True
                })
            
            # 组织字段
            for org in entities.get('organizations', []):
                fields.append({
                    'name': f'org_{len(fields)}',
                    'label': '组织',
                    'type': 'text',
                    'example': org,
                    'required': False
                })
        
        # 识别常见的法律文书字段
        common_fields = [
            (r'案号[：:]\s*([^\n]+)', 'case_number', '案号'),
            (r'当事人[：:]\s*([^\n]+)', 'party', '当事人'),
            (r'地址[：:]\s*([^\n]+)', 'address', '地址'),
            (r'联系电话[：:]\s*([^\n]+)', 'phone', '联系电话'),
        ]
        
        for pattern, field_name, field_label in common_fields:
            matches = re.findall(pattern, content)
            for match in matches:
                fields.append({
                    'name': field_name,
                    'label': field_label,
                    'type': 'text',
                    'example': match.strip(),
                    'required': True
                })
        
        # 去重
        seen = set()
        unique_fields = []
        for field in fields:
            key = (field['name'], field['example'])
            if key not in seen:
                seen.add(key)
                unique_fields.append(field)
        
        return unique_fields