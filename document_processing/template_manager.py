"""
模板管理模块
支持手动管理文书模板，包括扫描、解析、缓存功能
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from document_processing.file_parser import parse_file
from document_processing.smart_document_generator import SmartDocumentGenerator

logger = logging.getLogger(__name__)

# 模板文件夹路径
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "documents")
ANALYSIS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "analysis")

# 确保目录存在
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)


class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        self.smart_generator = SmartDocumentGenerator()
    
    def scan_templates(self) -> List[Dict]:
        """扫描模板文件夹中的所有模板文件
        
        Returns:
            模板列表，包含文件名、路径、是否已分析等信息
        """
        templates = []
        
        if not os.path.exists(TEMPLATES_DIR):
            logger.warning(f"模板目录不存在: {TEMPLATES_DIR}")
            return templates
        
        for filename in os.listdir(TEMPLATES_DIR):
            # 只处理支持的文件类型
            if filename.lower().endswith(('.pdf', '.docx', '.doc')):
                file_path = os.path.join(TEMPLATES_DIR, filename)
                template_name = os.path.splitext(filename)[0]
                
                # 检查是否已分析
                analysis_file = os.path.join(ANALYSIS_DIR, f"{template_name}_analysis.json")
                is_analyzed = os.path.exists(analysis_file)
                
                # 获取文件信息
                stat = os.stat(file_path)
                
                templates.append({
                    "id": template_name,
                    "name": template_name,
                    "filename": filename,
                    "file_path": file_path,
                    "is_analyzed": is_analyzed,
                    "file_size": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # 按名称排序
        templates.sort(key=lambda x: x["name"])
        
        logger.info(f"扫描到 {len(templates)} 个模板文件")
        return templates
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """获取指定模板的详细信息
        
        Args:
            template_name: 模板名称（不含扩展名）
            
        Returns:
            模板信息，如果不存在返回None
        """
        templates = self.scan_templates()
        for template in templates:
            if template["id"] == template_name:
                return template
        return None
    
    def analyze_template(self, template_name: str, force_reanalyze: bool = False) -> Dict:
        """分析模板文档结构
        
        Args:
            template_name: 模板名称
            force_reanalyze: 是否强制重新分析
            
        Returns:
            分析结果
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")
        
        analysis_file = os.path.join(ANALYSIS_DIR, f"{template_name}_analysis.json")
        
        # 如果已分析且不需要强制重新分析，直接返回缓存结果
        if template["is_analyzed"] and not force_reanalyze:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 解析文件
        logger.info(f"开始分析模板: {template_name}")
        parse_result = parse_file(template["file_path"])
        content = parse_result.get('full_content', '')
        
        if not content:
            raise ValueError(f"无法提取文件内容: {template_name}")
        
        # 使用AI分析文档结构
        try:
            analysis = self.smart_generator.analyze_document_structure(content)
            
            # 保存分析结果
            analysis_result = {
                "template_name": template_name,
                "filename": template["filename"],
                "analysis": analysis,
                "content": content[:5000],  # 保存前5000字符作为参考
                "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reusable_parts": analysis.get("reusable_parts", []),
                "variable_parts": analysis.get("variable_parts", []),
                "structure": analysis.get("structure", [])
            }
            
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模板分析完成: {template_name}, 变量数: {len(analysis.get('variable_parts', []))}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"模板分析失败: {template_name}, 错误: {str(e)}")
            raise
    
    def get_analysis(self, template_name: str) -> Optional[Dict]:
        """获取模板的分析结果
        
        Args:
            template_name: 模板名称
            
        Returns:
            分析结果，如果不存在返回None
        """
        analysis_file = os.path.join(ANALYSIS_DIR, f"{template_name}_analysis.json")
        
        if not os.path.exists(analysis_file):
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取分析结果失败: {template_name}, 错误: {str(e)}")
            return None
    
    def generate_document(self, template_name: str, variables: Dict[str, str]) -> str:
        """根据模板和变量生成文书
        
        Args:
            template_name: 模板名称
            variables: 变量值字典
            
        Returns:
            生成的文书内容
        """
        # 获取分析结果
        analysis_result = self.get_analysis(template_name)
        if not analysis_result:
            raise ValueError(f"模板未分析，请先分析模板: {template_name}")
        
        analysis = analysis_result.get("analysis", {})
        
        # 生成文书
        try:
            document = self.smart_generator.generate_document(analysis, variables)
            logger.info(f"文书生成完成: {template_name}")
            return document
        except Exception as e:
            logger.error(f"文书生成失败: {template_name}, 错误: {str(e)}")
            raise
    
    def delete_template(self, template_name: str) -> bool:
        """删除模板及其分析结果
        
        Args:
            template_name: 模板名称
            
        Returns:
            是否删除成功
        """
        template = self.get_template(template_name)
        if not template:
            return False
        
        try:
            # 删除模板文件
            if os.path.exists(template["file_path"]):
                os.remove(template["file_path"])
            
            # 删除分析结果
            analysis_file = os.path.join(ANALYSIS_DIR, f"{template_name}_analysis.json")
            if os.path.exists(analysis_file):
                os.remove(analysis_file)
            
            logger.info(f"模板已删除: {template_name}")
            return True
        except Exception as e:
            logger.error(f"删除模板失败: {template_name}, 错误: {str(e)}")
            return False
    
    def get_template_statistics(self) -> Dict:
        """获取模板统计信息
        
        Returns:
            统计信息
        """
        templates = self.scan_templates()
        analyzed_count = sum(1 for t in templates if t["is_analyzed"])
        
        return {
            "total_templates": len(templates),
            "analyzed_templates": analyzed_count,
            "unanalyzed_templates": len(templates) - analyzed_count,
            "templates": templates
        }


# 全局模板管理器实例
template_manager = TemplateManager()
