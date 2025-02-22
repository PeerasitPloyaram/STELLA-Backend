import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/milvus")

from milvus.core import Core
from milvus.schema import DATA_SOURCE_SCHEMA, FRONTEND_QUERY_SOURCE_SCHEMA, INDEX_PARAMS, FRONTEND_QUERY_PARAMS
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, UploadFile

from pydantic import BaseModel
import asyncio

import os, sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chunking.ndc_file import ndcFileChunking
from chunking.one_report_file import oneReportFileChunking
from io import BytesIO

load_dotenv()

core = Core(
            database_name="new_core",
            schema=DATA_SOURCE_SCHEMA,
            dense_embedding_model=HuggingFaceEmbeddings(model_name=os.getenv("DENSE_EMBEDDING_MODEL")),
            create_first_node=False,
            system_prune_first_node=False,
            token=os.getenv('TOKEN'),
        )



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections = {}

class DataModel(BaseModel):
    data: str

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    active_connections[user_id] = websocket

    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received message from {user_id}: {message}")

    except WebSocketDisconnect:
        del active_connections[user_id]
        print(f"User {user_id} disconnected")

import time



def long_running_task():
    time.sleep(5)  # Simulate
    return "Computation completed"
async def run_long_task():
    result = await asyncio.to_thread(long_running_task)
    return result
async def test(user_id):
    result = await run_long_task()
    await active_connections[user_id].send_text(f"Computation completed: {result}")

@app.post("/send_data/{user_id}")
async def send_data(user_id: str, payload: DataModel):
    if user_id not in active_connections:
        raise HTTPException(status_code=400, detail="User not connected")
    asyncio.create_task(test(user_id))
    result = f"Processed data: {payload.data}"
    return {"message": "Data sent successfully", "result": result}





def chunkingTask(e, f):
    chunks = ndcFileChunking(content=e, file_name=f)
    core.add_document(name="ndc", documents=chunks, node_type="g", description="National disclosure standards for financial climate, climate risk, NFCCC")
    return "Computation completed"

async def createAsyncTask(raw, file):
    result = await asyncio.to_thread(chunkingTask, raw, file)
    return result

async def load(raw, f, user_id):
    result = await createAsyncTask(raw, f.filename)
    await active_connections[user_id].send_text(f"Computation completed: {f.filename}")

@app.post("/uploadfile/{user_id}")
async def upload_file(user_id:str, file: UploadFile = File(...),):
    content = await file.read()
    raw_content = BytesIO(content)

    if user_id in active_connections:
        await active_connections[user_id].send_text(f"Upload started: {file.filename}")

    asyncio.create_task(load(raw_content, file, user_id))

    return {"status": True}




from stella.services.service import testLLM
from fastapi.responses import StreamingResponse

async def generateChatStream(chunks, message):
    rag = testLLM()
    print(chunks)
    async for chunks in rag.astream({"context": chunks, "question": message}):
        if isinstance(chunks, str):
            yield chunks

@app.post("/chat/{user_id}")
async def chat(user_id:str, payload: DataModel):
    chunks = core.stlRetreiver(user_query_input=payload.data)
    return StreamingResponse(generateChatStream(chunks=chunks, message=payload.data), media_type="text/event-stream")