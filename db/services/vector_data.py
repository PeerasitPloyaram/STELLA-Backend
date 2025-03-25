import os, sys
from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()

def getConnection():
    return MilvusClient(db_name=os.getenv("MILVUS_DATABASE_NAME"))

def getInfo():
    data = {}
    client = getConnection()
    collections = client.list_collections()

    for collection in collections:
        partitions = client.list_partitions(collection)
        partition_data = {}
        
        for partition in partitions:
            entity_stat = client.get_partition_stats(collection_name=collection, partition_name=partition)
            partition_data[partition] = entity_stat["row_count"]
        
        data[collection] = {"partition": partition_data}
    
    return data

def updateVectorFrontendNodeGeneral(file_name:str, new_description:str):
    base_collection:str = "frontend_query_gnode"
    client = getConnection()
    client.load_collection(collection_name=base_collection)
    pulling = client.query(collection_name=base_collection,
                    output_fields=["id", "name", "description", "dense_vector"],
                    filter=f"name == '{file_name}'"
                    )
    if not pulling:
        raise "Not Found"
    current_data = pulling[0]
    # print(current_data["description"], current_data["name"])
    current_data["description"] = new_description

    # print(current_data["description"], current_data["name"])

    client.upsert(collection_name=base_collection, data=current_data)


def deleteVectorFrontendNodeGeneral(file_name:str):
    base_collection:str = "frontend_query_gnode"
    client = getConnection()
    client.load_collection(collection_name=base_collection)
    client.delete(collection_name=base_collection, 
                filter=f"name == '{file_name}'")
    client.flush(collection_name=base_collection)


def deleteVectorGeneral(collection:str, partition:str):
    client = getConnection()
    client.release_partitions(collection_name=collection, partition_names=partition)
    client.drop_partition(collection_name=collection, partition_name=partition)


def deleteVectorCompany(collection:str, partition:str):
    client = getConnection()
    client.release_partitions(collection_name=collection, partition_names=partition)
    client.drop_partition(collection_name=collection, partition_name=partition)


def deleteVectorEachCompanyFile(collection:str, partition:str, file_name:str):
    client = getConnection()
    client.delete(
        collection_name=collection,
        partition_name=partition,
        filter=f"metadata['file_name'] == '{file_name}'"
    )

def countEntity(collection:str, partition:str):
    client = getConnection()
    count = client.get_partition_stats(collection_name=collection, partition_name=partition)
    return count["row_count"]

if __name__ == "__main__":
    pass
    # (deleteVectorFrontendNodeGeneral("b"))
    # deleteVectorCompany(collection="gnode_1", partition="ndc")
    # deleteVectorEachCompanyFile(collection="cnode_1", partition="bts", file_name="bts_esg_2023.pdf")
    # print(client.query(collection_name="frontend_query_gnode", filter=f"name == 'ndc'", output_fields=["name", "description"]))