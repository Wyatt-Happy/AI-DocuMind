try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    HAS_LANGCHAIN = True
except Exception as e:
    print(f"导入 LangChain 失败: {e}")
    HAS_LANGCHAIN = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import time
from functools import lru_cache
import numpy as np
import pickle

class TfidfVectorStore:
    """基于TF-IDF和FAISS的向量存储，不依赖PyTorch"""
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=768)
        self.texts = []
        self.metadatas = []
        self.vectors = None
        self.index = None
        self.page_info = {}  # 块到页码的映射
    
    def add_texts(self, texts, metadatas):
        self.texts.extend(texts)
        self.metadatas.extend(metadatas)
        
        if self.vectors is None:
            self.vectors = self.vectorizer.fit_transform(self.texts)
        else:
            new_vectors = self.vectorizer.transform(texts)
            from scipy.sparse import vstack
            self.vectors = vstack([self.vectors, new_vectors])
        
        # 构建FAISS索引
        self._build_faiss_index()
    
    def _build_faiss_index(self):
        """构建FAISS索引"""
        if self.vectors is None:
            return
        
        import faiss
        vectors_array = self.vectors.toarray().astype('float32')
        dimension = vectors_array.shape[1]
        
        # 使用L2距离的FAISS索引
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(vectors_array)
    
    def similarity_search(self, query, k=5, filter=None):
        if self.vectors is None or self.index is None:
            return []
        
        query_vector = self.vectorizer.transform([query]).toarray().astype('float32')
        
        # 使用FAISS进行搜索
        distances, indices = self.index.search(query_vector, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.texts):
                # 创建一个类似FAISS结果的对象
                class Doc:
                    def __init__(self, page_content, metadata, score):
                        self.page_content = page_content
                        self.metadata = metadata
                        self.score = score
                results.append(Doc(self.texts[idx], self.metadatas[idx], float(distances[0][i])))
        
        return results
    
    def save(self, save_path):
        """保存向量存储"""
        os.makedirs(save_path, exist_ok=True)
        
        with open(os.path.join(save_path, 'vectorizer.pkl'), 'wb') as f:
            pickle.dump(self.vectorizer, f)
        
        with open(os.path.join(save_path, 'texts.pkl'), 'wb') as f:
            pickle.dump(self.texts, f)
        
        with open(os.path.join(save_path, 'metadatas.pkl'), 'wb') as f:
            pickle.dump(self.metadatas, f)
        
        # 保存页码信息
        with open(os.path.join(save_path, 'page_info.pkl'), 'wb') as f:
            pickle.dump(self.page_info, f)
        
        if self.index is not None:
            faiss.write_index(self.index, os.path.join(save_path, 'index.faiss'))
    
    def load(self, load_path):
        """加载向量存储"""
        if not os.path.exists(load_path):
            print(f"向量存储目录不存在: {load_path}")
            return
        
        vectorizer_path = os.path.join(load_path, 'vectorizer.pkl')
        if not os.path.exists(vectorizer_path):
            print(f"向量存储文件不存在: {vectorizer_path}")
            return
        
        try:
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            
            with open(os.path.join(load_path, 'texts.pkl'), 'rb') as f:
                self.texts = pickle.load(f)
            
            with open(os.path.join(load_path, 'metadatas.pkl'), 'rb') as f:
                self.metadatas = pickle.load(f)
            
            # 加载页码信息
            page_info_path = os.path.join(load_path, 'page_info.pkl')
            if os.path.exists(page_info_path):
                with open(page_info_path, 'rb') as f:
                    self.page_info = pickle.load(f)
            
            index_path = os.path.join(load_path, 'index.faiss')
            if os.path.exists(index_path):
                import faiss
                self.index = faiss.read_index(index_path)
                
                # 重建向量矩阵
                self.vectors = self.vectorizer.transform(self.texts)
                print(f"成功加载向量存储: {len(self.texts)}个文档")
        except Exception as e:
            print(f"加载向量存储失败: {e}")
            # 清理可能损坏的数据
            self.texts = []
            self.metadatas = []
            self.vectors = None
            self.index = None

class VectorStore:
    def __init__(self, embedding_model_name="models/bge-small-zh"):
        print(f"开始加载嵌入模型: {embedding_model_name}")
        start_time = time.time()
        
        if not HAS_LANGCHAIN:
            print("LangChain 不可用，使用TF-IDF + FAISS向量存储")
            self.embedding_model = None
            self.vector_store = TfidfVectorStore()
            self.use_simple_store = True
        else:
            try:
                print("正在初始化 HuggingFaceEmbeddings...")
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name=embedding_model_name,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                print(f"嵌入模型加载成功，耗时: {time.time() - start_time:.2f}秒")
                self.vector_store = None
                self.use_simple_store = False
            except Exception as e:
                print(f"加载嵌入模型失败，使用TF-IDF + FAISS向量存储: {e}")
                self.embedding_model = None
                self.vector_store = TfidfVectorStore()
                self.use_simple_store = True
        
        self.search_cache = {}
        print("向量存储初始化完成")
    
    def add_texts(self, texts, metadatas):
        """添加文本和元数据到向量库"""
        if self.use_simple_store:
            self.vector_store.add_texts(texts, metadatas)
            # 构建页码信息
            for i, text in enumerate(texts):
                if metadatas and i < len(metadatas):
                    page = metadatas[i].get('page', '未知')
                    self.vector_store.page_info[text] = page
        elif self.embedding_model and self.vector_store is None:
            self.vector_store = FAISS.from_texts(
                texts=texts,
                embedding=self.embedding_model,
                metadatas=metadatas
            )
            # 构建页码信息
            self.vector_store.page_info = {}
            for i, text in enumerate(texts):
                if metadatas and i < len(metadatas):
                    page = metadatas[i].get('page', '未知')
                    self.vector_store.page_info[text] = page
        elif self.embedding_model:
            self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas
            )
            # 更新页码信息
            if not hasattr(self.vector_store, 'page_info'):
                self.vector_store.page_info = {}
            for i, text in enumerate(texts):
                if metadatas and i < len(metadatas):
                    page = metadatas[i].get('page', '未知')
                    self.vector_store.page_info[text] = page
    
    def save(self, save_path):
        """保存向量库"""
        if self.use_simple_store:
            self.vector_store.save(save_path)
        elif self.vector_store:
            self.vector_store.save_local(save_path)
    
    def load(self, load_path):
        """加载向量库"""
        if self.use_simple_store:
            self.vector_store.load(load_path)
        elif os.path.exists(load_path) and self.embedding_model:
            try:
                self.vector_store = FAISS.load_local(
                    load_path,
                    self.embedding_model,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"加载向量库失败: {e}")
                self.vector_store = None
    
    def search(self, query, k=5, filter=None):
        """搜索相关文本"""
        # 生成缓存键
        cache_key = f"{query}_{k}_{str(filter)}"
        
        # 检查缓存
        if cache_key in self.search_cache:
            print(f"使用缓存结果 for query: {query}")
            return self.search_cache[cache_key]
        
        # 执行搜索
        if self.vector_store:
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            
            # 更新缓存
            self.search_cache[cache_key] = results
            
            # 限制缓存大小
            if len(self.search_cache) > 100:
                # 删除最旧的缓存
                oldest_key = next(iter(self.search_cache))
                del self.search_cache[oldest_key]
            
            return results
        return []
    
    def get_all_documents(self):
        """获取所有文档"""
        documents = []
        if self.use_simple_store:
            # 从简单向量存储获取所有文档
            for i, text in enumerate(self.vector_store.texts):
                documents.append({
                    'content': text,
                    'metadata': self.vector_store.metadatas[i] if i < len(self.vector_store.metadatas) else {}
                })
        elif self.vector_store:
            # 遍历所有文档
            try:
                # 尝试使用store属性（InMemoryDocstore）
                if hasattr(self.vector_store.docstore, 'store'):
                    for doc_id, doc in self.vector_store.docstore.store.items():
                        documents.append({
                            'content': doc.page_content,
                            'metadata': doc.metadata
                        })
                # 尝试使用items方法（其他类型的docstore）
                elif hasattr(self.vector_store.docstore, 'items'):
                    for doc_id, doc in self.vector_store.docstore.items():
                        documents.append({
                            'content': doc.page_content,
                            'metadata': doc.metadata
                        })
                # 尝试直接使用texts和metadatas属性（如果存在）
                elif hasattr(self.vector_store, 'texts') and hasattr(self.vector_store, 'metadatas'):
                    for i, text in enumerate(self.vector_store.texts):
                        documents.append({
                            'content': text,
                            'metadata': self.vector_store.metadatas[i] if i < len(self.vector_store.metadatas) else {}
                        })
                else:
                    # 如果都不行，使用搜索方法获取文档
                    # 搜索一个通用查询，获取所有文档
                    results = self.search("", k=1000)
                    for result in results:
                        documents.append({
                            'content': result.page_content,
                            'metadata': result.metadata
                        })
                    print(f"使用搜索方法获取了 {len(documents)} 个文档")
            except Exception as e:
                print(f"获取文档时出错: {e}")
        return documents
