import os, sys
from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()

client = MilvusClient(db_name=os.getenv("MILVUS_DATABASE_NAME"))

def getInfo():
    data = {}
    collections = client.list_collections()

    for collection in collections:
        partitions = client.list_partitions(collection)
        partition_data = {}
        
        for partition in partitions:
            entity_stat = client.get_partition_stats(collection_name=collection, partition_name=partition)
            partition_data[partition] = entity_stat["row_count"]
        
        data[collection] = {"partition": partition_data}
    
    return data


if __name__ == "__main__":
    print(getInfo())