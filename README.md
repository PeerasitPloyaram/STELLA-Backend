# STELLA Backend
##### STELLA stands for [LLM for S.E.T]
It is a web application that allows users and guests to ask questions and receive answers from files stored in the system, such as One Reports (56-1), ESG Reports, or other related documents.

###### This project is my Senior Project (014184999) in Computer Science at Kasetsart University.

### Member
- ##### นาย พีรสิษฐ์ พลอยอร่าม 6410451237

<br>

### STELLA is Contains of 2 Repositories
- [STELLA Frontend](https://github.com/PeerasitPloyaram/RAG-SET)
- [STELLA Backend (This Project)](https://github.com/PeerasitPloyaram/STELLA-Backend)

### About This Repository
This repository is a backend of STELLA for API Server And SELF RAG System

<br>

### Requirement
- Hardware
    1. The computer must have more than 8 GB of RAM, as the Embedding Model requires approximately 2 GB of RAM.
    2. At least 4 GB of storage is required to run this project (For Caches and Vector DB).
- Software
    1. [Python](https://www.python.org/downloads/release/python-3120/) version 3.12

    2. [OpenAI](https://platform.openai.com) Account (for get API KEY)

<br>

### Caution
- ##### This backend is using a large amount of CPU and Memory to run the server. Please stop other processes or programs before run this.
- ##### After the server starts for the first time, retrieving data takes more time to load the collection into memory.

<br>

### Install
1. Install Environment
```
python -m venv venv
```

<br>

2. Activate Environment
```
./venv/bin/activate
```

<br>

3. Install Packages
```
python install -r requirements.text
```

<br>

4. Change name from .env_example to ".env" and Add Data inside .env (must be done before running Docker-Compose).


<br>

5. Install and Run Docker-Compse
```
# Change Path to Directory Milvus
cd milvus

# Run Docker-compose with use file .env
docker-compose --env-file ../.env up -d
```

<br>

6. Start Backend Server
```
# Change Path Back to Main
fastapi dev main/main.py

# After run this code it will use 1 - 2 minetues for start server
```

<br>

<br>

### Bug Milvus Caution
##### โปรเจคนี้ใช้ Milvus 2.5.4 เป็น Vector Database โดยมี BUG ที่เกิดขึ้นจากตัวของ Milvus DB เองในขั้นตอน Start Container ของ Docker ในบางครั้ง ** โดยตอนที่มีการ Start Docker-Compose ให้ลองสังเกตุว่า Container Name: milvus-standalone มีการหยุดทำงานหลังจากเริ่ม Start Container ไปหรือไม่ หากมี ให้ทำการ Restart Docker-Compose ใหม่ **
