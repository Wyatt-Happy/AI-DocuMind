import os
import logging
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置环境变量以解决PyTorch DLL加载问题
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'

# 首先导入PyTorch，确保它正确加载
try:
    import torch
    print(f"PyTorch导入成功: {torch.__version__}")
except Exception as e:
    print(f"PyTorch导入失败: {e}")

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

class QuestionRequest(BaseModel):
    question: str
import uuid
import re
from datetime import datetime
from utils.file_parser import parse_file
from utils.ner_processor import NERProcessor
from utils.vector_store import VectorStore
from utils.retrieval_integration import RetrievalIntegration
from utils.knowledge_graph import KnowledgeGraph
from utils.qa_processor import QAProcessor
from utils.document_processor import DocumentProcessor
from utils.case_analyzer import CaseAnalyzer
from utils.timeline_generator import TimelineGenerator
from utils.multimodal_processor import MultimodalProcessor
from utils.pdf_processor import PDFProcessor

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
    from utils.vector_store import VectorStore
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
print("Creating case analyzer...")
case_analyzer = CaseAnalyzer()
print("Creating timeline generator...")
timeline_generator = TimelineGenerator()
print("Creating multimodal processor...")
multimodal_processor = MultimodalProcessor()
print("Creating PDF processor...")
pdf_processor = PDFProcessor()
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
        # 对于PDF文件，我们使用pdf_processor处理，所以即使fitz解析失败也继续
        if not content and parse_result['file_type'] != 'pdf':
            print("文件解析失败：内容为空")
            raise HTTPException(status_code=500, detail="文件解析失败")
        
        # 对于PDF文件，如果fitz解析失败，使用pdf_processor提取的文本
        if not content and parse_result['file_type'] == 'pdf':
            print("fitz解析失败，使用pdf_processor提取文本")
            text, page_numbers = pdf_processor.extract_text_with_page_numbers(file_path)
            content = text
            
            # 检查pdf_processor是否提取到了文本
            if not content:
                print("PDF文件无文本内容")
                raise HTTPException(status_code=500, detail="文件解析失败：PDF文件无文本内容")
        
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
            # 使用新的PDF处理方式
            print("使用新的PDF处理方式")
            # 检查是否已经提取过文本
            if 'page_numbers' in locals():
                # 已经提取过文本，直接使用
                chunks, metadatas = pdf_processor.process_text_with_splitter(text, page_numbers)
            else:
                # 未提取过文本，重新提取
                text, page_numbers = pdf_processor.extract_text_with_page_numbers(file_path)
                chunks, metadatas = pdf_processor.process_text_with_splitter(text, page_numbers)
            
            # 为每个块添加额外的元数据
            for i, metadata in enumerate(metadatas):
                metadata.update({
                    "source": file.filename,
                    "file_type": 'pdf'
                })
                
                # 提取当前片段的实体
                chunk_entities = ner_processor.process_text(chunks[i])
                metadata.update({
                    "persons": chunk_entities["persons"],
                    "times": chunk_entities["times"],
                    "organizations": chunk_entities.get("organizations", []),
                    "positions": chunk_entities.get("positions", [])
                })
                
                # 为每个片段构建知识图谱关系
                if knowledge_graph:
                    chunk_metadata = {
                        "source": file.filename,
                        "page": f"页码 {metadata['page']}",
                        "timestamp": str(datetime.now())
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
                    "source": file.filename,
                    "page": f"段落 {paragraph_num}",
                    "paragraph_num": paragraph_num,
                    "persons": chunk_entities["persons"],
                    "times": chunk_entities["times"],
                    "organizations": chunk_entities.get("organizations", []),
                    "positions": chunk_entities.get("positions", []),
                    "file_type": 'docx'
                }
                
                # 添加到列表
                chunks.append(text)
                metadatas.append(metadata)
                
                # 为每个片段构建知识图谱关系
                if knowledge_graph:
                    chunk_metadata = {
                        "source": file.filename,
                        "page": f"段落 {paragraph_num}",
                        "timestamp": str(datetime.now())
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
                        "source": file.filename,
                        "page": f"片段 {i+1}",
                        "persons": chunk_entities["persons"],
                        "times": chunk_entities["times"],
                        "organizations": chunk_entities.get("organizations", []),
                        "positions": chunk_entities.get("positions", []),
                        "file_type": parse_result['file_type']
                    }
                    
                    # 添加到列表
                    chunks.append(segment)
                    metadatas.append(metadata)
                    
                    # 为每个片段构建知识图谱关系
                    if knowledge_graph:
                        chunk_metadata = {
                            "source": file.filename,
                            "page": f"片段 {i+1}",
                            "timestamp": str(datetime.now())
                        }
                        knowledge_graph.build_from_entities(chunk_entities, chunk_metadata)
        
        # 添加到向量库
        print(f"添加 {len(chunks)} 个片段到向量库")
        vector_store.add_texts(chunks, metadatas)
        vector_store.save(VECTOR_STORE_PATH)
        
        # 处理多模态内容
        print("处理多模态内容")
        multimodal_result = multimodal_processor.process_document(file_path)
        
        return {
            "filename": file.filename,
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

@app.post("/save-business-type")
async def save_business_type_for_file(request: dict):
    """为文件保存业务类型"""
    try:
        filename = request.get('filename')
        business_type = request.get('business_type')
        split = request.get('split', False)
        
        if not filename or not business_type:
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        # 加载文件业务类型映射
        file_business_types = load_file_business_types()
        
        # 保存文件业务类型映射
        file_business_types[filename] = {
            'business_type': business_type,
            'split': split,
            'timestamp': str(datetime.now())
        }
        
        save_file_business_types(file_business_types)
        
        return {
            "filename": filename,
            "business_type": business_type,
            "split": split
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存业务类型时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存业务类型时出错: {str(e)}")

if __name__ == "__main__":
    print("Starting server...")
    print("Loading dependencies...")
    import uvicorn
    print("Starting uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
