from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain_core.output_parsers import StrOutputParser

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pprint import pprint

import os,sys
load_dotenv()
sys.path.insert(0, "D:/STELLA-Backend/")
sys.path.insert(0, "D:/STELLA-Backend/milvus/")

from milvus.core import Core
from milvus.schema import DATA_SOURCE_SCHEMA
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
core = Core(
            database_name="new_core",
            schema=DATA_SOURCE_SCHEMA,
            dense_embedding_model=HuggingFaceEmbeddings(model_name=os.getenv("DENSE_EMBEDDING_MODEL")),
            create_first_node=False,
            system_prune_first_node=False,
            token=os.getenv('TOKEN'),
        )





### Retrieval Grader
class GradeDocuments(BaseModel):
    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )

llm_grader = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))
structured_llm_grader = llm_grader.with_structured_output(GradeDocuments)

# Prompt
system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
    It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
    If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
    ]
)

retrieval_grader = grade_prompt | structured_llm_grader


# question = "bts กับ esg"
# docs = core.stlRetreiver(question)
# for i in docs:
#     print(i)
#     print(retrieval_grader.invoke({"question": question, "document": i}))
#     print("====")



# MAIN Generation
prompt = """
    You are STELLA, senior Data Analyst related about companies data in Securities Exchange of Thailand:SET.


    Write an accurate, detailed, and comprehensive response to the user's question related about 
    Additional context is provided as "question" after specific questions.
    If question has related about more 1 company use must analyst both of data and compare like a you senior job.
    Your answer must be precise, of high-quality, and written by an expert using an unbiased and journalistic tone.
    Your answer must be written in the same language as the query, even if language preference is different.
    if you don't have context more than to answer, just say you don't have enough resources for answer this question.
    If you don't know the answer, just say that you don't know

    - Use markdown to format paragraphs, lists, tables, and quotes whenever possible.
    - Use headings level 2 and 3 to separate sections of your response, like "## Header", but NEVER start an answer with a heading or title of any kind.
    - Use single new lines for lists and double new lines for paragraphs.

\n\n
"""
llm_generate = ChatOpenAI(streaming=True, model_name="gpt-4o-mini", temperature=0 ,api_key=os.getenv("OPEN_AI_API_KEY"))

# Post-processing
# def format_docs(docs):
#     return "\n\n".join(doc.page_content for doc in docs)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", prompt),
        ("human", "Question: \n\n{question} \n\n Context: \n\n{context}"),
    ]
)

rag_chain = prompt | llm_generate | StrOutputParser()
# generation = rag_chain.invoke({"context": docs, "question": question})
# print(generation)






### Hallucination Grade
class GradeHallucinations(BaseModel):
    binary_score: str = Field(
        description="Answer is grounded in the facts, 'yes' or 'no'"
    )

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))
structured_llm_grader = llm.with_structured_output(GradeHallucinations)

system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts.\n 
Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""

hallucination_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
    ]
)

hallucination_grader = hallucination_prompt | structured_llm_grader
# print(hallucination_grader.invoke({"documents": docs, "generation": generation}))




### Answer Grader
class GradeAnswer(BaseModel):
    binary_score: str = Field(
        description="Answer addresses the question, 'yes' or 'no'"
    )


# LLM with function call
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))
structured_llm_grader = llm.with_structured_output(GradeAnswer)

# Prompt
system = """You are a grader assessing whether an answer addresses / resolves a question \n 
     Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question."""
answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
    ]
)

answer_grader = answer_prompt | structured_llm_grader
# answer_grader.invoke({"question": question, "generation": generation})



### Question Re-writer

# LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))

# Prompt
system = """You a question re-writer that converts an input question to a better version that is optimized \n 
     for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning."""
re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Here is the initial question: \n\n {question} \n Formulate an improved question.",
        ),
    ]
)

question_rewriter = re_write_prompt | llm | StrOutputParser()
# question_rewriter.invoke({"question": question})
















from typing import List
from typing_extensions import TypedDict


class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[str]


### Nodes
def retrieve(state):
    print("Retrieve:")
    question = state["question"]
    documents = core.stlRetreiver(question)
    return {"documents": documents, "question": question}


def generate(state):
    print("Generate")
    question = state["question"]
    documents = state["documents"]

    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}


def grade_documents(state):
    print("Check document relevance to question")
    question = state["question"]
    documents = state["documents"]

    relevant_docs = []
    for doc in documents:
        score = retrieval_grader.invoke(
            {"question": question, "document": doc.page_content}
        )
        grade = score.binary_score
        if grade == "yes":
            print("Document Relevant")
            relevant_docs.append(doc)
        else:
            print("Document Not Relevant")
            continue
    return {"documents": relevant_docs, "question": question}


def transform_query(state):
    print("Transform Query")
    question = state["question"]
    documents = state["documents"]

    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question}


### Edges
def decide_to_generate(state):
    print("Decide to generate or not")
    state["question"]
    filtered_documents = state["documents"]

    if not filtered_documents:
        print("Decide: No documents has relevant. Transform")
        return "transform_query"
    else:
        print("Decide: Generate")
        return "generate"


def grade_generation_v_documents_and_question(state):
    print("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    score = hallucination_grader.invoke(
        {"documents": documents, "generation": generation}
    )
    grade = score.binary_score

    # Check hallucination
    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        # Check question-answering
        print("---GRADE GENERATION vs QUESTION---")
        score = answer_grader.invoke({"question": question, "generation": generation})
        grade = score.binary_score
        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        pprint("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"
    










from langgraph.graph import END, StateGraph, START
workflow = StateGraph(GraphState)


workflow.add_node("retrieve", retrieve)                 # retrieve
workflow.add_node("grade_documents", grade_documents)   # grade documents
workflow.add_node("generate", generate)                 # generatae
workflow.add_node("transform_query", transform_query)   # transform_query


workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents", decide_to_generate,
    {
        "transform_query": "transform_query",
        "generate": "generate",
    },
)
workflow.add_edge("transform_query", "retrieve")
workflow.add_conditional_edges(
    "generate", grade_generation_v_documents_and_question,
    {
        "not supported": "generate",
        "useful": END,
        "not useful": "transform_query",
    },
)

# Compile
app = workflow.compile()















from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, UploadFile
from fastapi.responses import StreamingResponse
import asyncio

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections = {}
class DataModel(BaseModel):
    data: str


@api.websocket("/ws/{user_id}")
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




async def generateChatStream(message):
    text_speed = 30
    async for chunks in app.astream({"question": message}):
        for key, value in chunks.items():
            if "generation" in value:
                text = value["generation"]
                # yield text
                for i in range(0, len(text), text_speed):
                    chunk = text[i : i + text_speed]
                    yield chunk
                    await asyncio.sleep(0.1)  

@api.post("/chat/{user_id}")
async def chat(user_id:str, payload: DataModel):
    return StreamingResponse(generateChatStream(message=payload.data), media_type="text/event-stream")

# inputs = {"question": "bts คืออะไร"}
# for output in app.stream(inputs):
#     for key, value in output.items():
#         # Node
#         pprint(f"Node '{key}':")
#     pprint("\n---\n")

# pprint(value["generation"])