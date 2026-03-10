# AI智能档案系统

一个基于FastAPI和AI技术的智能档案管理系统，支持文件上传、业务类型管理、智能问答和人员查询等功能。

## 功能特性

- **文件上传**：支持上传.docx和.pdf文件，自动提取文本和实体信息
- **业务类型管理**：添加、删除和管理业务类型，为文件分类
- **智能问答**：基于千问百炼API的智能问答功能，提供详细的回答和溯源信息
- **人员查询**：查询人员履历和时间轴，可视化展示人员相关事件

## 技术路线

### 前端
- HTML5 + CSS3 + JavaScript
- 响应式设计，支持不同设备访问
- 动态交互，实时显示操作结果

### 后端
- FastAPI：高性能异步Web框架
- Python 3.11+：主要开发语言
- PyTorch：用于深度学习模型
- Sentence-BERT：用于文本嵌入和相似度计算
- FAISS：高效的向量搜索库
- 千问百炼API：提供智能问答能力

### 数据处理
- 文本提取：从PDF和Word文件中提取文本
- 实体识别：识别文本中的人员、时间、组织等实体
- 知识图谱：构建和管理实体之间的关系
- 向量存储：将文本转换为向量并存储，支持快速检索

## 项目结构

```
├── main.py              # 主应用入口
├── static/              # 静态文件目录
│   └── index.html       # 前端页面
├── utils/               # 工具类目录
│   ├── file_parser.py   # 文件解析工具
│   ├── ner_processor.py # 实体识别处理器
│   ├── vector_store.py  # 向量存储
│   ├── knowledge_graph.py # 知识图谱
│   ├── qa_processor.py  # 智能问答处理器
│   ├── document_processor.py # 文档处理器
│   ├── case_analyzer.py # 案件分析器
│   ├── timeline_generator.py # 时间轴生成器
│   ├── multimodal_processor.py # 多模态处理器
│   └── pdf_processor.py # PDF处理器
├── data/                # 数据存储目录
│   ├── uploads/         # 上传文件存储
│   ├── vector_store/    # 向量存储
│   ├── business_types.json # 业务类型配置
│   └── file_business_types.json # 文件业务类型映射
├── models/              # 模型目录
│   └── bge-small-zh     # 中文嵌入模型
└── README.md            # 项目说明文件
```

## 核心功能说明

### 1. 文件上传

- 支持上传.docx和.pdf文件
- 自动提取文本内容和实体信息
- 支持为文件设置业务类型
- 支持拆分文档为多个片段

### 2. 业务类型管理

- 添加新的业务类型，包含名称和描述
- 查看所有已创建的业务类型
- 删除不需要的业务类型
- 业务类型数据持久化存储

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

## 快速开始

### 环境要求

- Python 3.11+
- PyTorch 2.0+
- FastAPI
- 其他依赖包（见requirements.txt）

### 安装步骤

1. 克隆项目代码

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 下载嵌入模型（bge-small-zh）并放入models目录

4. 配置千问百炼API密钥（可选）
   - 在环境变量中设置`DASHSCOPE_API_KEY`

5. 启动服务器
   ```bash
   python main.py
   ```

6. 访问系统
   - 前端界面：http://localhost:8000/ui/
   - API接口：http://localhost:8000/

## API接口说明

### 文件上传
- `POST /upload` - 上传文件并处理

### 业务类型管理
- `GET /business-types` - 获取所有业务类型
- `POST /business-types` - 创建新业务类型
- `DELETE /business-types/{name}` - 删除业务类型
- `POST /save-business-type` - 为文件保存业务类型

### 智能问答
- `POST /ask` - 提交问题并获取回答

### 人员查询
- `GET /query` - 查询人员履历
- `GET /timeline/{person_id}` - 获取人员时间轴

### 其他接口
- `GET /status` - 获取系统状态
- `GET /templates` - 列出所有文书模板
- `POST /generate-document` - 根据模板生成文书
- `GET /case-analysis` - 获取案件统计分析结果

## 技术亮点

1. **智能检索**：使用向量存储和相似度计算，实现高效的文档检索
2. **知识图谱**：构建实体之间的关系，提供更丰富的语义理解
3. **AI问答**：集成千问百炼API，提供高质量的智能问答能力
4. **可视化时间轴**：直观展示人员相关事件的时间线
5. **模块化设计**：清晰的代码结构，便于维护和扩展

## 未来规划

1. 支持更多文件格式
2. 增强多模态处理能力
3. 优化向量存储和检索性能
4. 添加用户权限管理
5. 提供更多定制化的分析报告

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎联系项目维护者。