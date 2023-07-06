
import os
from dotenv import load_dotenv
import logging
from typing import Optional

from langchain.vectorstores.base import VectorStore
import pandas as pd
import urllib

from .azuresearch import AzureSearch
from .LLMHelper import LLMHelper
from .ConfigHelper import ConfigHelper, Config
from .DocumentLoading import DocumentLoading, Loading, LoadingStrategy
from .DocumentChunking import DocumentChunking

class DocumentProcessor:
    def __init__(self):
        load_dotenv()        
        # Azure Search settings
        self.azure_search_endpoint: str = os.getenv("AZURE_SEARCH_SERVICE")
        self.azure_search_key: str = os.getenv("AZURE_SEARCH_KEY")
        self.index_name: str = os.getenv("AZURE_SEARCH_INDEX")
        self.embeddings = LLMHelper().get_embedding_model()
        self.vector_store: AzureSearch = AzureSearch(
                azure_cognitive_search_name=self.azure_search_endpoint,
                azure_cognitive_search_key=self.azure_search_key,
                index_name=self.index_name,
                embedding_function=self.embeddings.embed_query)
        self.k: int = 4
        
    def process(self, source_url: str, config: Config = ConfigHelper.get_active_config_or_default(), loading: Loading = Loading({"strategy": "layout"})):
        try:
            document_loading = DocumentLoading()
            document_chunking = DocumentChunking()
            documents = document_loading.load(source_url, loading)
            documents = document_chunking.chunk(documents, config.chunking[0])
            keys = list(map(lambda x: x.metadata['key'], documents))
            return self.vector_store.add_documents(documents=documents, keys=keys)
        except Exception as e:
            logging.error(f"Error adding embeddings for {source_url}: {e}")
            raise e
    
    def get_all_documents(self, k: Optional[int] = None):
        result = self.vector_store.similarity_search(query="*", k=k if k else self.k)
        return pd.DataFrame(
            list(
                map(
                    lambda x: {
                        "key": x.metadata["key"],
                        "filename": x.metadata["filename"],
                        "source": urllib.parse.unquote(x.metadata["source"]),
                        "content": x.page_content,
                        "metadata": x.metadata,
                    },
                    result,
                )
            )
        )