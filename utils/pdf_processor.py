from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Tuple, Dict, Any
import logging
import os
import pickle

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF文档处理器"""
    
    def extract_text_with_page_numbers(self, pdf_path: str) -> Tuple[str, List[int]]:
        """
        从PDF中提取文本并记录每行文本对应的页码
        
        参数:
            pdf_path: PDF文件路径
        
        返回:
            text: 提取的文本内容
            page_numbers: 每行文本对应的页码列表
        """
        text = ""
        page_numbers = []
        
        try:
            pdf = PdfReader(pdf_path)
            
            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        text += extracted_text
                        page_numbers.extend([page_number] * len(extracted_text.split("\n")))
                    else:
                        logging.warning(f"No text found on page {page_number}.")
                except Exception as e:
                    logging.error(f"Error processing page {page_number}: {e}")
                    continue
        except Exception as e:
            logging.error(f"Error extracting text: {e}")
            return "", []
        
        return text, page_numbers
    
    def process_text_with_splitter(self, text: str, page_numbers: List[int]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        智能处理文本并创建块
        
        参数:
            text: 提取的文本内容
            page_numbers: 每行文本对应的页码列表
        
        返回:
            chunks: 分割后的文本块
            metadatas: 每个块的元数据
        """
        # 改进的文本分割策略
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", "，", "。", " ", ""],  # 添加中文标点
            chunk_size=512,
            chunk_overlap=128,
            length_function=len,
            is_separator_regex=False
        )
        
        # 分割文本
        chunks = text_splitter.split_text(text)
        logger.info(f"文本被分割成 {len(chunks)} 个块。")
        
        # 为每个块分配页码和其他元数据
        metadatas = []
        text_lines = text.split("\n")
        
        for i, chunk in enumerate(chunks):
            # 找到块的第一行对应的页码
            chunk_lines = chunk.split("\n")
            if chunk_lines:
                first_line = chunk_lines[0]
                # 查找第一行在原文本中的位置
                for line_idx, line in enumerate(text_lines):
                    if line.strip() == first_line.strip():
                        if line_idx < len(page_numbers):
                            page = page_numbers[line_idx]
                            break
                else:
                    page = 1  # 默认为第一页
            else:
                page = 1
            
            # 创建元数据
            metadata = {
                "page": page,
                "chunk_id": i,
                "chunk_length": len(chunk)
            }
            metadatas.append(metadata)
        
        return chunks, metadatas
    
    def save_page_info(self, chunks: List[str], metadatas: List[Dict[str, Any]], save_path: str):
        """
        保存块和页码信息
        
        参数:
            chunks: 文本块
            metadatas: 元数据
            save_path: 保存路径
        """
        os.makedirs(save_path, exist_ok=True)
        
        # 保存页码信息
        page_info = {chunk: metadata['page'] for chunk, metadata in zip(chunks, metadatas)}
        with open(os.path.join(save_path, "page_info.pkl"), "wb") as f:
            pickle.dump(page_info, f)
        logger.info(f"页码信息已保存到: {os.path.join(save_path, 'page_info.pkl')}")
    
    def load_page_info(self, load_path: str) -> Dict[str, int]:
        """
        加载页码信息
        
        参数:
            load_path: 加载路径
        
        返回:
            page_info: 块到页码的映射
        """
        page_info_path = os.path.join(load_path, "page_info.pkl")
        if os.path.exists(page_info_path):
            with open(page_info_path, "rb") as f:
                page_info = pickle.load(f)
            logger.info("页码信息已加载。")
            return page_info
        else:
            logger.warning("未找到页码信息文件。")
            return {}
