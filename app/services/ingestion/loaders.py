import os
import io
import asyncio
try:
    import pandas as pd
except Exception:
    pd = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import docx
except Exception:
    docx = None
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

class DocumentLoader:
    """Base class for all document loaders."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        raise NotImplementedError()

class PDFLoader(DocumentLoader):
    """Loads PDF files using pdfplumber to extract page text and metadata."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        def _load():
            documents = []
            filename = os.path.basename(source_path)
            with pdfplumber.open(source_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        documents.append({
                            "text": text,
                            "metadata": {
                                "source": filename,
                                "page": i + 1,
                                "total_pages": len(pdf.pages)
                            }
                        })
            return documents
        
        return await asyncio.get_running_loop().run_in_executor(executor, _load)

class DocxLoader(DocumentLoader):
    """Loads Microsoft Word documents (.docx)."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        def _load():
            filename = os.path.basename(source_path)
            doc = docx.Document(source_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text_content = "\n".join(paragraphs)
            return [{
                "text": text_content,
                "metadata": {
                     "source": filename
                }
            }]
            
        return await asyncio.get_running_loop().run_in_executor(executor, _load)

class CSVLoader(DocumentLoader):
    """Loads CSV files, transforming rows into formatted text lines."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        def _load():
            filename = os.path.basename(source_path)
            df = pd.read_csv(source_path)
            documents = []
            for index, row in df.iterrows():
                row_str = ", ".join([f"{col}: {val}" for col, val in row.items()])
                documents.append({
                    "text": row_str,
                    "metadata": {
                        "source": filename,
                        "row": index + 1
                    }
                })
            return documents
            
        return await asyncio.get_running_loop().run_in_executor(executor, _load)

class TextLoader(DocumentLoader):
    """Loads plain text files (.txt)."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        def _load():
            filename = os.path.basename(source_path)
            with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return [{
                "text": content,
                "metadata": {
                    "source": filename
                }
            }]
            
        return await asyncio.get_running_loop().run_in_executor(executor, _load)


class ExcelLoader(DocumentLoader):
    """Loads Excel files (.xlsx) and converts rows into text lines."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        def _load():
            filename = os.path.basename(source_path)
            documents = []
            xls = pd.read_excel(source_path, sheet_name=None)
            for sheet_name, df in xls.items():
                for idx, row in df.iterrows():
                    row_str = ", ".join([f"{col}: {val}" for col, val in row.items()])
                    documents.append({
                        "text": row_str,
                        "metadata": {"source": filename, "sheet": sheet_name, "row": idx + 1}
                    })
            return documents

        return await asyncio.get_running_loop().run_in_executor(executor, _load)


class ZipLoader(DocumentLoader):
    """Loads zip archives and extracts text from contained files (txt, csv, json)."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        import zipfile

        def _load():
            filename = os.path.basename(source_path)
            documents = []
            with zipfile.ZipFile(source_path, 'r') as z:
                for name in z.namelist():
                    if name.endswith(('.txt', '.csv', '.json')):
                        with z.open(name) as fh:
                            try:
                                content = fh.read().decode('utf-8')
                            except Exception:
                                content = ''
                            if content.strip():
                                documents.append({
                                    "text": content,
                                    "metadata": {"source": f"{filename}:{name}", "inner_path": name}
                                })
            return documents

        return await asyncio.get_running_loop().run_in_executor(executor, _load)

class ImageLoader(DocumentLoader):
    """Fallback loader for images. Since OCR is not fully installed in this environment, it extracts metadata."""
    async def load(self, source_path: str) -> List[Dict[str, Any]]:
        def _load():
            filename = os.path.basename(source_path)
            content = f"Image file: {filename}\nNote: OCR text extraction is pending or unavailable."
            return [{
                "text": content,
                "metadata": {
                    "source": filename,
                    "type": "image"
                }
            }]
        return await asyncio.get_running_loop().run_in_executor(executor, _load)
