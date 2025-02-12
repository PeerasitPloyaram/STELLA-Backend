from pymilvus import CollectionSchema, FieldSchema, DataType

id_field = FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True)  # Auto ID
vector_field = FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024)  # Vector Embedding dimension
# sparse_field = FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR)
text_field = FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192)  # Page Content
metadata_field = FieldSchema(name="metadata", dtype=DataType.JSON)  # Additional metadata

schema_fields = [id_field, vector_field, text_field, metadata_field]
DATA_SOURCE_SCHEMA = CollectionSchema(
    fields=schema_fields,
    description="Schema for Data Source Collection",
    enable_dynamic_field=True
)

# INDEX_PARAMS = {
#     "index_type": "IVF_FLAT",
#     "params": {
#         "nlist": 128
#     },
#     "metric_type": "L2"
# }

INDEX_PARAMS = {
    "index_type": "IVF_PQ",
    "params": {
        "nlist": 128,
        "m": 4
    },
    "metric_type": "L2"
}

# DENSE_INDEX_PARAMS = {
#     "index_type": "IVF_PQ",
#     "params": {
#         "nlist": 128,
#         "m": 4
#     },
#     "metric_type": "IP"
# }

# SPARSE_INDEX_PARAMS = {
#     "index_type": "SPARSE_INVERTED_INDEX",
#     "params": {
#         "inverted_index_algo": "DAAT_MAXSCORE"
#     },
#     "metric_type": "IP"
# }