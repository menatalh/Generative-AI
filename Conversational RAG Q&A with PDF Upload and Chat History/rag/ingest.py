import os
import re
import tempfile
from typing import Protocol

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# control characters PDFs sometimes contain, keeping \t \n \r
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

class UploadedPDF(Protocol):
    """What we need from Streamlit's UploadedFile"""
    name: str
    size: int
    def getvalue(self) -> bytes: ...

def sanitize(text: str) -> str:
    return CONTROL_CHARS.sub("", text).strip()

def load_pdfs(files: list[UploadedPDF], max_file_mb: int) -> tuple[list[Document], list[str]]:
    """Load uploaded PDFs into page documents; return the docs and an error message per skipped file"""
    docs, errors = [], []
    with tempfile.TemporaryDirectory() as tmp_dir:
        for f in files:
            if not f.name.lower().endswith(".pdf"):
                errors.append(f"{f.name}: not a PDF")
                continue
            if f.size > max_file_mb * 1024 * 1024:
                errors.append(f"{f.name}: larger than {max_file_mb} MB")
                continue

            path = os.path.join(tmp_dir, os.path.basename(f.name))
            with open(path, "wb") as out:
                out.write(f.getvalue())
            try:
                pages = PyPDFLoader(path).load()
            except Exception as e:
                errors.append(f"{f.name}: could not be read ({e})")
                continue

            for p in pages:
                p.page_content = sanitize(p.page_content)
                p.metadata["source"] = f.name
            pages = [p for p in pages if p.page_content]
            if not pages:
                errors.append(f"{f.name}: no extractable text (scanned PDF?)")
                continue
            docs.extend(pages)
    return docs, errors

def split_documents(docs: list[Document], chunk_size: int, chunk_overlap: int) -> list[Document]:
    return RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_documents(docs)

def index_documents(vectorstore: Chroma, chunks: list[Document]):
    """Replace the collection's contents with these chunks, so re-uploads don't duplicate and removed PDFs disappear"""
    vectorstore.reset_collection()
    if chunks:
        vectorstore.add_documents(chunks)
