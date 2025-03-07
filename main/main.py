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
from fastapi import File, Form, UploadFile, Response, status

from pydantic import BaseModel
import asyncio

import os, sys
from io import BytesIO

from db.services.user import createUser, findUser, checkPassword, getUserId, auth
from db.services.vector_data import getInfo
from db.services.service import (
    getAllCompaniesInfo, getAllSector,
    findCompanies, createNewCompany,
    getAllGeneralFile, findDocument, findCompany,
    updateDescriptionGeneralData,
    deleteGeneralFile, deleteCompanyData, findSQLComapnyDataFile,
    getCompanyId, getALLSQLCompanyDataFile, deleteEachCompanyFileData
)

from stella.services.srag import app as ai
from stella.services.srag import oneReportTask, esgReportTask, ndcTask

load_dotenv()

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
    session: str

class UserDataModel(BaseModel):
    username: str
    password: str

class AuthDataModel(BaseModel):
    id:str

class AddCompanyDataModel(BaseModel):
    abbr:str
    name_th:str
    name_en:str
    sector_id:int

class updateDescriptionGeneralDataModel(BaseModel):
    name:str
    description:str

class deleteDataModel(BaseModel):
    name:str

class deleteCompanyEashDataModel(BaseModel):
    file_name:str
    abbr:str


async def generateChatStream(session_id:str, message):
    text_speed = 30
    async for chunks in ai.astream({"question": message, "session_id": session_id}):
        for key, value in chunks.items():
            if "generation" in value:
                text = value["generation"]
                # yield text
                for i in range(0, len(text), text_speed):
                    chunk = text[i : i + text_speed]
                    yield chunk
                    await asyncio.sleep(0.1)  

# Main Chat Stream
@app.post("/chat/")
async def chat(payload: DataModel):
    print(payload.session, payload.data)
    return StreamingResponse(generateChatStream(session_id=payload.session, message=payload.data), media_type="text/event-stream")


# Notification Socket
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


# SignUp / Login
@app.post("/sign_up/")
async def signUp(payload: UserDataModel):
    print(payload.username, payload.password)

    if findUser(payload.username):
        return {"status": False, "message": "username alrady"}
    createUser(username=payload.username, password=payload.password, email="")
    return True

@app.post("/sign_in/")
async def signIn(payload: UserDataModel):
    print(payload.username, payload.password)

    found = checkPassword(payload.username, payload.password)
    if found:
        id = getUserId(username=payload.username)
        return {"status": True, "user_id": id}
    else:
        return {"status": False}

# Auth
@app.post("/auth/")
async def authMiddleware(payload: AuthDataModel):
    r = auth(user_id=payload.id)
    return {"status": True, "role": r}




# Admin
@app.get("/manage/get/sectors")
async def manageGetSectors(response: Response):
    try:
        res = getAllSector()
        response.status_code = status.HTTP_200_OK
        return {"status": True, "info": res}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "info": ""}

@app.get("/manage/get/company")
async def manageGetCompany(response: Response):
    try:
        res = getAllCompaniesInfo()
        response.status_code = status.HTTP_200_OK
        return {"status": True, "info": res}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "info": ""}
    
@app.get("/manage/get/companyFile/{company}")
async def manageGetCompany(company:str, response: Response):
    # try:
        res = getALLSQLCompanyDataFile(company_abbr=company)
        response.status_code = status.HTTP_200_OK
        return {"status": True, "info": res}
    # except:
    #     response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    #     return {"status": False, "info": ""}

@app.get("/manage/get/general")
async def manageGetCompany(response: Response):
    try:
        res = getAllGeneralFile()
        response.status_code = status.HTTP_200_OK
        return {"status": True, "info": res}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "info": ""}

@app.get("/manage/info")
async def manageInfo(response: Response):
    try:
        res = getInfo()
        response.status_code = status.HTTP_200_OK
        return {"status": True, "info": res}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "info": ""}
    
@app.post("/manage/addCompany")
async def authMiddleware(payload: AddCompanyDataModel, response: Response):
    found_name:list = findCompanies([payload.abbr])
    print(found_name, [payload.abbr])
    if found_name == [payload.abbr]:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Already have a Company"}
    
    try:
        createNewCompany(abbr=payload.abbr, name_th=payload.name_th,
                        name_en=payload.name_en, sector_id=payload.sector_id)
        return {"status": True, "message": "Add New Company Succesful"}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": "Error"}


@app.post("/manage/update/description")
async def authMiddleware(payload: updateDescriptionGeneralDataModel, response: Response):
    found_name:bool = findDocument(payload.name)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    # try:
    updateDescriptionGeneralData(name=payload.name, new_description=payload.description)
    response.status_code = status.HTTP_200_OK
    return {"status": True, "message": "Update Description Succesfully"}
    # except:
    #     response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    #     return {"status": False, "message": "Error"}
    

@app.post("/manage/delete/generalFile")
async def authMiddleware(payload: deleteDataModel, response: Response):
    found_name:bool = findDocument(payload.name)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    # try:
    deleteGeneralFile(name=payload.name)
    response.status_code = status.HTTP_200_OK
    return {"status": True, "message": "Delete File Succesfully"}
    # except:
    #     response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    #     return {"status": False, "message": "Error"}

@app.post("/manage/delete/company")
async def authMiddleware(payload: deleteDataModel, response: Response):
    found_name:bool = findCompany(payload.name)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    # try:
    deleteCompanyData(name=payload.name)
    response.status_code = status.HTTP_200_OK
    return {"status": True, "message": "Delete File Succesfully"}
    # except:
    #     response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    #     return {"status": False, "message": "Error"}


@app.post("/manage/delete/companyFile")
async def authMiddleware(payload: deleteCompanyEashDataModel, response: Response):
    found_name:bool = findCompany(payload.abbr)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    # try:
    deleteEachCompanyFileData(file_name=payload.file_name, company_abbr=payload.abbr)
    response.status_code = status.HTTP_200_OK
    return {"status": True, "message": "Delete File Succesfully"}
    # except:
    #     response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    #     return {"status": False, "message": "Error"}







# Add General Document
async def createAsyncGeneralTask(raw, file, type, partition, description):
    # if type == True:
    print("[CORE] Create Task NDC")
    task = ndcTask
    # elif type == "general_documents":
    #     pass
    # elif type == "company_documents":
    #     pass
    # elif type == "etc":
    #     pass
    # else:
    #     return

    result = await asyncio.to_thread(task, raw, file, partition, description)
    return result

async def chunkingGeneralTask(raw, file_name, user_id, type, partition, description):
    await createAsyncGeneralTask(raw, file_name, type, partition, description)
    # print(f.filename)
    await active_connections[user_id].send_text(f"Computation completed: {file_name}")


@app.post("/manage/upload/generalFile/{user_id}")
async def upload_file(user_id:str,
                    response: Response,
                    name: str= Form(...),
                    description: str= Form(...),
                    file: UploadFile = File(...)):
    
    content = await file.read()
    raw_content = BytesIO(content)

    found_name = findDocument(name)
    if found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Already Name Exits"}
    
    if user_id in active_connections:
        await active_connections[user_id].send_text(f"Upload started: {file.filename}")

    asyncio.create_task(chunkingGeneralTask(raw_content, file.filename, user_id, type=name, partition=name, description=description))
    response.status_code = status.HTTP_200_OK
    return {"status": True}





# Add Company Document
async def createAsyncCompanyTask(raw, file, type, partition):
    if type == "56-1":
        print("[CORE] Create Task 56-1")
        task = oneReportTask
    elif type == "esg":
        print("[CORE] Create Task esg")
        task = esgReportTask
    elif type == "etc":
        print("[CORE] Create Task etc")
        # task = esgReportTask
        pass
    # elif type == "ndc":
    #     print("[CORE] Create Task NDC")
    #     task = ndcTask
    # elif type == "general_documents":
    #     pass
    # elif type == "company_documents":
    #     pass
    else:
        return

    result = await asyncio.to_thread(task, raw, file, partition)
    return result


async def chunkingTask(raw, file_name, user_id, type, partition):
    await createAsyncCompanyTask(raw, file_name, type, partition)
    # print(f.filename)
    await active_connections[user_id].send_text(f"Computation completed: {file_name}")


@app.post("/manage/upload/companyFile/{user_id}")
async def upload_file(user_id:str,
                    type: str = Form(...),
                    partition: str= Form(...),
                    file_name: str= Form(...),
                    file: UploadFile = File(...)):
    loc_id:str = getCompanyId(name=partition)
    found:bool = findSQLComapnyDataFile(company_id=loc_id, file_name=file_name)

    print(partition, loc_id, found, file_name)
    if found:
        return {"status": False, "message": "Already File Exits"}
    content = await file.read()
    raw_content = BytesIO(content)

    if user_id in active_connections:
        await active_connections[user_id].send_text(f"Upload started: {file.filename}")

    asyncio.create_task(chunkingTask(raw_content, file_name, user_id, type=type, partition=partition))
    return {"status": True}