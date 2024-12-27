from pymilvus import connections, Collection, utility, db
from langchain_core.documents import Document
from langchain_milvus import Milvus
from schema import DATA_SOURCE_SCHEMA, INDEX_PARAMS

import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s]  %(message)s")
logger = logging.getLogger("milvus_logger")

class Core:
    def __init__(self,
                schema,
                database_name:str,
                dense_embedding_model, 
                collection_name:str,
                system_prune:bool=False,
                verbose:bool=False
                )-> None:
        """
        Mivus Database Core
        implements by Peerasit PLOYARAM

        args:
        shcema: CollectionSchema -> The schema of the collection.
        dense_embedding_model: HuggingFaceEmbeddings -> The embedding model for dense vector.
        collection_name: str -> The name of the collection.
        system_prune: bool = False -> Drop the collection if it exists.
        verbose: bool = False -> Print the status of the database.
        """
        logger.info("[CORE] Initializing Milvus Database Core...")
        self.database_name = database_name
        self.data_source_collection = collection_name
        self.data_source_schema = schema

        # Embedding Model
        logger.info("[DB] init Embedding Model...")
        self.dense_embedding_model = dense_embedding_model
        logger.info("[DB] init Embedding Model Successfully.")
        self.sparse_embedding_model = ""

        self.initDataBase(system_prune=system_prune)
        
    
    def initDataBase(self, system_prune: bool = False):
        """
        Initialize the Milvus Database

        args:
        system_prune: bool = False -> Drop the collection if it exists.
        verbose: bool = False -> Print the status of the database.
        """

        try:
            connections.connect(host="localhost", port="19530")
        except Exception as e:
            logger.error(f"[DB] Connection Error: {e}")
            return
        
        if self.database_name in db.list_database():
            logger.info(f'[DB] Found Database: {self.database_name}')
            connections.connect(host="localhost", port="19530", db_name=self.database_name)
        else:
            logger.info(f'[DB] Create Database "{self.database_name}"')
            db.create_database(self.database_name)
            connections.connect(host="localhost", port="19530", db_name=self.database_name)
        
        if utility.has_collection(self.data_source_collection):
            logger.info(f'[DB] Found Collection "{self.data_source_collection}".')
            
            if system_prune:
                logger.info(f'[DB] Drop Collection "{self.data_source_collection}"...')
                utility.drop_collection(self.data_source_collection)
                logger.info(f'[DB] Drop Collection "{self.data_source_collection}" Successfully.')
            else:
                self.collection = Collection(name=self.data_source_collection)
                return
        
        logger.info(f'[DB] Create Collection "{self.data_source_collection}"')
        self.collection = Collection(
                                name=self.data_source_collection,
                                schema=self.data_source_schema,
                                consistency_level="Strong"
                                )
        self.collection.create_index("dense_vector", INDEX_PARAMS)
        self.collection.flush()

        logger.info(f'[DB] Collection "{self.data_source_collection}" Is Ready.\n==========================================================================')

    def initVectorStore(self, host:str="localhost", port:str="19530"):
        self.vector_store = Milvus(
            embedding_function=self.dense_embedding_model,
            collection_name=self.data_source_collection,
            connection_args={
                "host": host,
                "port": port
            },
            primary_field="id",
            vector_field="dense_vector",
            text_field="text",
            metadata_field="metadata",
            enable_dynamic_field=False,
            auto_id=True,
        )
        return self.vector_store
    
    def vectorStoreAddDocument(self, documents: list[Document]):
        self.vector_store.add_documents(documents=documents)


    def thread_add_document(self ,embedding_model, documents: list[Document], batch_size=10):
        from concurrent.futures import ThreadPoolExecutor
        """
        """
        def prepare_data(document):
            vector = embedding_model.embed_query(document.page_content)
            return {
                "text": document.page_content,
                "vector": vector,
                "tester": "test"
            }
        
        with ThreadPoolExecutor() as executor:
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                # Generate embeddings in parallel
                prepared_data = list(executor.map(prepare_data, batch))
                
                # MilvusClient().insert(self.data_source_collection, prepared_data)
                self.collection.insert(prepared_data)
                print(f"Inserted batch of {len(prepared_data)} documents into Milvus collection.")
                self.collection.flush()
                # MilvusClient().flush([self.data_source_collection])

    def add_document(self, embedding_model, documents: list[Document]):
        """
        """
        for document in documents:
            vector = embedding_model.embed_query(document.page_content)
            datas = {
                "text": document.page_content,
                "vector": vector,
                "source": "test"
            }

            self.collection.insert(data=[datas])
        self.collection.flush()



if __name__ == "__main__":
    from langchain_huggingface import HuggingFaceEmbeddings

    core = Core(collection_name="data_source",
                database_name="stella_db",
                schema=DATA_SOURCE_SCHEMA,
                dense_embedding_model=HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large"),
                system_prune=True
            )
    print(db.list_database())
    print(utility.list_collections())