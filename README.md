# DocuMind AI - 智能档案管理系统

一个基于FastAPI和AI技术的智能档案管理系统，支持文件上传、业务类型管理、智能问答、人员查询和智能文书生成等功能。

## 功能特性

- **文件上传**：支持上传.docx和.pdf文件，自动提取文本、表格和实体信息
- **业务类型管理**：添加、删除和管理业务类型，为文件分类，支持模板融合
- **智能问答**：基于千问百炼API的智能问答功能，提供详细的回答和溯源信息
- **人员查询**：查询人员履历和时间轴，可视化展示人员相关事件
- **智能文书生成**：AI分析文档结构，识别可复用和不可复用部分，自动生成文书
- **模板融合**：同一业务类型的多个文件自动融合，生成更全面的模板

## 技术路线

```
文档进入 → pdfplumber提取文本和表格 → 基于段落和页面的智能分割算法
    → TF-IDF + FAISS向量存储 → 千问百炼API智能问答/文书生成
```

### 前端
- HTML5 + CSS3 + JavaScript
- 响应式设计，支持不同设备访问
- 动态交互，实时显示操作结果

### 后端
- **FastAPI**：高性能异步Web框架
- **Python 3.11+**：主要开发语言
- **TF-IDF + FAISS**：高效的向量搜索
- **千问百炼API**：提供智能问答和文书生成能力
- **pdfplumber**：PDF文本和表格提取
- **python-docx**：Word文档解析

### 数据处理
- **文本提取**：从PDF和Word文件中提取文本和表格
- **实体识别(NER)**：识别文本中的人员、时间、组织等实体
- **知识图谱**：构建和管理实体之间的关系
- **向量存储**：将文本转换为向量并存储，支持快速检索

## 项目结构

```
DocuMind_AI/
├── main.py                          # 主应用入口，API路由定义
├── static/
│   └── index.html                   # 前端页面
│
├── core/                            # 核心模块
│   ├── vector_store.py              # 向量存储（TF-IDF + FAISS）
│   ├── knowledge_graph.py           # 知识图谱构建与管理
│   └── ner_processor.py             # 命名实体识别处理器
│
├── qa_system/                       # 智能问答模块
│   ├── qa_processor.py              # 问答处理器（千问百炼API）
│   └── retrieval_integration.py     # 检索集成
│
├── document_processing/             # 文档处理模块
│   ├── file_parser.py               # 文件解析器（PDF/DOCX）
│   ├── document_processor.py        # 文档处理器
│   └── smart_document_generator.py  # 智能文书生成器
│
├── analysis/                        # 分析模块
│   ├── case_analyzer.py             # 案件分析器
│   └── timeline_generator.py        # 时间轴生成器
│
├── multimodal/                      # 多模态处理模块
│   └── multimodal_processor.py      # 多模态处理器（图片/表格）
│
├── data/                            # 数据存储目录
│   ├── uploads/                     # 上传文件存储
│   ├── vector_store/                # 向量存储文件
│   ├── knowledge_graph/             # 知识图谱数据
│   ├── multimodal/                  # 多模态数据（图片/表格）
│   ├── templates/                   # 文书模板
│   ├── timelines/                   # 时间轴数据
│   ├── case_analysis/               # 案件分析结果
│   ├── business_types.json          # 业务类型配置
│   ├── file_business_types.json     # 文件业务类型映射
│   └── document_analysis.json       # 文档分析结果（模板融合）
│
└── README.md                        # 项目说明文件
```

## 核心功能说明

### 1. 文件上传

- 支持上传.docx和.pdf文件
- 自动提取文本内容、表格和实体信息
- 支持为文件设置业务类型
- 自动分析文档结构，识别可复用和不可复用部分
- 支持拆分文档为多个片段

### 2. 业务类型管理

- 添加新的业务类型
- 查看所有已创建的业务类型
- 删除不需要的业务类型
- 业务类型数据持久化存储
- **模板融合**：同一业务类型的多个文件自动融合

### 3. 智能问答

- 输入问题后，系统会检索相关文档
- 使用千问百炼API生成高质量的回答
- 自动提取并显示溯源信息（信息来源）
- 支持复杂问题的处理和分析

### 4. 人员查询

- 输入人员姓名后，查询相关履历信息
- 生成人员事件时间轴，可视化展示
- 时间轴包含事件时间、类型、内容和来源
- 支持多维度的人员信息展示

### 5. 智能文书生成

- **AI分析文档结构**：识别可复用部分和需要填写的变量
- **模板融合**：同一业务类型多个文件自动融合，生成更全面的模板
- **完型填空式填写**：用户只需填写变量部分
- **LLM生成润色**：千问百炼API生成专业文书
- **溯源信息**：记录生成过程和填写内容

### 6. 数据管理

- 查看系统数据状态
- 删除向量存储、知识图谱、NER数据
- 管理业务类型和文件映射

## 快速开始

### 环境要求

- Python 3.11+
- FastAPI
- 其他依赖包（见requirements.txt）

### 安装步骤

1. 克隆项目代码
   ```bash
   git clone git@github.com:Wyatt-Happy/AI-.git
   cd AI-
   ```

2. 创建虚拟环境并安装依赖
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. 配置千问百炼API密钥
   - 在环境变量中设置 `DASHSCOPE_API_KEY`
   - 或在系统环境变量中添加

4. 启动服务器
   ```bash
   python main.py
   ```

5. 访问系统
   - 前端界面：http://localhost:8000/ui/
   - API接口：http://localhost:8000/

## API接口说明

### 文件上传
- `POST /upload` - 上传文件并处理

### 业务类型管理
- `GET /business-types` - 获取所有业务类型
- `POST /business-types` - 创建新业务类型
- `DELETE /business-types/{name}` - 删除业务类型
- `POST /save-business-type` - 为文件保存业务类型（自动分析文档结构）

### 智能问答
- `POST /ask` - 提交问题并获取回答

### 人员查询
- `GET /query` - 查询人员履历
- `GET /timeline/{person_id}` - 获取人员时间轴

### 智能文书生成
- `GET /document-analysis` - 列出所有已分析的文档
- `GET /document-analysis/{business_type}` - 获取业务类型的文档分析结果
- `POST /document/analyze` - 分析文档结构
- `POST /document/generate` - 根据分析结果生成文书

### 数据管理
- `GET /data-status` - 获取数据状态
- `POST /delete-file-data` - 删除文件相关数据
- `POST /clear-all-data` - 清空所有数据

## 技术亮点

1. **智能检索**：使用TF-IDF + FAISS向量存储，实现高效的文档检索
2. **知识图谱**：构建实体之间的关系，提供更丰富的语义理解
3. **AI问答**：集成千问百炼API，提供高质量的智能问答能力
4. **智能文书生成**：AI分析文档结构，自动识别可复用和不可复用部分
5. **模板融合**：同一业务类型多个文件自动融合，生成更全面的模板
6. **可视化时间轴**：直观展示人员相关事件的时间线
7. **模块化设计**：清晰的代码结构，便于维护和扩展

## 智能文书生成流程

```
1. 文件上传 → 选择业务类型 → 保存
       ↓
2. AI自动分析文档结构
   - 识别可复用部分（固定格式、通用表述）
   - 识别不可复用部分（人名、日期、案号等变量）
       ↓
3. 模板融合（如果同一业务类型有多个文件）
   - 合并可复用部分（去重）
   - 整合变量部分（合并示例）
       ↓
4. 用户选择业务类型 → 填写变量 → 生成文书
       ↓
5. LLM润色生成 → 显示溯源信息
```

## 未来规划

1. 支持更多文件格式
2. 增强多模态处理能力
3. 优化向量存储和检索性能
4. 添加用户权限管理
5. 提供更多定制化的分析报告
6. 支持文书模板导出和导入

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎联系项目维护者。
