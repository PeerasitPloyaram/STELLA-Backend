from pymilvus import connections, Collection, utility, db
from langchain_core.documents import Document
from langchain_milvus import Milvus
from schema import DATA_SOURCE_SCHEMA, INDEX_PARAMS

# import logging
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s]  %(message)s")
# logger = logging.getLogger("milvus_logger")

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
        # logger.info("[CORE] Initializing Milvus Database Core...")
        print("[CORE] Initializing Milvus Database Core...")
        self.database_name = database_name
        self.data_source_collection = collection_name
        self.data_source_schema = schema

        # Embedding Model
        # logger.info("[DB] init Embedding Model...")
        print("[DB] init Embedding Model...")
        self.dense_embedding_model = dense_embedding_model
        # logger.info("[DB] init Embedding Model Successfully.")
        print("[DB] init Embedding Model Successfully.")
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
            # logger.error(f"[DB] Connection Error: {e}")
            print(f"[DB] Connection Error: {e}")
            return
        
        # list_db = db.list_database():
        if self.database_name in db.list_database():
            # logger.info(f'[DB] Found Database: {self.database_name}')
            print("f'[DB] Found Database: {self.database_name}'")
            connections.connect(host="localhost", port="19530", db_name=self.database_name)
        else:
            # logger.info(f'[DB] Create Database: {self.database_name}')
            print(f'[DB] Create Database: {self.database_name}')
            db.create_database(self.database_name)
            connections.connect(host="localhost", port="19530", db_name=self.database_name)
        
        if utility.has_collection(self.data_source_collection):
            # logger.info(f'[DB] Found Collection "{self.data_source_collection}".')
            print(f'[DB] Found Collection "{self.data_source_collection}".')
            
            if system_prune:
                # logger.info(f'[DB] Drop Collection "{self.data_source_collection}"...')
                print(f'[DB] Drop Collection "{self.data_source_collection}"...')
                # utility.drop_collection(self.data_source_collection)
                cl = Collection(name=self.data_source_collection)
                print(f"{self.data_source_collection} has: {cl.num_entities} entities")
                cl.drop()
                # logger.info(f'[DB] Drop Collection "{self.data_source_collection}" Successfully.')
                print(f'[DB] Drop Collection "{self.data_source_collection}" Successfully.')
            else:
                self.collection = Collection(name=self.data_source_collection)
                return
        
        # logger.info(f'[DB] Create Collection "{self.data_source_collection}"')
        print(f'[DB] Create Collection "{self.data_source_collection}"')
        self.collection = Collection(
                                name=self.data_source_collection,
                                schema=self.data_source_schema,
                                consistency_level="Strong"
                                )
        self.collection.create_index("dense_vector", INDEX_PARAMS)
        self.collection.flush()

        # logger.info(f'[DB] Collection "{self.data_source_collection}" Is Ready.\n==========================================================================')
        print(f'[DB] Collection "{self.data_source_collection}" Is Ready.\n==========================================================================')

    def getNumEntities(self):
        return self.collection.num_entities

    def initVectorStore(self, host:str="localhost", port:str="19530"):
        self.vector_store = Milvus(
            embedding_function=self.dense_embedding_model,
            collection_name=self.data_source_collection,
            connection_args={
                "host": host,
                "port": port,
                "db_name": self.database_name
            },
            index_params=INDEX_PARAMS,
            primary_field="id",
            vector_field="dense_vector",
            text_field="text",
            metadata_field="metadata",
            enable_dynamic_field=False,
            auto_id=True,
        )
        return self.vector_store
    
    def add_document(self, documents: list[Document]):
        chunks = []
        for doc in documents:
            buffer = {
                "dense_vector": self.dense_embedding_model.embed_query(doc.page_content),
                "text": doc.page_content,
                "metadata": doc.metadata
            }
            chunks.append(buffer)

        self.collection.load()
        print(self.collection.insert(data=chunks))
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