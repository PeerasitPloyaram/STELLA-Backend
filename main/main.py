import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/milvus")

from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, Form, UploadFile, Response, status

from pydantic import BaseModel
import asyncio
import httpx

import json
import os, sys
from io import BytesIO
from exceptions.custom_exception import ChunkingError, EmbeddingError

from db.services.user import createUser, findUser, checkPassword, getUserId, auth, getRole, findUserById
from db.services.vector_data import getInfo
from db.services.service import (
    getAllCompaniesInfo, getAllSector,
    findCompanies, createNewCompany,
    getAllGeneralFile, findDocument, findCompany,
    updateDescriptionGeneralData,
    deleteGeneralFile, deleteCompanyData, findSQLComapnyDataFile,
    getCompanyId, getALLSQLCompanyDataFile, deleteEachCompanyFileData
)

from db.services.user_session import (
    findSession, SessionIsExpire,
    createGuestSession, createUserSession, findSessionIsGuest,
    changeGuestSesionToUserSession, getAllChatHistoryName, dropUserSession,
    findSessionIsOwnByUser
)

from stella.services.srag import app as ai
from stella.services.srag import oneReportTask, esgReportTask, generalTask, etcTask

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

class UserSignUpDataModel(BaseModel):
    username: str
    password: str
    email: str

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

class chatSessionDataModel(BaseModel):
    user_id:str
    current_session:str

@app.post("/session/")
async def getSession(payload:chatSessionDataModel):
    print("Session Request:",payload.current_session)

    if findUserById(user_id=payload.user_id):
        if findSession(payload.current_session):
            if findSessionIsGuest(payload.current_session):
                changeGuestSesionToUserSession(session_id=payload.current_session, user_id=payload.user_id)
            new_session_id = payload.current_session

        else:
            new_session_id = createUserSession(user_id=payload.user_id)
    
    else:  
        if findSession(payload.current_session):
            new_session_id:str = payload.current_session
            if SessionIsExpire(payload.current_session):
                new_session_id = createGuestSession()
        else:
            new_session_id = createGuestSession()
    return {"status": True, "message": new_session_id}

@app.get("/session/getHistory/")
async def getSession(user_id:str, session_id:str | None):
    if findUserById(user_id=str(user_id)):
        if session_id:
            changeGuestSesionToUserSession(session_id=session_id, user_id=user_id)
            chat_names = getAllChatHistoryName(user_id=user_id, session=session_id)
        else:
            chat_names = getAllChatHistoryName(user_id=user_id)
    else:
        chat_names = getAllChatHistoryName(user_id="guest", session=session_id)

    return {"status": True, "message": chat_names}

@app.post("/session/deleteSession")
async def deleteUserSession(payload:chatSessionDataModel):
    if findUserById(user_id=str(payload.user_id)):
        if findSessionIsOwnByUser(user_id=payload.user_id, session=payload.current_session):
            dropUserSession(user_id=payload.user_id, session_id=payload.current_session)
            return {"status": True, "message": "Drop User Session Successfully"}
    

async def generateChatStream(session_id:str, message):
    text_speed = 30
    try:
        flag = True
        async for chunks in ai.astream({"question": message, "session_id": session_id}):
            for key, value in chunks.items():
                if "documents" in value and flag:
                    yield "generating"
                    flag = False

                if "generation" in value:
                    text = value["generation"]
                    for i in range(0, len(text), text_speed):
                        chunk = text[i : i + text_speed]
                        yield chunk
                        await asyncio.sleep(0.1)  
    except httpx.RemoteProtocolError as e:
        print(f"Remote protocol error while streaming: {e}")
        raise HTTPException(status_code=503, detail="External service error")
    except asyncio.CancelledError:
        print("Stream was cancelled")
        raise HTTPException(status_code=408, detail="Request Timeout")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
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
async def signUp(payload: UserSignUpDataModel):
    if findUser(payload.username):
        return {"status": False, "message": "Username Already Exists."}
    createUser(username=payload.username, password=payload.password, email=payload.email)
    return {"status": True, "message": "Create User Succesfully"}

@app.post("/sign_in/")
async def signIn(payload: UserDataModel):
    found:bool = checkPassword(payload.username, payload.password)
    if found:
        id:str = getUserId(username=payload.username)
        role:str = getRole(username=payload.username)
        return {
            "status": True,
            "user_id": id,
            "role": role[1],
            "username": payload.username
        }
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
    try:
        res = getALLSQLCompanyDataFile(company_abbr=company)
        response.status_code = status.HTTP_200_OK
        return {"status": True, "info": res}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "info": ""}

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
        return {"status": True, "message": "Add New Company Succesfully."}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": "Error"}


@app.post("/manage/update/description")
async def authMiddleware(payload: updateDescriptionGeneralDataModel, response: Response):
    found_name:bool = findDocument(payload.name)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    try:
        updateDescriptionGeneralData(name=payload.name, new_description=payload.description)
        response.status_code = status.HTTP_200_OK
        return {"status": True, "message": "Update Description Succesfully"}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": "Error"}
    

@app.post("/manage/delete/generalFile")
async def authMiddleware(payload: deleteDataModel, response: Response):
    found_name:bool = findDocument(payload.name)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    try:
        deleteGeneralFile(name=payload.name)
        response.status_code = status.HTTP_200_OK
        return {"status": True, "message": "Delete File Succesfully"}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": "Error"}

@app.post("/manage/delete/company")
async def authMiddleware(payload: deleteDataModel, response: Response):
    found_name:bool = findCompany(payload.name)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    try:
        deleteCompanyData(name=payload.name)
        response.status_code = status.HTTP_200_OK
        return {"status": True, "message": "Delete File Succesfully"}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": "Error"}


@app.post("/manage/delete/companyFile")
async def authMiddleware(payload: deleteCompanyEashDataModel, response: Response):
    found_name:bool = findCompany(payload.abbr)
    if not found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Not Found"}
    
    try:
        deleteEachCompanyFileData(file_name=payload.file_name, company_abbr=payload.abbr)
        response.status_code = status.HTTP_200_OK
        return {"status": True, "message": "Delete File Succesfully"}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": "Error"}







# Add General Document
async def createAsyncGeneralTask(raw, file, partition, description, start_page):
    print("[CORE] Create Task General")
    task = generalTask
    result = await asyncio.to_thread(task, raw, file, partition, description, start_page)
    return result

async def chunkingGeneralTask(raw, file_name, user_id, partition, description, start_page):
    try:
        await createAsyncGeneralTask(raw, file_name, partition, description, start_page)
        noti_template = {
            "title": "Upload Successfully.",
            "message":f"Chunking and Embedding File: {file_name} Completed.",
            "type": "success"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))
    except ChunkingError:
        noti_template = {
            "title": "Upload Failured.",
            "message":f"Error to Chunking File: {file_name}",
            "type": "error"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))
    except EmbeddingError:
        noti_template = {
            "title": "Upload Failured.",
            "message":f"Error to Embedding File: {file_name}",
            "type": "error"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))


@app.post("/manage/upload/generalFile/{user_id}")
async def upload_file(user_id:str, response: Response,
                    name: str= Form(...),
                    description: str= Form(...),
                    file: UploadFile = File(...),
                    start_page: int= Form(...)
                ):
    
    content = await file.read()
    raw_content = BytesIO(content)

    found_name = findDocument(name)
    if found_name:
        response.status_code = status.HTTP_200_OK
        return {"status": False, "message": "Already Name Exits"}
    
    if user_id in active_connections:
        noti_template = {
            "title": "Upload Started",
            "message":f"Upload File: {file.filename} Started.",
            "type": "success"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))

    asyncio.create_task(chunkingGeneralTask(raw_content, file.filename, user_id, partition=name, description=description, start_page=start_page))
    response.status_code = status.HTTP_200_OK
    return {"status": True}





# Add Company Document
async def createAsyncCompanyTask(raw, file, type, partition, start_page):
    if type == "56-1":
        print("[CORE] Create Task 56-1")
        task = oneReportTask
    elif type == "esg":
        print("[CORE] Create Task esg")
        task = esgReportTask
    elif type == "etc":
        print("[CORE] Create Task etc")
        task = etcTask
        result = await asyncio.to_thread(task, raw, file, partition, start_page)
        return result
    else:
        return

    result = await asyncio.to_thread(task, raw, file, partition)
    return result


async def chunkingCompanyTask(raw, file_name, user_id, type, partition, start_page):
    try:
        await createAsyncCompanyTask(raw, file_name, type, partition, start_page=start_page)
        noti_template = {
            "title": "Upload Successfully.",
            "message":f"Chunking and Embedding File: {file_name} Completed.",
            "type": "success"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))
    except ChunkingError:
        noti_template = {
            "title": "Upload Failured.",
            "message":f"Error to Chunking File: {file_name}",
            "type": "error"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))
    except EmbeddingError:
        noti_template = {
            "title": "Upload Failured.",
            "message":f"Error to Embedding File: {file_name}",
            "type": "error"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))

@app.post("/manage/upload/companyFile/{user_id}")
async def upload_file(user_id:str,
                    type: str = Form(...),
                    partition: str= Form(...),
                    file_name: str= Form(...),
                    file: UploadFile = File(...),
                    start_page: int= Form(...)):
    
    loc_id:str = getCompanyId(name=partition)
    found:bool = findSQLComapnyDataFile(company_id=loc_id, file_name=file_name)

    print(partition, loc_id, found, file_name)
    if found:
        return {"status": False, "message": "Already File Exits"}
    content = await file.read()
    raw_content = BytesIO(content)

    if user_id in active_connections:
        noti_template = {
            "title": "Upload Started",
            "message":f"Upload File: {file_name} Started.",
            "type": "success"
        }
        await active_connections[user_id].send_text(json.dumps(noti_template))

    asyncio.create_task(chunkingCompanyTask(raw_content, file_name, user_id, type=type, partition=partition, start_page=start_page))
    return {"status": True}