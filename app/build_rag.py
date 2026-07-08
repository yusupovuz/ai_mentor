import contextlib
import huggingface_hub.file_download
huggingface_hub.file_download.FileLock = contextlib.nullcontext

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def build_vector_database():
    loader = PyPDFLoader('../data/python.pdf')
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory='./chroma_db'
    )
    
    print("Muvaffaqiyatli yakunlandi! RAG bazasi 'chroma_db' papkasida tayyor.")

if __name__ == '__main__':
    build_vector_database()