"""
Vector store management using ChromaDB for FAQ retrieval.
"""
import time
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from src.config import settings
from src.observability.logging_config import get_logger
from src.observability.tracing import trace_function
from src.observability import metrics

logger = get_logger(__name__)


class VectorStoreManager:
    """
    Manages ChromaDB vector store for FAQ retrieval.
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize the vector store manager.

        Args:
            persist_dir: Directory to persist ChromaDB data
            collection_name: Name of the collection to use
        """
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self._client: Optional[ClientAPI] = None
        self._collection: Optional[Collection] = None

        logger.info(
            f"Vector store manager initialized: dir={self.persist_dir}, "
            f"collection={self.collection_name}"
        )

    @property
    def client(self) -> ClientAPI:
        """
        Get or create ChromaDB client.

        Returns:
            ChromaDB client instance
        """
        if self._client is None:
            try:
                self._client = chromadb.PersistentClient(path=self.persist_dir)
                logger.info(f"ChromaDB client connected: {self.persist_dir}")
            except Exception as e:
                logger.error(f"Failed to create ChromaDB client: {e}", exc_info=True)
                raise
        return self._client

    @property
    def collection(self) -> Collection:
        """
        Get or create the FAQ collection.

        Returns:
            ChromaDB collection
        """
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=self.collection_name
                )
                logger.info(f"Collection loaded: {self.collection_name}")
            except Exception as e:
                logger.error(f"Failed to get collection: {e}", exc_info=True)
                raise
        return self._collection

    @trace_function(
        name="vector_store_query",
        attributes={"db.system": "chromadb", "db.operation": "query"},
    )
    def query(
        self,
        query_text: str,
        n_results: int = None,
        include_metadata: bool = True,
        include_documents: bool = True,
        include_distances: bool = True,
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.

        Args:
            query_text: Text to query for
            n_results: Number of results to return
            include_metadata: Include metadata in results
            include_documents: Include documents in results
            include_distances: Include distances in results

        Returns:
            Query results with documents, metadata, and distances
        """
        n_results = n_results or settings.FAQ_RETRIEVAL_TOP_K

        logger.info(f"🔍 Querying vector store: '{query_text}' (top {n_results})")
        start_time = time.time()

        try:
            # Build include list
            include = []
            if include_metadata:
                include.append("metadatas")
            if include_documents:
                include.append("documents")
            if include_distances:
                include.append("distances")

            # Query the collection
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=include,
            )

            duration = time.time() - start_time
            metrics.vector_store_query_duration_seconds.labels(
                collection=self.collection_name
            ).observe(duration)
            metrics.vector_store_queries_total.labels(
                collection=self.collection_name, status="success"
            ).inc()

            num_results = len(results.get("ids", [[]])[0]) if results.get("ids") else 0
            logger.info(f"✅ Found {num_results} results in {duration:.3f}s")

            return results

        except Exception as e:
            logger.error(f"Vector store query failed: {e}", exc_info=True)
            metrics.vector_store_queries_total.labels(
                collection=self.collection_name, status="error"
            ).inc()
            raise

    def format_faq_context(self, results: Dict[str, Any]) -> str:
        """
        Format query results into a readable FAQ context string.

        Args:
            results: Query results from ChromaDB

        Returns:
            Formatted FAQ context string
        """
        faq_context = ""

        if not results or not results.get("metadatas"):
            return "No relevant FAQs were found."

        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, meta in enumerate(metadatas):
            q = meta.get("question", "")
            a = meta.get("answer", "")
            score = distances[i] if i < len(distances) else 0.0

            faq_context += f"FAQ {i+1} (relevance score: {score:.3f})\n"
            faq_context += f"Q: {q}\n"
            faq_context += f"A: {a}\n\n"

        return faq_context

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """
        Add documents to the collection.

        Args:
            documents: List of document texts
            metadatas: List of metadata dicts
            ids: List of document IDs
        """
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info(f"✅ Added {len(documents)} documents to collection")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}", exc_info=True)
            raise

    def get_collection_count(self) -> int:
        """
        Get the number of documents in the collection.

        Returns:
            Number of documents
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}", exc_info=True)
            return 0


# Global vector store manager instance
_vector_store: Optional[VectorStoreManager] = None


def get_vector_store() -> VectorStoreManager:
    """
    Get the global vector store manager instance.

    Returns:
        VectorStoreManager instance
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreManager()
    return _vector_store
