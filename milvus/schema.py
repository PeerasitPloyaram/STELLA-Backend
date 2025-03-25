from pymilvus import CollectionSchema, FieldSchema, DataType

id_field = FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True)        # Auto ID
vector_field = FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024)        # Vector Embedding dimension
# sparse_field = FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR)
text_field = FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192)                # Page Content
metadata_field = FieldSchema(name="metadata", dtype=DataType.JSON)                            # Additional metadata
# partition_key_field = FieldSchema(name="partition_key", dtype=DataType.VARCHAR, max_length=128, is_partition_key=True)


name_field = FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255)                 # FrontEnd General Documents Name
description_field = FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=4095)  # FrontEnd General Documents Description 


schema_fields = [id_field, vector_field, text_field, metadata_field]
DATA_SOURCE_SCHEMA = CollectionSchema(
    fields=schema_fields,
    description="Schema for Data Source Collection",
    enable_dynamic_field=True
)

INDEX_PARAMS = {
    "index_type": "IVF_PQ",
    "params": {
        "nlist": 128,
        "m": 4
    },
    "metric_type": "IP"
}


general_documents_fileds = [id_field, name_field, description_field, vector_field,
    # sparse_field
    ]

FRONTEND_QUERY_SOURCE_SCHEMA = CollectionSchema(
    fields=general_documents_fileds,
    description="Schema for Fronted Query General Documents",
    enable_dynamic_field=True
)

# FRONTEND_QUERY_PARAMS = {
#     "metric_type": "COSINE",
#     "index_type": "HNSW",
#     "params": {"M": 16, "efConstruction": 200}
# }
FRONTEND_QUERY_PARAMS = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 8, "efConstruction": 100,"efSearch": 100}
}