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
- ##### This backend consumes a large amount of CPU and memory to run the server. Please stop other processes or programs before running it.
- ##### When starting the server for the first time, retrieving data may take longer as the collection is loaded into memory.

<br>

### Install
1. Install Environment
```
python -m venv venv
```

<br>

2. Activate Environment
```
# MacOS and Linux
./venv/bin/activate

# Window
./venv/Scripts/activate
```

<br>

3. Install Packages
```
python install -r requirements.text
```

<br>

4. Rename ```.env_example``` to ```.env``` and add the required data inside .env (this must be done before running Docker Compose).


<br>

5. Install and Run Docker-Compose
```
# Change Path to Directory Milvus
cd milvus

# Run Docker-compose with use file .env
docker-compose --env-file ../.env up -d
```

<br>

6. Init Vector Db and Schema (Only in First time)
```
# Run the script to initialize the vector database and set the configuration.
python core.py
```

The output should be like this:
```
[CORE] Initializing Milvus Database Core...
[DB] init Embedding Model...
[DB] init Embedding Model Successfully.
[DB] Found Database: global_evaluate
[DB] Create Collection "cnode_1"
[DB] Collection "cnode_1" Is Ready.
[DB] Create Collection "gnode_1"
[DB] Collection "gnode_1" Is Ready.
[DB] Create Collection "frontend_query_gnode"
[DB] Collection "frontend_query_gnode" Is Ready.
Create Schma Successfuly.
```

<br>

7. Start Backend Server
```
# Change Path Back to Main
cd ..

# Start
fastapi dev main/main.py

# After running this code, it will take 1–2 minutes to start the server.
```

<br>

<br>

### Bug Milvus Caution
##### โปรเจคนี้ใช้ Milvus 2.5.4 เป็น Vector Database โดยมี BUG ที่เกิดขึ้นจากตัวของ Milvus DB เองในขั้นตอน Start Container ของ Docker ในบางครั้ง ** โดยตอนที่มีการ Start Docker-Compose ให้ลองสังเกตุว่า Container Name: milvus-standalone มีการหยุดทำงานหลังจากเริ่ม Start Container ไปหรือไม่ หากมี ให้ทำการ Restart Docker-Compose ใหม่ **
