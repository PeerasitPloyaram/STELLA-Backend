import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/milvus")

from milvus.core import Core
from milvus.schema import DATA_SOURCE_SCHEMA, FRONTEND_QUERY_SOURCE_SCHEMA, INDEX_PARAMS, FRONTEND_QUERY_PARAMS
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile
from typing import Annotated

load_dotenv()
# core = Core(
#             database_name="new_core",
#             schema=DATA_SOURCE_SCHEMA,
#             dense_embedding_model=HuggingFaceEmbeddings(model_name=os.getenv("DENSE_EMBEDDING_MODEL")),
#             create_first_node=False,
#             system_prune_first_node=False,
#             token=os.getenv('TOKEN'),
#         )


app = FastAPI()    
# Creating a Streamer queue  
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from chunking.ndc_file import ndcFileChunking
from chunking.one_report_file import oneReportFileChunking
@app.post("/uploadfile/")
async def upload_file(file: UploadFile):

    # print(ndcFileChunking("/Users/peerasit/senior_project/STELLA-Backend/chunking/pdfs/general/Thailand_INDCs_2015.pdf"))
    print(oneReportFileChunking("/Users/peerasit/senior_project/STELLA-Backend/chunking/pdfs/aav_56-1_2023.pdf"))
    # with open(file_path, "wb") as buffer:
        # shutil.copyfileobj(file.file, buffer)
    
    return {"status": True}

# @app.get("/query/{query_input}")
# def read_root(query_input):
#     # return query_input
#     # return {"Hello": "World"}
#     import timeit
#     from extraction.query_extractor import query_extractorV2
#     start = timeit.default_timer()

#     name = query_extractorV2(user_query=query_input)
#     a =  core.search_general_documents(query=query_input)


#     stop = timeit.default_timer()
#     # print('Time: ', stop - start)
#     return {"name":name, "general": a, "run_time": stop - start} 

# from extraction.query_extractor import query_extractorV2
# name = query_extractorV2(user_query="btsและtrueมีclimateriskหรือไม่")
# print(name)