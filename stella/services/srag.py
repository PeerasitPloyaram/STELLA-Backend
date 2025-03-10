from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pprint import pprint

from chunking.one_report_file import oneReportFileChunking
from chunking.esg_file import esgFileChunking
from chunking.ndc_file import ndcFileChunking

from db.services.user_session import SessionIsExpire, createGuestSession, findSession
from exceptions.custom_exception import ChunkingError, EmbeddingError
import os,sys

load_dotenv()

sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/")
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/milvus/")
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/db/")
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/db/services/")

from db.services.user_session import getHistory, saveHistory

from milvus.core import Core
from milvus.schema import DATA_SOURCE_SCHEMA
from langchain_huggingface import HuggingFaceEmbeddings

from extraction.query_extractor import decompose_query

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



# MAIN Generation
#   Write an accurate, detailed, and comprehensive response to the user's question related about
#   Additional context is provided as "question" after specific questions.
#   If question has related about more 1 company use must analyst both of data and compare like a you senior job.
#     Your answer must be precise, of high-quality, and written by an expert using an unbiased and journalistic tone.
#     Your answer must be written in the same language as the query, even if language preference is different.
#     if don't have any context, just say just say you don't have enough resources for answer this question.
#      if you don't have context more than to answer, just say that with this question, you don't have enough resources for answer this question.
prompt = """
    You are STELLA, senior Data Analyst related about companies data in Securities Exchange of Thailand:SET.
    Write an accurate, detailed, and comprehensive response to the user's question related about

    You must answer only using the provided context or chat history.
    Keep your answer ground in the facts of the Context.
    If the answer is not found in the context or history, just say just say you don't have enough resources for answer this question.
    Do not use any external or pre-trained knowledge.

    If the user's query is a simple greeting (e.g., 'hello', 'hi', 'good morning'), respond naturally instead of saying there's not enough resources.
    If the user's query is a general greeting or an inquiry like 'Who are you?', respond naturally instead of saying there's not enough resources.

    - Use markdown to format paragraphs, lists, tables, and quotes whenever possible.
    - Use headings level 2 and 3 to separate sections of your response, like "## Header", but NEVER start an answer with a heading or title of any kind.
    - Use single new lines for lists and double new lines for paragraphs.

\n\n
"""
llm_generate = ChatOpenAI(streaming=True, model_name="gpt-4o", temperature=0 ,api_key=os.getenv("OPEN_AI_API_KEY"))

# Post-processing
# def format_docs(docs):
#     return "\n\n".join(doc.page_content for doc in docs)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        # ("human", "Question: \n\n{question} \n\n Context: \n\n{context}"),
        ("Context: Context\n\n{context}"),
        ("human", "Question: \n\n{question}")
    ]
)

rag_chain = prompt | llm_generate | StrOutputParser()






### Hallucination Grade
class GradeHallucinations(BaseModel):
    binary_score: str = Field(
        description="Answer is grounded in the facts, 'yes' or 'no'"
    )

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))
structured_llm_grader = llm.with_structured_output(GradeHallucinations)

system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts.
\n Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts.\n
IF don't have any fact give a binay score 'yes'
"""

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
# """You are a grader assessing whether an answer addresses / resolves a question \n 
#      Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question."""
system = """You are a grader assessing whether an answer addresses / resolves a question.  
- If the question is a general greeting (e.g., 'hello', 'hi', 'who are you?'), and the answer is a natural response, return 'yes'.  
- Otherwise, return 'yes' only if the answer sufficiently resolves the question.  
- If the answer is irrelevant or does not resolve the question, return 'no'.
- If the answer likely don't have enough information to answer this question. retrun 'yes'.
"""
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
system = """You are a question rewriter that converts an input question into a more precise and optimized version 
for vector store retrieval. Analyze the input query to understand its semantic intent and refine it for better clarity, 
relevance, and specificity.

- Ensure the question aligns with the Securities Exchange of Thailand (SET) domain.
- Preserve company names exactly as they appear in the original query.
- Clarify ambiguous terms and expand abbreviations when necessary.
- Maintain the original language of the query.
- Improve structure for better retrieval performance.
"""

re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Here is the initial question related to the Securities Exchange of Thailand (SET): \n\n {question} \n\n"
            "Formulate an improved question that is clearer and better suited for vector retrieval.\n"
            "**Ensure company names (e.g., True, AOT, BTS) remain unchanged.**",
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
    session_id: str | None
    counter: int


### Nodes
from stella.services.question_classifier import classifier
sys.path.append(os.path.dirname(os.path.abspath(__name__)))
from db.services.service import GetAllCompanies, findCompanies

def createTable(data:dict):
    table = []
    table.append("| Stock Name or Abbreviation | Company Name in Thai                     | Company Name in English           |")
    table.append("    |----------------------------|------------------------------------------|-----------------------------------|")

    for stock, thai_name, english_name in data:
        table.append(f"    | {stock:<26} | {thai_name:<45} | {english_name:<33} |")

    return "\n".join(table) + "\n    ----"


def question_class(state):
    print("Classify question")
    question = state["question"]
    session_id = state["session_id"]
    counter = 0

    pipe = classifier()
    result = pipe.invoke({"input": question, "table": createTable(GetAllCompanies())})
    if result.binary_score == "yes":
        print("Classify: Extract")
        # return {"question": question, "decide": "extract"}
        return {"question": question, "decide": "extract", "counter": counter}
    else:
        print("Classify: Generate")
        # return {"documents": [], "question": question,  "decide": "generate", "session": session_id}
        return {"documents": [], "question": question,  "decide": "generate", "session": session_id, "counter": counter}

def question_classify(state):
    d = state["decide"]

    if d == "extract":
        return "extract"
    else:
        return "generate"

def retrieve_and_gradeDco(state):
    print("Retrieve:")
    question = state["question"]
    counter = state["counter"]
    
    # documents = []
    relevant_docs = []
    sub_query:list = decompose_query(original_query=question)
    for sub in sub_query:
        print("Sub Query:", sub)
        document = core.stlRetreiver(user_query_input=sub)
        for doc in document:
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
    # documents = core.stlRetreiver(question)

    print("CONTEXT:", relevant_docs)
    # return {"documents": documents, "question": question}
    return {"documents": relevant_docs, "question": question, "counter": counter}

# def grade_documents(state):
#     print("Check document relevance to question")
#     question = state["question"]
#     documents = state["documents"]
#     counter = state["counter"]

#     relevant_docs = []
#     # if not relevant_docs:
#     #     return {"documents": [], "question": question}
#         # return {"documents": [], "question": question, "counter": counter}
#     for doc in documents:
#         score = retrieval_grader.invoke(
#             {"question": question, "document": doc.page_content}
#         )
#         grade = score.binary_score
#         if grade == "yes":
#             print("Document Relevant")
#             relevant_docs.append(doc)
#         else:
#             print("Document Not Relevant")
#             continue
#     # return {"documents": relevant_docs, "question": question}
#     return {"documents": relevant_docs, "question": question, "counter": counter}

def decide_to_generate(state):
    print("Decide to generate or not")
    state["question"]
    filtered_documents = state["documents"]
    counter = state["counter"]
    print("Count:", counter)
    if int(counter) >= 2:
        print("Decide: Generate")
        return "generate"

    if not filtered_documents:
        print("Decide: No documents has relevant. Transform")
        return "transform_query"
    else:
        print("Decide: Generate")
        return "generate"


def generate(state):
    print("Generate")
    question = state["question"]
    documents = state["documents"]
    session_id = state["session_id"]
    # counter = state["counter"]

    if not findSession(session_id=session_id):
        # if SessionIsExpire(session_id=session_id):
        #     session_id = createGuestSession()
        #     print("Session: is expire")
        # print("Session: Found and not expire")
    # else:
        session_id = createGuestSession()

    chat_history = getHistory(session_id)
    print(chat_history)

    generation = rag_chain.invoke({"context": documents, "question": question, "chat_history": chat_history})
    print(generation)
    # print("session", session_id)
    return {"documents": documents, "question": question, "generation": generation, "session": session_id}
    # return {"documents": documents, "question": question, "generation": generation, "session": session_id, "counter": counter}


def transform_query(state):
    print("Transform Query")
    question = state["question"]
    documents = state["documents"]
    counter = state["counter"]
    counter += 1
    # if not documents:
    #     return {"documents": [], "question": question, "counter": counter}

    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
    print("better question", better_question)
    # return {"documents": documents, "question": better_question}
    return {"documents": documents, "question": better_question, "counter": counter}


### Edges
def grade_generation_v_documents_and_question(state):
    print("Check Hallucination")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    session = state["session"]

    score = hallucination_grader.invoke(
        {"documents": documents, "generation": generation}
    )
    grade = score.binary_score

    # Check hallucination
    if grade == "yes":
        print("yes")
        # score = answer_grader.invoke({"question": question, "generation": generation})
        # grade = score.binary_score
        # if grade == "yes":
        #     print("useful")
        saveHistory(session, message=question, role="human")
        saveHistory(session, message=generation, role="system")
        return "useful"
        # else:
        #     print("not useful")
        #     return "not useful"
    else:
        pprint("not supports")
        return "not supported"
    










from langgraph.graph import END, StateGraph, START
workflow = StateGraph(GraphState)

workflow.add_node("classify", question_class)
workflow.add_node("retrieve", retrieve_and_gradeDco)      # retrieve
# workflow.add_node("grade_documents", grade_documents)   # grade documents
workflow.add_node("generate", generate)                 # generatae
workflow.add_node("transform_query", transform_query)   # transform_query

workflow.add_edge(START, "classify")
workflow.add_conditional_edges(
    "classify", question_classify,
    {
        "extract": "retrieve",
        "generate": "generate"
    }
)
# workflow.add_edge(START, "retrieve")
# workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "retrieve", decide_to_generate,
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




# Add Document
def oneReportTask(raw:str, file:str, partition_name:str):
    chunks = None
    try:
        chunks = oneReportFileChunking(content=raw, file_name=file)
    except:
        raise ChunkingError("Chunking Error")
    try:
        core.add_document(name=partition_name, documents=chunks, node_type="c", file_type="one_report", file_name=file)
    except:
        raise EmbeddingError("Embedding Error")
    
    return "Computation completed"

def esgReportTask(raw:str, file:str, partition_name:str):
    chunks = None
    try:
        chunks = esgFileChunking(content=raw, file_path=file)
    except:
        raise ChunkingError("Chunking Error")
    try:
        core.add_document(name=partition_name, documents=chunks, node_type="c", file_type="esg_report", file_name=file)
    except:
        raise EmbeddingError("Embedding Error")
    return "Computation completed"

def ndcTask(raw:str, file:str, partition_name:str, description:str):
    chunks = None
    try:
        chunks = ndcFileChunking(content=raw, file_name=file)
    except:
        raise ChunkingError("Chunking Error")
    try:
        # "National disclosure standards for financial climate, climate risk, NFCCC"
        core.add_document(name=partition_name, documents=chunks, node_type="g", description=description)
        pass
    except:
        raise EmbeddingError("Embedding Error")
    return "Computation completed"