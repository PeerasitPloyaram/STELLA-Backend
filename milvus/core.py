from pymilvus import connections, Collection, utility, db, MilvusClient
from langchain_core.documents import Document
from langchain_milvus import Milvus
# from pymilvus import WeightedRanker
# from pymilvus.model.sparse.bm25.tokenizers import build_default_analyzer
# from pymilvus.model.sparse import BM25EmbeddingFunction

from schema import DATA_SOURCE_SCHEMA, FRONTEND_QUERY_SOURCE_SCHEMA, INDEX_PARAMS, FRONTEND_QUERY_PARAMS

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.service import insertCompanyData, insertGeneralData

class Core:
    def __init__(self,
                schema,
                database_name:str,
                dense_embedding_model,
                token: str,
                verbose:bool=False,
                create_first_node: bool=True,
                system_prune_first_node: bool=False
                )-> None:
        """
        Mivus Database Core
        implements by Peerasit PLOYARAM

        args:
        """

        print("[CORE] Initializing Milvus Database Core...")
        self.database_name = database_name
        self.token = token
        self.collection_pointer = None
        self.data_source_schema = schema

        # Embedding Model
        print("[DB] init Embedding Model...")
        self.dense_embedding_model = dense_embedding_model
        print("[DB] init Embedding Model Successfully.")

        self.initDataBase()
        if create_first_node:
            self.createCollection("cnode_1", system_prune=system_prune_first_node)
            self.createCollection("gnode_1", system_prune=system_prune_first_node)
            self.createFrontEndQueryCollection(system_prune=system_prune_first_node)
        
    
    def initDataBase(self):
        """
        Initialize the Milvus Database

        args:
        system_prune: bool = False -> Drop the collection if it exists.
        verbose: bool = False -> Print the status of the database.
        """

        try:
            connections.connect(host="localhost", port="19530", token=self.token)
        except Exception as e:
            print(f"[DB] Connection Error: {e}")
            return
        
        # list_db = db.list_database():
        if self.database_name in db.list_database():
            print(f'[DB] Found Database: {self.database_name}')
            connections.connect(host="localhost", port="19530", db_name=self.database_name, token=self.token)
        else:
            print(f'[DB] Create Database: {self.database_name}')
            db.create_database(self.database_name)
            connections.connect(host="localhost", port="19530", db_name=self.database_name, token=self.token)

    def createCollection(self, collection_name: str,system_prune: bool = False):
        if utility.has_collection(collection_name=collection_name):
            print(f'[DB] Found Collection "{collection_name}".')
            
            if system_prune:
                print(f'[DB] Drop Collection "{collection_name}"...')
                cl = Collection(name=collection_name)
                print(f"{collection_name} has: {cl.num_entities} entities")
                cl.drop()
                print(f'[DB] Drop Collection "{collection_name}" Successfully.')

            else:
                print(f'[DB] GET Collection Successfully.')
                self.collection = Collection(name=collection_name)
                return
        
        print(f'[DB] Create Collection "{collection_name}"')
        collection = Collection(name=collection_name,
                                schema=self.data_source_schema,
                                consistency_level="Strong",
                                num_shards=4,
                                )
        collection.create_index("dense_vector", INDEX_PARAMS)
        # self.collection.create_index("sparse_vector", SPARSE_INDEX_PARAMS)
        collection.flush()
        print(f'[DB] Collection "{collection_name}" Is Ready.')
        return collection

    def dropCollection(self, collection_name: str):
        utility.drop_collection(collection_name)
    
    # Set Pointer to Collection
    def setCollectionPointer(self, collection_name):
        if type(collection_name) == Collection:
            # print("From Collection")
            self.collection_pointer = collection_name
        else:
            # print("From String")
            self.collection_pointer = Collection(name=collection_name)

    def getCollectionPointer(self) -> Collection:
        return self.collection_pointer
    
    def listCollection(self):
        return utility.list_collections()


    def listPartition(self, collection_name):
        return MilvusClient(db_name=self.database_name, token=self.token).list_partitions(collection_name)
    def findPartition(self, collection:Collection, partitinon_name:str):
        return collection.has_partition(partitinon_name)

    # def createPartition(self,collection: Collection, partition_name, description=""):
    #     if not collection.has_partition(partition_name):
    #         print("[DB] Create New Partition")
    #         cl = collection.create_partition(partition_name=partition_name,
    #                                             description=description)
    #         # cl.flush()

    # def drop(self, collection: Collection, partition_name: str):
    #     collection.drop_partition(partition_name)


    def getNumEntities(self):
        return self.collection_pointer.num_entities
    
    def describe(self):
        return self.collection_pointer.describe()


    # def initVectorStore(self, collection_name, partition_names:list, host:str="localhost", port:str="19530"):
    def initVectorStore(self, collection_name, partition_names:list, search_kwargs):
        client = Milvus(
        embedding_function=self.dense_embedding_model,
        partition_names=partition_names,
        collection_name=collection_name,
        connection_args={
            "host": "localhost",
            "port": 19530,
            "user": "root",
            "password": "Milvus",
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

        # {
        #     "k": 8,
        #     "partition_names": ["bts", "scb"],
        #     "expr": '(metadata["year"] == "2023" && metadata["company_name"] == "SCB") || (metadata["year"] == "2023" && metadata["company_name"] == "BTS")'
        # }
        client._load(partition_names=partition_names)

        retreiver = client.as_retriever(search_kwargs=search_kwargs)
        return retreiver


    def findCollectionGNode(self):
        client = MilvusClient(db_name=self.database_name, token=self.token)
        collections = client.list_collections()
        cnode_items = [item for item in collections if item.startswith("gnode_")]
        cnode_items.sort()
        if cnode_items == []:
            return []
        return cnode_items

    # Find Collection Node
    def findCollectionCNode(self):
        client = MilvusClient(db_name=self.database_name, token=self.token)
        collections = client.list_collections()
        cnode_items = [item for item in collections if item.startswith("cnode_")]
        cnode_items.sort()
        if cnode_items == []:
            return []
        return cnode_items


    # Create Collection Node
    def createCnodeCollection(self)-> str:
        current_node = self.findCollectionCNode()
        current_node = current_node[-1]

        try:
            if current_node == []:
                collection_name = f"cnode_{1}"
            else:
                if isinstance(id := int(current_node.split("_")[1]), int):
                    collection_name = f"cnode_{id + 1}"
                    print("Create", collection_name)

            collection = Collection(name=collection_name,
                                    schema=self.data_source_schema,
                                    consistency_level="Strong",
                                    num_shards=4,
                                    )
            collection.create_index("dense_vector", INDEX_PARAMS)
            # self.collection.create_index("sparse_vector", SPARSE_INDEX_PARAMS)
            collection.flush()
            print(f'[DB] Collection "{collection_name}" Is Ready.')
            return collection_name
        except:
            pass

    def createGnodeCollection(self)-> str:
        current_node = self.findCollectionGNode()
        current_node = current_node[-1]

        try:
            if current_node == []:
                collection_name = f"gnode_{1}"
            else:
                if isinstance(id := int(current_node.split("_")[1]), int):
                    collection_name = f"gnode_{id + 1}"
                    print("Create", collection_name)

            collection = Collection(name=collection_name,
                                    schema=self.data_source_schema,
                                    consistency_level="Strong",
                                    num_shards=4,
                                    )
            collection.create_index("dense_vector", INDEX_PARAMS)
            # self.collection.create_index("sparse_vector", SPARSE_INDEX_PARAMS)
            collection.flush()
            print(f'[DB] Collection "{collection_name}" Is Ready.')
            return collection_name
        except:
            pass


    def createFrontEndQueryCollection(self, system_prune: bool = False):
        collection_name = "frontend_query_general_documents"
        if utility.has_collection(collection_name=collection_name):
            print(f'[DB] Found Collection "{collection_name}".')
            
            if system_prune:
                print(f'[DB] Drop Collection "{collection_name}"...')
                cl = Collection(name=collection_name)
                print(f"{collection_name} has: {cl.num_entities} entities")
                cl.drop()
                print(f'[DB] Drop Collection "{collection_name}" Successfully.')

            else:
                print(f'[DB] GET Collection Successfully.')
                self.collection = Collection(name=collection_name)
                return
            
        print(f'[DB] Create Collection "{collection_name}"')
        collection = Collection(name=collection_name,
                                schema=FRONTEND_QUERY_SOURCE_SCHEMA,
                                consistency_level="Strong",
                                num_shards=4,
                                )
        collection.create_index("dense_vector", FRONTEND_QUERY_PARAMS)
        collection.flush()
        print(f'[DB] Collection "{collection_name}" Is Ready.')
        return collection


    def addFrontEndQueryData(self, front_end_query: list[dict[str:str]]):
        """Add name partition and description for simirality search frontend query general datas.
        Format {"name": "name_of_partition", description: "description of general file"}
        """

        documents = front_end_query
        entities = []
        for doc in documents:
            entities.append({
                "name": doc["name"],
                "description": doc["description"],
                "dense_vector": self.dense_embedding_model.embed_query(doc["description"]),
                # "sparse_vector": sparse_vector
            })

        cl = Collection(name="frontend_query_general_documents")
        cl.insert(entities)
        cl.flush()
        print("[DB] Insert Query FrontEnd Successfuly.")



    def search_general_documents(self, query:str, top_k:int=3, ratio:float=0.785):
        """Search the most relevant general documents for a given query."""

        cl = Collection(name="frontend_query_general_documents")
        cl.load()
        
        query_embedding = self.dense_embedding_model.embed_query(query)
        results = cl.search(
            data=[query_embedding],
            anns_field="dense_vector",
            param=FRONTEND_QUERY_PARAMS,
            limit=top_k,
            output_fields=["name", "description"]
        )

        partition_loc = []
        for entities in results:
            for entity in entities:
                print(entity)
                if float(entity.distance) >= ratio:
                    partition_loc.append(entity.get("name"))
        return partition_loc

    # def search_general_documents_hybrid(self, input):
    #     from pymilvus import WeightedRanker

    #     rerank= WeightedRanker(0.3, 0.8) 
    #     # from pymilvus import RRFRanker

    #     # rerank = RRFRanker(100)
    #     from pymilvus import AnnSearchRequest
    #     search_param_1 = {
    #         "data": [self.dense_embedding_model.embed_query(input)],
    #         "anns_field": "dense_vector",
    #         "param": {
    #             "metric_type": "IP",
    #             "params": {"nprobe": 10}
    #         },
    #         "limit": 2
    #     }
    #     request_1 = AnnSearchRequest(**search_param_1)

    #     b = BM25EmbeddingFunction()
    #     search_param_2 = {
    #         "data": b.encode_documents([input]),
    #         "anns_field": "sparse_vector",
    #         "param": {
    #             "metric_type": "IP",
    #             "params": {}
    #         },
    #         "limit": 2
    #     }
    #     request_2 = AnnSearchRequest(**search_param_2)


    #     reqs = [request_1, request_2]
    #     client = MilvusClient(db_name=self.database_name, token=self.token)
    #     client.load_collection("frontend_query_general_documents")
    #     res = client.hybrid_search(
    #         collection_name="frontend_query_general_documents",
    #         reqs=reqs,
    #         ranker=rerank
    #     )
    #     for hits in res:
    #         print("TopK results:")
    #         for hit in hits:
    #             print(hit)


    # Isolate
    def add_document(self, name: str, documents: list[Document], node_type:str, description:str | None=None, sector_id: int | None=None):
        limit_size = 2

        if node_type == "c":
            nodes = self.findCollectionCNode()
        else:
            nodes = self.findCollectionGNode()
        found_at = ""
        found_partition = False

        for node in nodes:
            if self.findPartition(Collection(name=node), name):
                found_partition = True
                found_at = node
                break

        chunks = []
        for doc in documents:
            buffer = {
                "dense_vector": self.dense_embedding_model.embed_query(doc.page_content),
                # "sparse_vector": BM25SparseEmbedding(corpus=[""]).embed_query(doc.page_content),
                "text": doc.page_content,
                "metadata": doc.metadata
            }
            chunks.append(buffer)
        
        if found_partition:
            self.setCollectionPointer(found_at)
            current_node = self.getCollectionPointer()

            print("[DB Found Partition")
            s = current_node.partition(name)
            print(f"[DB] Partition {name}: {s.num_entities} entities")
            s.load()
            s.insert(data=chunks)
            s.flush()
            print(f"[DB] Partition {name}: {s.num_entities} entities")
        else:
            flag = False
            for node in nodes:
                if len(self.listPartition(node)) - 1 < limit_size:
                    flag = False
                    self.setCollectionPointer(node)
                    break
                else:
                    flag = True
            if flag:
                if node_type == "c":
                    new_node = self.createCnodeCollection()
                else:
                    new_node = self.createGnodeCollection()

                self.setCollectionPointer(new_node)

            current_node = self.getCollectionPointer()
            print(current_node)
            print(type(current_node))
            current_node.create_partition(partition_name=name, description="")

            if node_type == "c":
                if sector_id == None:
                    print("[DB] ERROR: You Must Pass Sector")
                    return "You must pass sector"
                insertCompanyData(sector_id=sector_id, abbr=name, collection_name=current_node.name, partition_name=name)
            else:
                if description != None:
                    frontend_context = [{"name": name, "description": description}]
                else:
                    return "You must pass description if node type g"
                insertGeneralData(document_name=name, collection_name=current_node.name, partition_name=name)
                self.addFrontEndQueryData(front_end_query=frontend_context)

            print("[DB] Create New Partition")
            partition = current_node.partition(name)
            partition.load()
            partition.insert(data=chunks)
            partition.flush()
            print(f"[DB] Partition {name}: {partition.num_entities} entities")



if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from langchain_huggingface import HuggingFaceEmbeddings

    load_dotenv()
    core = Core(
                database_name="new_core",
                schema=DATA_SOURCE_SCHEMA,
                dense_embedding_model=HuggingFaceEmbeddings(model_name=os.getenv("DENSE_EMBEDDING_MODEL")),
                create_first_node=False,
                system_prune_first_node=False,
                token=os.getenv('TOKEN'),
            )
    print("====")
    for collection in core.listCollection():
        print(f"Collection {collection}:")
        for p in core.listPartition(collection):
            c = Collection(name=collection).partition(p).num_entities
            print("Partition in", collection, ":", p, "has", c, "entities")
    print("===")