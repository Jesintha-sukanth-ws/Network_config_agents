"""
chroma_manager.py

Manages persistent vector collections
for RAG retrieval.

Responsibilities:

- Initialize ChromaDB
- Create collections
- Store vectors
- Resolve collections
- Semantic retrieval
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

import chromadb
from chromadb.config import Settings

from app.rag.config import (

    CHROMA_PERSIST_DIR,

    CHROMA_COLLECTIONS,

    RETRIEVAL_TOP_K
)


logger = logging.getLogger(__name__)


class ChromaManager:


    def __init__(

        self,

        persist_dir: Optional[Path]=None

    ):


        self.persist_dir=(

            Path(

                persist_dir

                or

                CHROMA_PERSIST_DIR
            )
        )


        self.persist_dir.mkdir(

            parents=True,

            exist_ok=True
        )


        self.client=(

            chromadb.PersistentClient(

                path=str(
                    self.persist_dir
                ),

                settings=Settings(

                    anonymized_telemetry=False
                )
            )
        )


        self.collections:Dict[
            str,
            Any
        ]={}


        self._initialize()



    def _initialize(

        self

    )->None:

        """
        Initialize collections.
        """


        for name in CHROMA_COLLECTIONS:


            self.collections[name]=(

                self.client
                .get_or_create_collection(

                    name=name,

                    metadata={

                        "hnsw:space":

                        "cosine"
                    }
                )
            )


            logger.info(

                "Collection '%s' initialized "
                "(count=%d)",

                name,

                self.collections[
                    name
                ].count()
            )



    def resolve_collection(

        self,

        vendor:str,

        os_name:str,

        version:Optional[
            str
        ]=None

    )->str:


        """
        Dynamically resolve collection.

        Version intentionally ignored.

        Version belongs in
        chunk metadata filtering.
        """


        vendor=vendor.lower()

        os_name=os_name.lower()


        for (

            collection_name,

            metadata

        ) in (

            CHROMA_COLLECTIONS.items()
        ):


            if (

                metadata[
                    "vendor"
                ].lower()

                ==

                vendor

                and

                metadata[
                    "os"
                ].lower()

                ==

                os_name
            ):

                return (

                    collection_name
                )


        raise ValueError(

            f"No collection found "
            f"for "

            f"{vendor} "
            f"{os_name}"
        )



    def upsert_chunks(

        self,

        collection_name:str,

        ids:List[str],

        documents:List[str],

        embeddings:List[
            List[float]
        ],

        metadatas:List[
            Dict[str,Any]
        ]

    )->None:


        """
        Store chunks.

        Existing ids:
        update

        New ids:
        insert
        """


        if not (

            len(ids)

            ==

            len(documents)

            ==

            len(embeddings)

            ==

            len(metadatas)

        ):

            raise ValueError(

                "Input length mismatch"
            )


        collection=(

            self.collections.get(

                collection_name
            )
        )


        if collection is None:

            raise ValueError(

                f"Collection "

                f"{collection_name}"

                f" not found"
            )


        collection.upsert(

            ids=ids,

            documents=
            documents,

            embeddings=
            embeddings,

            metadatas=
            metadatas
        )


        logger.debug(

            "Stored %d chunks "
            "in %s",

            len(ids),

            collection_name
        )



    def clear_collection(
        self,
        collection_name: str
    ) -> None:
        """
        Clear all data from a collection while preserving the collection structure.
        """
        collection = self.collections.get(collection_name)
        
        if collection is None:
            raise ValueError(f"Collection {collection_name} not found")
        
        # Get all IDs in the collection
        if collection.count() > 0:
            # ChromaDB requires getting all IDs first, then deleting them
            all_data = collection.get()
            if all_data["ids"]:
                collection.delete(ids=all_data["ids"])
                logger.info(
                    "Cleared %d documents from collection '%s'",
                    len(all_data["ids"]),
                    collection_name
                )
        else:
            logger.info("Collection '%s' is already empty", collection_name)

    def query(

        self,

        collection_name:str,

        query_embeddings:
        List[List[float]],

        n_results:int=
        RETRIEVAL_TOP_K,

        where:
        Optional[
            Dict
        ]=None

    )->Dict:


        """
        Semantic retrieval
        with optional filtering.
        """


        collection=(

            self.collections.get(

                collection_name
            )
        )


        if collection is None:

            raise ValueError(

                f"Collection "

                f"{collection_name}"

                f" not found"
            )


        if collection.count()==0:


            logger.warning(

                "Query on empty "
                "collection %s",

                collection_name
            )


            return {

                "ids":[[]],

                "documents":[[]],

                "metadatas":[[]],

                "distances":[[]]
            }


        return (

            collection.query(

                query_embeddings=
                query_embeddings,

                n_results=
                n_results,

                where=
                where,

                include=[

                    "documents",

                    "metadatas",

                    "distances"
                ]
            )
        )