import docx
import fitz

def parse_word_file(file_path):
    """解析 Word 文件"""
    try:
        doc = docx.Document(file_path)
        content = []
        paragraphs = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if text:
                content.append(text)
                paragraphs.append({
                    'text': text,
                    'paragraph_num': i + 1
                })
        return {
            'full_content': '\n'.join(content),
            'paragraphs': paragraphs,
            'file_type': 'docx',
            'total_paragraphs': len(paragraphs)
        }
    except Exception as e:
        print(f"解析 Word 文件失败: {e}")
        return {
            'full_content': "",
            'paragraphs': [],
            'file_type': 'docx',
            'total_paragraphs': 0
        }

def parse_pdf_file(file_path):
    """解析 PDF 文件"""
    try:
        doc = fitz.open(file_path)
        content = []
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            if text:
                content.append(f"页码 {page_num + 1}: {text}")
                pages.append({
                    'text': text,
                    'page_num': page_num + 1
                })
        return {
            'full_content': '\n'.join(content),
            'pages': pages,
            'file_type': 'pdf',
            'total_pages': len(pages)
        }
    except Exception as e:
        print(f"解析 PDF 文件失败: {e}")
        return {
            'full_content': "",
            'pages': [],
            'file_type': 'pdf',
            'total_pages': 0
        }

def parse_file(file_path):
    """根据文件类型解析文件"""
    if file_path.endswith('.docx'):
        result = parse_word_file(file_path)
        result['file_path'] = file_path
        return result
    elif file_path.endswith('.pdf'):
        result = parse_pdf_file(file_path)
        result['file_path'] = file_path
        return result
    else:
        print(f"不支持的文件类型: {file_path}")
        return {
            'full_content': "",
            'file_path': file_path,
            'file_type': 'unknown',
            'total_pages': 0,
            'total_paragraphs': 0
        }
