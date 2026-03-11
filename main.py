import os
import logging
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict

class QuestionRequest(BaseModel):
    question: str
import uuid
import re
from datetime import datetime
from document_processing.file_parser import parse_file
from core.ner_processor import NERProcessor
from core.vector_store import VectorStore
from qa_system.retrieval_integration import RetrievalIntegration
from core.knowledge_graph import KnowledgeGraph
from qa_system.qa_processor import QAProcessor
from document_processing.document_processor import DocumentProcessor
from document_processing.smart_document_generator import SmartDocumentGenerator
from document_processing.template_manager import template_manager
from analysis.case_analyzer import CaseAnalyzer
from analysis.timeline_generator import TimelineGenerator
from multimodal.multimodal_processor import MultimodalProcessor

# 初始化应用
app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境中应该设置为具体的域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)

# 挂载静态文件服务
app.mount("/ui", StaticFiles(directory="static", html=True), name="static")

# 初始化组件
print("Initializing components...")
print("Creating NER processor...")
ner_processor = NERProcessor()
print("Creating vector store...")
try:
    vector_store = VectorStore()
except Exception as e:
    print(f"创建向量存储时出错: {e}")
    # 创建一个空的向量存储，即使模型加载失败也能启动服务器
    from core.vector_store import VectorStore
    vector_store = VectorStore()
    vector_store.embedding_model = None
print("Creating knowledge graph...")
knowledge_graph = KnowledgeGraph()
print("Creating retrieval integration...")
retrieval_integration = RetrievalIntegration(vector_store, knowledge_graph)
print("Creating QA processor...")
qa_processor = QAProcessor(vector_store, knowledge_graph)
print("Creating document processor...")
document_processor = DocumentProcessor()
document_processor.create_default_templates()
print("Creating smart document generator...")
smart_document_generator = SmartDocumentGenerator(ner_processor=ner_processor)
print("Creating case analyzer...")
case_analyzer = CaseAnalyzer()
print("Creating timeline generator...")
timeline_generator = TimelineGenerator()
print("Creating multimodal processor...")
multimodal_processor = MultimodalProcessor()
print("Components initialized successfully.")

# 检查向量存储是否初始化成功
if vector_store.embedding_model is None:
    print("提示：使用TF-IDF + FAISS向量存储，功能完整，检索效率高")

# 确保上传目录存在
UPLOAD_DIR = "data/uploads"
VECTOR_STORE_PATH = "data/vector_store"
BUSINESS_TYPES_FILE = "data/business_types.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
os.makedirs("data", exist_ok=True)

# 业务类型管理
def load_business_types():
    """加载业务类型"""
    if os.path.exists(BUSINESS_TYPES_FILE):
        with open(BUSINESS_TYPES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_business_types(business_types):
    """保存业务类型"""
    with open(BUSINESS_TYPES_FILE, 'w', encoding='utf-8') as f:
        json.dump(business_types, f, ensure_ascii=False, indent=2)

# 文件业务类型映射
FILE_BUSINESS_TYPES_FILE = "data/file_business_types.json"

def load_file_business_types():
    """加载文件业务类型映射"""
    if os.path.exists(FILE_BUSINESS_TYPES_FILE):
        with open(FILE_BUSINESS_TYPES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_file_business_types(file_business_types):
    """保存文件业务类型映射"""
    with open(FILE_BUSINESS_TYPES_FILE, 'w', encoding='utf-8') as f:
        json.dump(file_business_types, f, ensure_ascii=False, indent=2)

# 尝试加载已有的向量库
vector_store.load(VECTOR_STORE_PATH)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件并处理"""
    try:
        # 保存上传的文件
        file_extension = os.path.splitext(file.filename)[1]
        if file_extension not in [".docx", ".pdf"]:
            raise HTTPException(status_code=400, detail="只支持 .docx 和 .pdf 文件")
        
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{file_extension}")
        print(f"保存文件到: {file_path}")
        
        with open(file_path, "wb") as f:
            content = await file.read()
            print(f"文件大小: {len(content)} 字节")
            f.write(content)
        
        # 解析文件
        print(f"开始解析文件: {file_path}")
        parse_result = parse_file(file_path)
        print(f"解析结果: {parse_result}")
        
        content = parse_result['full_content']
        
        if not content:
            print("文件解析失败：内容为空")
            raise HTTPException(status_code=500, detail="文件解析失败")
        
        # 提取实体
        print("开始提取实体")
        entities = ner_processor.process_text(content)
        print(f"提取的实体: {entities}")
        
        # 使用知识图谱构建实体关系
        if knowledge_graph:
            metadata = {
                "source": file.filename,
                "timestamp": str(datetime.now())
            }
            knowledge_graph.build_from_entities(entities, metadata)
            knowledge_graph.save_to_disk()
        
        # 分割文本为片段并准备元数据
        chunks = []
        metadatas = []
        
        # 根据文件类型处理片段
        if parse_result['file_type'] == 'pdf':
            # 使用PDF文件的页面信息
            print("使用PDF处理方式")
            pages = parse_result.get('pages', [])
            
            for i, page in enumerate(pages):
                text = page['text']
                if text.strip():
                    # 提取当前片段的实体
                    chunk_entities = ner_processor.process_text(text)
                    
                    # 生成元数据
                    metadata = {
                        'source': file.filename,
                        'page': page['page_num'],
                        'file_type': 'pdf',
                        'persons': chunk_entities["persons"],
                        'times': chunk_entities["times"],
                        'organizations': chunk_entities.get("organizations", []),
                        'positions': chunk_entities.get("positions", [])
                    }
                    
                    # 添加到列表
                    chunks.append(text)
                    metadatas.append(metadata)
                    
                    # 为每个片段构建知识图谱关系
                    if knowledge_graph:
                        chunk_metadata = {
                            'source': file.filename,
                            'page': f"页码 {page['page_num']}",
                            'timestamp': str(datetime.now())
                        }
                        knowledge_graph.build_from_entities(chunk_entities, chunk_metadata)
        elif parse_result['file_type'] == 'docx':
            # Word文件按段落分割
            print(f"Word文件有 {len(parse_result.get('paragraphs', []))} 个段落")
            for paragraph in parse_result.get('paragraphs', []):
                text = paragraph['text']
                paragraph_num = paragraph['paragraph_num']
                
                # 提取当前片段的实体
                chunk_entities = ner_processor.process_text(text)
                
                # 生成元数据
                metadata = {
                    'source': file.filename,
                    'page': f"段落 {paragraph_num}",
                    'paragraph_num': paragraph_num,
                    'persons': chunk_entities["persons"],
                    'times': chunk_entities["times"],
                    'organizations': chunk_entities.get("organizations", []),
                    'positions': chunk_entities.get("positions", []),
                    'file_type': 'docx'
                }
                
                # 添加到列表
                chunks.append(text)
                metadatas.append(metadata)
                
                # 为每个片段构建知识图谱关系
                if knowledge_graph:
                    chunk_metadata = {
                        'source': file.filename,
                        'page': f"段落 {paragraph_num}",
                        'timestamp': str(datetime.now())
                    }
                    knowledge_graph.build_from_entities(chunk_entities, chunk_metadata)
        else:
            # 其他文件类型按行分割
            segments = content.split('\n')
            print(f"其他文件类型有 {len(segments)} 行")
            for i, segment in enumerate(segments):
                segment = segment.strip()
                if segment:
                    # 提取当前片段的实体
                    chunk_entities = ner_processor.process_text(segment)
                    
                    # 生成元数据
                    metadata = {
                        'source': file.filename,
                        'page': f"行 {i+1}",
                        'persons': chunk_entities["persons"],
                        'times': chunk_entities["times"],
                        'organizations': chunk_entities.get("organizations", []),
                        'positions': chunk_entities.get("positions", []),
                        'file_type': 'other'
                    }
                    
                    # 添加到列表
                    chunks.append(segment)
                    metadatas.append(metadata)
                    
                    # 为每个片段构建知识图谱关系
                    if knowledge_graph:
                        chunk_metadata = {
                            'source': file.filename,
                            'page': f"行 {i+1}",
                            'timestamp': str(datetime.now())
                        }
                        knowledge_graph.build_from_entities(chunk_entities, chunk_metadata)
        
        # 添加到向量库
        print(f"添加 {len(chunks)} 个片段到向量库")
        vector_store.add_texts(chunks, metadatas)
        vector_store.save(VECTOR_STORE_PATH)
        
        # 处理多模态内容
        print("处理多模态内容")
        multimodal_result = multimodal_processor.process_document(file_path)
        
        # 获取实际保存的文件名（UUID格式）
        saved_filename = os.path.basename(file_path)
        
        return {
            "filename": file.filename,
            "saved_filename": saved_filename,
            "file_path": file_path,
            "status": "success",
            "entities": entities,
            "chunks_count": len(chunks),
            "multimodal": {
                "images_count": len(multimodal_result['images']),
                "tables_count": len(multimodal_result['tables']),
                "images": multimodal_result['images'],
                "tables": multimodal_result['tables']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")

@app.get("/query")
async def query(person_id: str, query: str):
    """查询人员履历"""
    try:
        # 搜索相关信息
        results = retrieval_integration.search_by_person(person_id, query)
        
        # 格式化结果
        formatted_results = retrieval_integration.format_retrieval_results(results)
        
        return {
            "person_id": person_id,
            "query": query,
            "results": formatted_results
        }
    except Exception as e:
        logger.error(f"查询时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询时出错: {str(e)}")

@app.get("/status")
async def get_status():
    """获取系统状态"""
    return {
        "status": "running",
        "vector_store_path": VECTOR_STORE_PATH,
        "upload_dir": UPLOAD_DIR
    }

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """智能问答接口"""
    try:
        # 处理用户问题
        result = qa_processor.process_question(request.question)
        
        return {
            "question": request.question,
            "answer": result["answer"],
            "analysis": result["analysis"]
        }
    except Exception as e:
        logger.error(f"处理问题时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理问题时出错: {str(e)}")

@app.get("/templates")
async def list_templates():
    """列出所有文书模板"""
    try:
        templates = document_processor.list_templates()
        return {"templates": templates}
    except Exception as e:
        logger.error(f"获取模板列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板列表时出错: {str(e)}")

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """获取指定文书模板"""
    try:
        template = document_processor.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板时出错: {str(e)}")

@app.post("/templates")
async def create_template(template: dict):
    """创建新文书模板"""
    try:
        template_id = document_processor.save_template(template)
        return {"template_id": template_id, "status": "success"}
    except Exception as e:
        logger.error(f"创建模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建模板时出错: {str(e)}")

@app.put("/templates/{template_id}")
async def update_template(template_id: str, template: dict):
    """更新文书模板"""
    try:
        # 确保模板ID一致
        template['id'] = template_id
        template_id = document_processor.save_template(template)
        return {"template_id": template_id, "status": "success"}
    except Exception as e:
        logger.error(f"更新模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新模板时出错: {str(e)}")

@app.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """删除文书模板"""
    try:
        success = document_processor.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除模板时出错: {str(e)}")

@app.post("/generate-document")
async def generate_document(template_id: str, data: dict):
    """根据模板生成文书"""
    try:
        document = document_processor.generate_document(template_id, data)
        return document
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"生成文书时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成文书时出错: {str(e)}")

@app.get("/case-analysis")
async def get_case_analysis():
    """获取案件统计分析结果"""
    try:
        # 从向量存储中获取所有文档
        documents = vector_store.get_all_documents()
        
        # 分析案件数据
        stats = case_analyzer.analyze_cases(documents)
        
        # 生成趋势分析
        analysis = case_analyzer.generate_trend_analysis(stats)
        
        # 保存分析结果
        case_analyzer.save_analysis(analysis)
        
        return analysis
    except Exception as e:
        logger.error(f"获取案件分析时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取案件分析时出错: {str(e)}")

@app.get("/templates-manual")
async def list_manual_templates():
    """获取手动模板列表"""
    try:
        import os
        template_dir = "templates/documents"
        if not os.path.exists(template_dir):
            return {"templates": []}
        
        # 获取文件夹中的所有文件
        files = [f for f in os.listdir(template_dir) if os.path.isfile(os.path.join(template_dir, f))]
        return {"templates": files}
    except Exception as e:
        logger.error(f"获取模板列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板列表时出错: {str(e)}")

@app.post("/templates-manual/{template_name}/analyze")
async def analyze_manual_template(template_name: str):
    """分析手动模板文件"""
    try:
        import os
        from document_processing.smart_document_generator import SmartDocumentGenerator
        from document_processing.file_parser import parse_file
        
        template_dir = "templates/documents"
        template_path = os.path.join(template_dir, template_name)
        
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail=f"模板文件不存在: {template_name}")
        
        # 使用file_parser解析文件内容（支持PDF、Word、TXT等多种格式）
        try:
            parse_result = parse_file(template_path)
            content = parse_result.get('full_content', '')
            if not content:
                raise HTTPException(status_code=400, detail="无法从文件中提取文本内容")
        except Exception as parse_error:
            logger.error(f"解析文件失败: {str(parse_error)}")
            raise HTTPException(status_code=400, detail=f"解析文件失败: {str(parse_error)}")
        
        # 分析文档结构
        generator = SmartDocumentGenerator()
        analysis = generator.analyze_document_structure(content)
        
        # 保存分析结果
        analysis_dir = "templates/analysis"
        os.makedirs(analysis_dir, exist_ok=True)
        
        analysis_path = os.path.join(analysis_dir, f"{os.path.splitext(template_name)[0]}_analysis.json")
        import json
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        return {
            "template_name": template_name,
            "analysis": analysis,
            "variable_count": len(analysis.get("variable_parts", [])),
            "reusable_count": len(analysis.get("reusable_parts", []))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析模板时出错: {str(e)}")

class GenerateManualDocumentRequest(BaseModel):
    template_name: str
    variables: Dict[str, str]

@app.post("/templates-manual/generate")
async def generate_manual_document(request: GenerateManualDocumentRequest):
    """根据模板和用户输入生成文书"""
    try:
        import os
        import json
        from document_processing.smart_document_generator import SmartDocumentGenerator
        from document_processing.file_parser import parse_file
        
        template_name = request.template_name
        variables = request.variables
        
        # 读取分析结果
        analysis_dir = "templates/analysis"
        analysis_path = os.path.join(analysis_dir, f"{os.path.splitext(template_name)[0]}_analysis.json")
        
        if not os.path.exists(analysis_path):
            raise HTTPException(status_code=404, detail=f"模板分析结果不存在，请先分析模板")
        
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        # 读取模板文件（使用file_parser解析PDF、Word等多种格式）
        template_dir = "templates/documents"
        template_path = os.path.join(template_dir, template_name)
        
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail=f"模板文件不存在: {template_name}")
        
        try:
            parse_result = parse_file(template_path)
            content = parse_result.get('full_content', '')
            if not content:
                raise HTTPException(status_code=400, detail="无法从文件中提取文本内容")
        except Exception as parse_error:
            logger.error(f"解析文件失败: {str(parse_error)}")
            raise HTTPException(status_code=400, detail=f"解析文件失败: {str(parse_error)}")
        
        # 替换变量
        for var_name, var_value in variables.items():
            content = content.replace(f"{{{{ {var_name} }}}}", var_value)
            content = content.replace(f"{{{{{var_name}}}}}", var_value)
        
        # 生成文书
        generator = SmartDocumentGenerator()
        generated_content = content
        
        return {
            "content": generated_content,
            "template_name": template_name,
            "generated_at": datetime.now().isoformat(),
            "variables_used": list(variables.keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成文书时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成文书时出错: {str(e)}")

@app.get("/timeline/{person_id}")
async def get_person_timeline(person_id: str):
    """获取人员事件时间轴"""
    try:
        # 从向量存储中获取所有文档
        documents = vector_store.get_all_documents()
        
        # 生成时间轴
        timeline = timeline_generator.generate_timeline(person_id, documents)
        
        # 保存时间轴
        timeline_generator.save_timeline(person_id, timeline)
        
        return {
            'person_id': person_id,
            'timeline': timeline
        }
    except Exception as e:
        logger.error(f"获取时间轴时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取时间轴时出错: {str(e)}")

# 业务类型管理API
@app.get("/business-types")
async def get_business_types():
    """获取所有业务类型"""
    try:
        business_types = load_business_types()
        return {"business_types": business_types}
    except Exception as e:
        logger.error(f"获取业务类型时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取业务类型时出错: {str(e)}")

@app.post("/business-types")
async def create_business_type(business_type: dict):
    """创建新业务类型"""
    try:
        business_types = load_business_types()
        
        # 检查是否已存在
        for bt in business_types:
            if bt['name'] == business_type['name']:
                raise HTTPException(status_code=400, detail=f"业务类型 '{business_type['name']}' 已存在")
        
        # 添加新业务类型
        business_types.append(business_type)
        save_business_types(business_types)
        
        return business_type
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建业务类型时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建业务类型时出错: {str(e)}")

@app.delete("/business-types/{name}")
async def delete_business_type(name: str):
    """删除业务类型"""
    try:
        business_types = load_business_types()
        
        # 查找并删除业务类型
        original_length = len(business_types)
        business_types = [bt for bt in business_types if bt['name'] != name]
        
        if len(business_types) == original_length:
            raise HTTPException(status_code=404, detail=f"业务类型 '{name}' 不存在")
        
        save_business_types(business_types)
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除业务类型时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除业务类型时出错: {str(e)}")

DOCUMENT_ANALYSIS_FILE = "data/document_analysis.json"

def load_document_analysis():
    """加载文档分析结果"""
    if os.path.exists(DOCUMENT_ANALYSIS_FILE):
        with open(DOCUMENT_ANALYSIS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_document_analysis(analysis_data):
    """保存文档分析结果"""
    with open(DOCUMENT_ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)

@app.post("/save-business-type")
async def save_business_type_for_file(request: dict):
    """为文件保存业务类型，并自动分析文档结构，支持多文件融合"""
    try:
        filename = request.get('filename')
        business_type = request.get('business_type')
        split = request.get('split', False)
        file_path = request.get('file_path')
        
        if not filename or not business_type:
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        # 加载文件业务类型映射
        file_business_types = load_file_business_types()
        
        # 查找文件路径
        if not file_path or not os.path.exists(file_path):
            for f in os.listdir(UPLOAD_DIR):
                if filename in f or f.startswith(filename.split('.')[0]):
                    file_path = os.path.join(UPLOAD_DIR, f)
                    break
        
        document_analysis = None
        if file_path and os.path.exists(file_path):
            try:
                # 解析文件获取内容
                parse_result = parse_file(file_path)
                content = parse_result.get('full_content', '')
                
                if content:
                    # 分析文档结构
                    logger.info(f"开始分析文档结构: {filename}")
                    document_analysis = smart_document_generator.analyze_document_structure(content)
                    logger.info(f"文档分析完成，识别到 {len(document_analysis.get('variable_parts', []))} 个变量")
                    
                    # 加载已有的文档分析结果
                    analysis_data = load_document_analysis()
                    
                    # 如果该业务类型已有分析结果，进行融合
                    if business_type in analysis_data:
                        existing = analysis_data[business_type]
                        # 融合模板
                        merged_analysis = merge_document_analyses(
                            existing.get('analysis', {}),
                            document_analysis,
                            existing.get('files', []),
                            filename
                        )
                        # 更新文件列表
                        existing_files = existing.get('files', [])
                        if filename not in [f['filename'] for f in existing_files]:
                            existing_files.append({
                                'filename': filename,
                                'file_path': file_path,
                                'timestamp': str(datetime.now())
                            })
                        
                        analysis_data[business_type] = {
                            'filename': existing.get('filename', filename),
                            'business_type': business_type,
                            'analysis': merged_analysis,
                            'content': existing.get('content', '') + '\n\n--- 新增文件 ---\n\n' + content[:3000],
                            'files': existing_files,
                            'merged': True,
                            'timestamp': str(datetime.now())
                        }
                        document_analysis = merged_analysis
                    else:
                        # 新业务类型，直接保存
                        analysis_data[business_type] = {
                            'filename': filename,
                            'business_type': business_type,
                            'analysis': document_analysis,
                            'content': content[:5000],
                            'files': [{
                                'filename': filename,
                                'file_path': file_path,
                                'timestamp': str(datetime.now())
                            }],
                            'merged': False,
                            'timestamp': str(datetime.now())
                        }
                    
                    save_document_analysis(analysis_data)
            except Exception as e:
                logger.warning(f"文档分析失败: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning(f"文件不存在: {file_path}")
        
        # 保存文件业务类型映射
        file_business_types[filename] = {
            'business_type': business_type,
            'split': split,
            'timestamp': str(datetime.now()),
            'analyzed': document_analysis is not None
        }
        
        save_file_business_types(file_business_types)
        
        # 确保业务类型在列表中
        business_types = load_business_types()
        if business_type not in [bt['name'] for bt in business_types]:
            business_types.append({'name': business_type, 'created_at': str(datetime.now())})
            save_business_types(business_types)
        
        # 获取融合信息
        analysis_data = load_document_analysis()
        merged_info = analysis_data.get(business_type, {})
        
        return {
            "filename": filename,
            "business_type": business_type,
            "split": split,
            "analyzed": document_analysis is not None,
            "variable_count": len(document_analysis.get('variable_parts', [])) if document_analysis else 0,
            "reusable_count": len(document_analysis.get('reusable_parts', [])) if document_analysis else 0,
            "merged": merged_info.get('merged', False),
            "files_count": len(merged_info.get('files', []))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存业务类型时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存业务类型时出错: {str(e)}")


def merge_document_analyses(existing_analysis: dict, new_analysis: dict, 
                            existing_files: list, new_filename: str) -> dict:
    """融合两个文档分析结果
    
    Args:
        existing_analysis: 已有的分析结果
        new_analysis: 新的分析结果
        existing_files: 已有文件列表
        new_filename: 新文件名
        
    Returns:
        融合后的分析结果
    """
    # 合并可复用部分（去重）
    existing_reusable = existing_analysis.get('reusable_parts', [])
    new_reusable = new_analysis.get('reusable_parts', [])
    
    merged_reusable = []
    seen_contents = set()
    
    for part in existing_reusable + new_reusable:
        content_key = part.get('content', '')[:100]  # 用前100字符去重
        if content_key not in seen_contents:
            seen_contents.add(content_key)
            merged_reusable.append(part)
    
    # 合并变量部分（去重并整合描述）
    existing_vars = existing_analysis.get('variable_parts', [])
    new_vars = new_analysis.get('variable_parts', [])
    
    merged_vars = []
    var_map = {}  # 用描述作为key进行合并
    
    for var in existing_vars + new_vars:
        desc = var.get('description', '')
        if desc in var_map:
            # 合并示例
            existing_examples = var_map[desc].get('examples', [var_map[desc].get('example', '')])
            new_example = var.get('example', '')
            if new_example and new_example not in existing_examples:
                existing_examples.append(new_example)
            var_map[desc]['examples'] = existing_examples
        else:
            var_map[desc] = var.copy()
            var_map[desc]['examples'] = [var.get('example', '')] if var.get('example') else []
    
    for i, (desc, var) in enumerate(var_map.items()):
        var['id'] = f"var_{i}"
        var['description'] = desc
        if var.get('examples'):
            var['example'] = var['examples'][0]  # 取第一个作为示例
        merged_vars.append(var)
    
    # 合并结构
    existing_structure = existing_analysis.get('structure', [])
    new_structure = new_analysis.get('structure', [])
    
    merged_structure = existing_structure.copy()
    for item in new_structure:
        # 检查是否已存在类似结构
        content = item.get('content', '')[:50]
        exists = any(s.get('content', '')[:50] == content for s in merged_structure)
        if not exists:
            merged_structure.append(item)
    
    return {
        'reusable_parts': merged_reusable,
        'variable_parts': merged_vars,
        'structure': merged_structure,
        'paragraph_count': len(merged_structure),
        'variable_count': len(merged_vars),
        'reusable_count': len(merged_reusable),
        'merged_from': len(existing_files) + 1
    }

@app.get("/document-analysis/{business_type}")
async def get_document_analysis(business_type: str):
    """获取业务类型的文档分析结果"""
    try:
        analysis_data = load_document_analysis()
        
        if business_type not in analysis_data:
            raise HTTPException(status_code=404, detail=f"未找到业务类型 '{business_type}' 的分析结果")
        
        return analysis_data[business_type]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档分析结果时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档分析结果时出错: {str(e)}")

@app.get("/document-analysis")
async def list_document_analysis():
    """列出所有已分析的文档"""
    try:
        analysis_data = load_document_analysis()
        result = []
        for business_type, data in analysis_data.items():
            result.append({
                'business_type': business_type,
                'filename': data.get('filename', ''),
                'variable_count': len(data.get('analysis', {}).get('variable_parts', [])),
                'reusable_count': len(data.get('analysis', {}).get('reusable_parts', [])),
                'timestamp': data.get('timestamp', '')
            })
        return {"analyses": result}
    except Exception as e:
        logger.error(f"列出文档分析结果时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出文档分析结果时出错: {str(e)}")

class DeleteRequest(BaseModel):
    filename: str
    delete_vector: bool = True
    delete_knowledge_graph: bool = True
    delete_ner: bool = True

@app.post("/delete-file-data")
async def delete_file_data(request: DeleteRequest):
    """删除文件相关的数据（向量存储、知识图谱、NER数据）"""
    try:
        filename = request.filename
        delete_vector = request.delete_vector
        delete_knowledge_graph = request.delete_knowledge_graph
        delete_ner = request.delete_ner
        
        deleted_info = {
            "filename": filename,
            "deleted_vector": False,
            "deleted_knowledge_graph": False,
            "deleted_ner": False,
            "message": ""
        }
        
        # 删除向量存储中的数据
        if delete_vector:
            try:
                global vector_store
                from core.vector_store import VectorStore, TfidfVectorStore
                
                all_documents = vector_store.get_all_documents()
                documents_to_delete = []
                
                for doc in all_documents:
                    metadata = doc.get('metadata', {})
                    if metadata.get('source') == filename:
                        documents_to_delete.append(doc)
                
                if documents_to_delete:
                    # 重新构建向量存储，排除要删除的文档
                    remaining_texts = []
                    remaining_metadatas = []
                    
                    for doc in all_documents:
                        metadata = doc.get('metadata', {})
                        if metadata.get('source') != filename:
                            remaining_texts.append(doc['content'])
                            remaining_metadatas.append(metadata)
                    
                    # 重新初始化向量存储
                    vector_store = VectorStore()
                    if vector_store.use_simple_store:
                        vector_store.vector_store = TfidfVectorStore()
                    
                    # 重新添加剩余的文档
                    if remaining_texts:
                        vector_store.add_texts(remaining_texts, remaining_metadatas)
                    
                    # 保存向量存储
                    vector_store.save(VECTOR_STORE_PATH)
                    
                    deleted_info["deleted_vector"] = True
                    deleted_info["message"] += f"已从向量存储中删除 {len(documents_to_delete)} 个文档片段。"
                else:
                    deleted_info["message"] += "向量存储中未找到相关文档。"
            except Exception as e:
                logger.error(f"删除向量存储数据时出错: {str(e)}")
                deleted_info["message"] += f"删除向量存储数据失败: {str(e)}。"
        
        # 删除知识图谱中的数据
        if delete_knowledge_graph:
            try:
                # 获取所有关系
                all_relations = knowledge_graph.get_relations()
                
                # 筛选出与该文件相关的关系
                relations_to_delete = []
                for relation in all_relations:
                    metadata = relation.get('metadata', {})
                    if metadata.get('source') == filename:
                        relations_to_delete.append(relation)
                
                if relations_to_delete:
                    # 重新构建知识图谱，排除要删除的关系
                    new_graph = defaultdict(dict)
                    new_entities = defaultdict(set)
                    
                    for relation in all_relations:
                        metadata = relation.get('metadata', {})
                        if metadata.get('source') != filename:
                            subject = relation['subject']
                            predicate = relation['predicate']
                            object_ = relation['object']
                            
                            if subject not in new_graph:
                                new_graph[subject] = {}
                            if predicate not in new_graph[subject]:
                                new_graph[subject][predicate] = []
                            
                            new_graph[subject][predicate].append({
                                'object': object_,
                                'metadata': metadata
                            })
                            
                            new_entities['subjects'].add(subject)
                            new_entities['objects'].add(object_)
                    
                    # 更新知识图谱
                    knowledge_graph.graph = new_graph
                    knowledge_graph.entities = new_entities
                    knowledge_graph.save_to_disk()
                    
                    deleted_info["deleted_knowledge_graph"] = True
                    deleted_info["message"] += f"已从知识图谱中删除 {len(relations_to_delete)} 个关系。"
                else:
                    deleted_info["message"] += "知识图谱中未找到相关关系。"
            except Exception as e:
                logger.error(f"删除知识图谱数据时出错: {str(e)}")
                deleted_info["message"] += f"删除知识图谱数据失败: {str(e)}。"
        
        # 删除NER数据（NER数据主要存储在知识图谱中，所以这里主要是清理缓存）
        if delete_ner:
            try:
                # NER数据主要存储在知识图谱中，已经在上面处理
                # 这里可以清理NER处理器的缓存
                ner_processor.entity_cache.clear()
                
                deleted_info["deleted_ner"] = True
                deleted_info["message"] += "已清理NER缓存。"
            except Exception as e:
                logger.error(f"删除NER数据时出错: {str(e)}")
                deleted_info["message"] += f"删除NER数据失败: {str(e)}。"
        
        # 删除文件业务类型映射
        file_business_types = load_file_business_types()
        if filename in file_business_types:
            del file_business_types[filename]
            save_file_business_types(file_business_types)
            deleted_info["message"] += "已删除文件业务类型映射。"
        
        return deleted_info
    except Exception as e:
        logger.error(f"删除文件数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文件数据时出错: {str(e)}")

@app.post("/clear-all-data")
async def clear_all_data():
    """清空所有数据（向量存储、知识图谱、NER数据）"""
    try:
        deleted_info = {
            "deleted_vector": False,
            "deleted_knowledge_graph": False,
            "deleted_ner": False,
            "deleted_business_types": False,
            "deleted_file_mappings": False,
            "message": ""
        }
        
        # 清空向量存储
        try:
            global vector_store
            from core.vector_store import VectorStore, TfidfVectorStore
            
            # 重新初始化向量存储
            vector_store = VectorStore()
            if vector_store.use_simple_store:
                vector_store.vector_store = TfidfVectorStore()
            
            vector_store.save(VECTOR_STORE_PATH)
            deleted_info["deleted_vector"] = True
            deleted_info["message"] += "已清空向量存储。"
        except Exception as e:
            logger.error(f"清空向量存储时出错: {str(e)}")
            deleted_info["message"] += f"清空向量存储失败: {str(e)}。"
        
        # 清空知识图谱
        try:
            knowledge_graph.clear()
            deleted_info["deleted_knowledge_graph"] = True
            deleted_info["message"] += "已清空知识图谱。"
        except Exception as e:
            logger.error(f"清空知识图谱时出错: {str(e)}")
            deleted_info["message"] += f"清空知识图谱失败: {str(e)}。"
        
        # 清空NER缓存
        try:
            ner_processor.entity_cache.clear()
            deleted_info["deleted_ner"] = True
            deleted_info["message"] += "已清空NER缓存。"
        except Exception as e:
            logger.error(f"清空NER缓存时出错: {str(e)}")
            deleted_info["message"] += f"清空NER缓存失败: {str(e)}。"
        
        # 清空业务类型
        try:
            save_business_types([])
            deleted_info["deleted_business_types"] = True
            deleted_info["message"] += "已清空业务类型。"
        except Exception as e:
            logger.error(f"清空业务类型时出错: {str(e)}")
            deleted_info["message"] += f"清空业务类型失败: {str(e)}。"
        
        # 清空文件业务类型映射
        try:
            save_file_business_types({})
            deleted_info["deleted_file_mappings"] = True
            deleted_info["message"] += "已清空文件业务类型映射。"
        except Exception as e:
            logger.error(f"清空文件业务类型映射时出错: {str(e)}")
            deleted_info["message"] += f"清空文件业务类型映射失败: {str(e)}。"
        
        return deleted_info
    except Exception as e:
        logger.error(f"清空所有数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空所有数据时出错: {str(e)}")

@app.get("/data-status")
async def get_data_status():
    """获取数据状态统计"""
    try:
        status = {
            "vector_store": {
                "exists": False,
                "document_count": 0,
                "files": set()
            },
            "knowledge_graph": {
                "exists": False,
                "entity_count": 0,
                "relation_count": 0,
                "files": set()
            },
            "business_types": {
                "count": 0,
                "types": []
            },
            "file_mappings": {
                "count": 0,
                "files": []
            }
        }
        
        # 获取向量存储状态
        try:
            all_documents = vector_store.get_all_documents()
            status["vector_store"]["exists"] = True
            status["vector_store"]["document_count"] = len(all_documents)
            
            for doc in all_documents:
                metadata = doc.get('metadata', {})
                source = metadata.get('source', '未知')
                if source != '未知':
                    status["vector_store"]["files"].add(source)
            
            status["vector_store"]["files"] = list(status["vector_store"]["files"])
        except Exception as e:
            logger.error(f"获取向量存储状态时出错: {str(e)}")
        
        # 获取知识图谱状态
        try:
            stats = knowledge_graph.get_statistics()
            status["knowledge_graph"]["exists"] = True
            status["knowledge_graph"]["entity_count"] = stats['entities']
            status["knowledge_graph"]["relation_count"] = stats['relations']
            
            # 获取所有文件来源
            all_relations = knowledge_graph.get_relations()
            for relation in all_relations:
                metadata = relation.get('metadata', {})
                source = metadata.get('source', '未知')
                if source != '未知':
                    status["knowledge_graph"]["files"].add(source)
            
            status["knowledge_graph"]["files"] = list(status["knowledge_graph"]["files"])
        except Exception as e:
            logger.error(f"获取知识图谱状态时出错: {str(e)}")
        
        # 获取业务类型状态
        try:
            business_types = load_business_types()
            status["business_types"]["count"] = len(business_types)
            status["business_types"]["types"] = [bt['name'] for bt in business_types]
        except Exception as e:
            logger.error(f"获取业务类型状态时出错: {str(e)}")
        
        # 获取文件业务类型映射状态
        try:
            file_business_types = load_file_business_types()
            status["file_mappings"]["count"] = len(file_business_types)
            status["file_mappings"]["files"] = list(file_business_types.keys())
        except Exception as e:
            logger.error(f"获取文件业务类型映射状态时出错: {str(e)}")
        
        return status
    except Exception as e:
        logger.error(f"获取数据状态时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取数据状态时出错: {str(e)}")

# 智能文书生成API

class CreateSmartTemplateRequest(BaseModel):
    content: str
    template_name: str
    business_type: str = ""

class FillSmartTemplateRequest(BaseModel):
    template_id: str
    user_inputs: dict
    context: str = ""

class EditDocumentRequest(BaseModel):
    content: str
    edits: list

@app.post("/smart-templates/analyze")
async def analyze_document_structure(request: dict):
    """分析文档结构，识别可复用和不可复用部分"""
    try:
        content = request.get('content', '')
        if not content:
            raise HTTPException(status_code=400, detail="文档内容不能为空")
        
        analysis = smart_document_generator.analyze_document_structure(content)
        return analysis
    except Exception as e:
        logger.error(f"分析文档结构时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析文档结构时出错: {str(e)}")

@app.post("/smart-templates")
async def create_smart_template(request: CreateSmartTemplateRequest):
    """从文档创建智能模板"""
    try:
        template = smart_document_generator.create_template_from_document(
            content=request.content,
            template_name=request.template_name,
            business_type=request.business_type
        )
        return template
    except Exception as e:
        logger.error(f"创建智能模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建智能模板时出错: {str(e)}")

@app.get("/smart-templates")
async def list_smart_templates(business_type: str = None):
    """获取所有智能模板"""
    try:
        templates = smart_document_generator.list_templates(business_type)
        return {"templates": templates}
    except Exception as e:
        logger.error(f"获取智能模板列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取智能模板列表时出错: {str(e)}")

@app.get("/smart-templates/{template_id}")
async def get_smart_template(template_id: str):
    """获取指定智能模板"""
    try:
        template = smart_document_generator.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取智能模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取智能模板时出错: {str(e)}")

@app.delete("/smart-templates/{template_id}")
async def delete_smart_template(template_id: str):
    """删除智能模板"""
    try:
        success = smart_document_generator.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除智能模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除智能模板时出错: {str(e)}")

@app.post("/smart-templates/{template_id}/fill")
async def fill_smart_template(template_id: str, request: FillSmartTemplateRequest):
    """使用LLM填充和润色模板"""
    try:
        result = smart_document_generator.fill_template_with_llm(
            template_id=template_id,
            user_inputs=request.user_inputs,
            context=request.context
        )
        return result
    except Exception as e:
        logger.error(f"填充智能模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"填充智能模板时出错: {str(e)}")

@app.post("/smart-templates/extract-fields")
async def extract_fillable_fields(request: dict):
    """从文档内容中提取可填写字段"""
    try:
        content = request.get('content', '')
        if not content:
            raise HTTPException(status_code=400, detail="文档内容不能为空")
        
        fields = smart_document_generator.extract_fillable_fields(content)
        return {"fields": fields}
    except Exception as e:
        logger.error(f"提取可填写字段时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提取可填写字段时出错: {str(e)}")

@app.post("/smart-templates/edit")
async def edit_generated_document(request: EditDocumentRequest):
    """编辑生成的文档"""
    try:
        edited_content = smart_document_generator.edit_generated_document(
            generated_content=request.content,
            edits=request.edits
        )
        return {"content": edited_content}
    except Exception as e:
        logger.error(f"编辑文档时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"编辑文档时出错: {str(e)}")

# 新增：文档分析和生成API
class AnalyzeDocumentRequest(BaseModel):
    content: str

class GenerateDocumentRequest(BaseModel):
    analysis: dict
    user_inputs: dict
    context: str = ""

@app.post("/document/analyze")
async def analyze_document_for_template(request: AnalyzeDocumentRequest):
    """分析文档结构，识别可复用和不可复用部分"""
    try:
        if not request.content:
            raise HTTPException(status_code=400, detail="文档内容不能为空")
        
        analysis = smart_document_generator.analyze_document_structure(request.content)
        return analysis
    except Exception as e:
        logger.error(f"分析文档时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析文档时出错: {str(e)}")

@app.post("/document/generate")
async def generate_document_from_analysis(request: GenerateDocumentRequest):
    """根据分析结果和用户输入生成文书"""
    try:
        analysis = request.analysis
        user_inputs = request.user_inputs
        context = request.context
        
        # 构建生成提示
        prompt = smart_document_generator._build_generation_prompt_from_analysis(
            analysis, user_inputs, context
        )
        
        # 调用LLM生成
        generated_content = smart_document_generator._call_llm(prompt)
        
        return {
            "content": generated_content,
            "traceability": {
                "generated_at": datetime.now().isoformat(),
                "user_inputs": user_inputs,
                "variable_count": len(analysis.get('variable_parts', [])),
                "reusable_count": len(analysis.get('reusable_parts', []))
            }
        }
    except Exception as e:
        logger.error(f"生成文档时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成文档时出错: {str(e)}")

# ==================== 新的智能文书API（手动模板管理） ====================

@app.get("/templates-manual")
async def list_manual_templates():
    """获取所有手动管理的模板列表"""
    try:
        templates = template_manager.scan_templates()
        return {
            "templates": templates,
            "total": len(templates),
            "analyzed": sum(1 for t in templates if t["is_analyzed"])
        }
    except Exception as e:
        logger.error(f"获取模板列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板列表时出错: {str(e)}")


@app.get("/templates-manual/{template_name}")
async def get_manual_template(template_name: str):
    """获取指定模板的详细信息"""
    try:
        template = template_manager.get_template(template_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板不存在: {template_name}")
        
        # 如果已分析，返回分析结果
        if template["is_analyzed"]:
            analysis = template_manager.get_analysis(template_name)
            template["analysis"] = analysis
        
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板信息时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板信息时出错: {str(e)}")


@app.post("/templates-manual/{template_name}/analyze")
async def analyze_manual_template(template_name: str, force: bool = False):
    """分析指定模板文档结构
    
    Args:
        template_name: 模板名称
        force: 是否强制重新分析
    """
    try:
        result = template_manager.analyze_template(template_name, force_reanalyze=force)
        return {
            "success": True,
            "template_name": template_name,
            "analyzed_at": result["analyzed_at"],
            "variable_count": len(result.get("variable_parts", [])),
            "reusable_count": len(result.get("reusable_parts", [])),
            "analysis": result["analysis"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"分析模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析模板时出错: {str(e)}")


@app.get("/templates-manual/{template_name}/analysis")
async def get_manual_template_analysis(template_name: str):
    """获取模板的分析结果（如果已分析）"""
    try:
        analysis = template_manager.get_analysis(template_name)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"模板未分析或不存在: {template_name}")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析结果时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分析结果时出错: {str(e)}")


class GenerateFromTemplateRequest(BaseModel):
    template_name: str
    variables: dict


@app.post("/templates-manual/generate")
async def generate_from_manual_template(request: GenerateFromTemplateRequest):
    """根据手动管理的模板生成文书"""
    try:
        document = template_manager.generate_document(
            request.template_name, 
            request.variables
        )
        
        return {
            "success": True,
            "template_name": request.template_name,
            "content": document,
            "generated_at": datetime.now().isoformat(),
            "variables_used": list(request.variables.keys())
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成文书时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成文书时出错: {str(e)}")


@app.delete("/templates-manual/{template_name}")
async def delete_manual_template(template_name: str):
    """删除指定模板"""
    try:
        success = template_manager.delete_template(template_name)
        if not success:
            raise HTTPException(status_code=404, detail=f"模板不存在: {template_name}")
        return {"success": True, "message": f"模板已删除: {template_name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除模板时出错: {str(e)}")


@app.get("/templates-manual-stats")
async def get_manual_template_statistics():
    """获取模板统计信息"""
    try:
        stats = template_manager.get_template_statistics()
        return stats
    except Exception as e:
        logger.error(f"获取统计信息时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息时出错: {str(e)}")


if __name__ == "__main__":
    print("Starting server...")
    print("Loading dependencies...")
    import uvicorn
    print("Starting uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
