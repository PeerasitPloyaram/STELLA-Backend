from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pprint import pprint
import os,sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chunking.one_report_file import oneReportFileChunking
from chunking.esg_file import esgFileChunking
from chunking.global_file import globalFileChunking

from db.services.user_session import createGuestSession, findSession
from exceptions.custom_exception import ChunkingError, EmbeddingError

from typing import List
from typing_extensions import TypedDict


class GraphState(TypedDict):
    question: str
    input_question: str
    generation: str
    documents: List[str]
    session_id: str | None
    counter: int


load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/milvus")

from db.services.user_session import getHistory, saveHistory

from milvus.core import Core
from milvus.schema import DATA_SOURCE_SCHEMA
from langchain_huggingface import HuggingFaceEmbeddings

from extraction.query_extractor import decompose_query

load_dotenv()
core = Core(
        database_name=os.getenv("MILVUS_DATABASE_NAME"),
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

llm_grader = ChatOpenAI(model=os.getenv("OPEN_AI_MODEL_GRADER"), temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))
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



# MAIN Promp bug
#   If question has related about more 1 company use must analyst both of data and compare like a you senior job.
#     Your answer must be precise, of high-quality, and written by an expert using an unbiased and journalistic tone.
###     Your answer must be written in the same language as the query, even if language preference is different.
#     if don't have any context, just say just say you don't have enough resources for answer this question.
#      if you don't have context more than to answer, just say that with this question, you don't have enough resources for answer this question.

    # Keep your answer ground in the facts of the Context


# Main Prompt V1 with bug use pretrain data
# prompt = """
# You are STELLA, a Senior Data Analyst specializing in company data related to the Securities Exchange of Thailand (SET). 

# When answering questions, ensure that your response is:

# 1. **Accurate**: Provide detailed, precise information based on the context or history provided.  
# 2. **Comprehensive**: Your response should fully address the query, including any necessary context, explanations, or examples.  
# 3. **Unbiased**: Present the information objectively, without any personal opinions.  
# 4. **Journalistic Tone**: Maintain a neutral, formal tone that aligns with professional industry standards.

# ### Guidelines for Responses:
# - **Thoroughness**: Write long-form answers, providing in-depth explanations to all inquiries.  
# - **Format**: Ensure use **markdown** to structure your response effectively (headings, lists, quotes, tables). 
# - **Context-Dependent**: Only use information available from the current chat history or provided context. If the information is not available, kindly state that you don’t have enough resources to answer the query.
# - **Language Consistency**: Generate responses in the same language as the input.
# - **Greeting Responses**: If the user greets you or asks general questions like “Who are you?” or “Hello,” respond naturally, without referring to limitations.

# ### Specific Instructions:
# - **Answer Structure**: Begin by addressing the user’s query directly, then break down your response into relevant sub-sections or points if needed.  
# - **Clarity**: Avoid unnecessary jargon or complexity; ensure readability for a wide audience, while maintaining professional accuracy.

# ### Data Comparison:
# - If the question **involves a comparison between two data**,explicitly points out differences, or asks to highlight variations, generate a **simple table** in markdown format.  
# - The table should include the **key metrics of both data** to allow for a structured analysis.
# - After the table, provide **a concise summary analyzing the key differences and insights**.

# #### Example Table Format:
# | Metric           | Dataset 1 Value | Dataset 2 Value | Difference/Insight |
# |-----------------|---------------|---------------|----------------|
# | Revenue (THB)  | X             | Y             | Higher revenue in Dataset 1 |
# | Net Profit     | A             | B             | Dataset 2 has better profitability |
# """



# Main Prompt V2 with not use pretrain data
prompt = """
You are STELLA, a Senior Data Analyst specializing in company data related to the Securities Exchange of Thailand (SET).

## **Response Guidelines**
When answering questions, you **must** follow this priority order:
1. **If both retrieved context and chat history exist**, use **both** to generate the response.
2. **If only retrieved context is available**, use it to generate the response.
3. **If only chat history is available**, use it to generate the response.  
   - **Do not return "not enough context" if chat history exists.**  
   - Use the conversation history to provide the most relevant answer.  
4. **If neither retrieved context nor chat history is available**, return:  
   *"I cannot generate an answer because there is not enough context."*

### **Strict Constraints**
- **No Pre-Trained Knowledge**: Responses **must only** be based on retrieved context or chat history.
- **No Assumptions**: Do not infer beyond the provided data.
- **Avoid Partial Responses**: If necessary information is missing, do not attempt to answer.

---

## **Response Logic**
- **If both retrieved context and chat history exist**, **combine them** to generate the most complete and accurate response.
- **If only retrieved context exists**, use it.
- **If only chat history exists**, **use it** and provide an answer.  
  - **You must always generate a response based on chat history if it is available.**
- **If neither retrieved context nor chat history exists**, return:  
  *"I cannot generate an answer because there is not enough context."*

---

## **Specific Instructions**
- **Answer Structure**: Begin by addressing the user’s query directly, then break down your response into relevant sub-sections or points if needed.  
- **Clarity**: Avoid unnecessary jargon or complexity; ensure readability for a wide audience, while maintaining professional accuracy.  

### **Data Comparison**
- If the question **involves a comparison between two data points**, explicitly highlight differences, variations, or insights.
- Present the key metrics in a **structured markdown table**.
- After the table, provide **a concise summary analyzing the key differences and insights**.

#### **Example Table Format**
| Metric           | Dataset 1 Value | Dataset 2 Value | Difference/Insight |
|-----------------|---------------|---------------|----------------|
| Revenue (THB)  | X             | Y             | Higher revenue in Dataset 1 |
| Net Profit     | A             | B             | Dataset 2 has better profitability |

---
  
### Guidelines for Responses:
- **Thoroughness**: Write long-form answers, providing in-depth explanations to all inquiries.  
- **Format**: Ensure use **markdown** to structure your response effectively (headings, lists, quotes, tables). 
- **Language Consistency**: Generate responses in the same language as the input.
- **Greeting Responses**: If the user greets you or asks general questions like “Who are you?” or “Hello,” respond naturally, without referring to limitations.
  
---

## **Handling Missing Context**
- **If both retrieved context and chat history exist**, combine them for the response.
- **If only retrieved context exists**, use it.
- **If only chat history exists**, **always generate a response** based on the available history.
- **If neither retrieved context nor chat history is available**, return:  
  *"I cannot generate an answer because there is not enough context."*
"""


llm_generate = ChatOpenAI(streaming=True, model_name=os.getenv("OPEN_AI_MODEL_MAIN"), temperature=0 ,api_key=os.getenv("OPEN_AI_API_KEY"))

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", prompt),
        MessagesPlaceholder(variable_name="chat_history"),
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

llm = ChatOpenAI(model=os.getenv("OPEN_AI_MODEL_GRADER"), temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))
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




### Answer Grader
class GradeAnswer(BaseModel):
    binary_score: str = Field(
        description="Answer addresses the question, 'yes' or 'no'"
    )


# LLM with function call
llm = ChatOpenAI(model=os.getenv("OPEN_AI_MODEL_GRADER"), temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))
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



### Question Re-writer

# LLM
llm = ChatOpenAI(model=os.getenv("OPEN_AI_MODEL_GRADER"), temperature=0, api_key=os.getenv("OPEN_AI_API_KEY"))

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







### Nodes
sys.path.append(os.path.dirname(os.path.abspath(__name__)))
sys.path.append(os.path.dirname(os.path.abspath(__name__)) + "/stella/services")

from stella.services.question_classifier import classifier, createDocTable, createTable
from db.services.service import GetAllCompanies, findCompanies, getALLDocument



def question_class(state):
    print("Classify question")
    question = state["question"]
    input_question = question
    session_id = state["session_id"]
    counter = 0

    pipe = classifier()
    result = pipe.invoke({"input": question, "table": createTable(GetAllCompanies()), "general_file": createDocTable(getALLDocument())})
    if result.binary_score == "yes":
        print("Classify: Extract")
        # return {"question": question, "decide": "extract"}
        return {"question": question, "input_question": input_question, "decide": "extract", "counter": counter}
    else:
        print("Classify: Generate")
        # return {"documents": [], "question": question,  "decide": "generate", "session": session_id}
        return {"documents": [], "question": question, "input_question": input_question, "decide": "generate", "session": session_id, "counter": counter}

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
        # print("Sub Query:", sub)
        print("[Grade Doc] Question:", sub)
        document = core.stlRetreiver(user_query_input=sub)
        for doc in document:
            score = retrieval_grader.invoke(
                {"question": sub, "document": doc.page_content}
            )
            grade = score.binary_score
            if grade == "yes":
                print("Document Relevant")
                relevant_docs.append(doc)
            else:
                print("Document Not Relevant")
                continue

    print("CONTEXT:", relevant_docs)
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
    if int(counter) >= 1:
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
    input_question = state["input_question"]

    if not findSession(session_id=session_id):
        session_id = createGuestSession()

    chat_history = getHistory(session_id)
    print(chat_history)

    generation = rag_chain.invoke({"context": documents, "question": question, "chat_history": chat_history})
    print(generation)


    print("Check Hallucination")
    score = hallucination_grader.invoke(
        {"documents": documents, "generation": generation}
    )
    grade = score.binary_score
    if grade == "yes":
        saveHistory(session_id, message=input_question, role="human")
        saveHistory(session_id, message=generation, role="system")

        return {"documents": documents, "question": question, "generation": generation, "session": session_id}
    else:
        print("Check Hallucination")
        generation = rag_chain.invoke({"context": documents, "question": question, "chat_history": chat_history})
        score = hallucination_grader.invoke(
            {"documents": documents, "generation": generation}
        )
        print(score.binary_score)
        return {"documents": documents, "question": question, "generation": generation, "session": session_id}


def transform_query(state):
    print("Transform Query")
    question = state["question"]
    documents = state["documents"]
    counter = state["counter"]
    counter += 1

    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
    print("better question", better_question)
    # return {"documents": documents, "question": better_question}
    return {"documents": documents, "question": better_question, "counter": counter}


### Edges
def grade_generation_v_documents_and_question(state):
    return "useful"
    # print("Check Hallucination")
    # # question = state["question"]
    # input_question = state["input_question"]
    # documents = state["documents"]
    # generation = state["generation"]
    # session = state["session"]
    # counter_halu = state["counter_halu"]
    # grade = state["grade"]

    # score = hallucination_grader.invoke(
    #     {"documents": documents, "generation": generation}
    # )
    # # grade = score.binary_score
    # grade = "no"

    # print("count", counter_halu)        
    # # Check hallucination
    # if grade == "yes" or counter_halu > 1:
    #     print("yes")
    #     grade = "yes"
    #     state["grade"] = grade
    #     # score = answer_grader.invoke({"question": question, "generation": generation})
    #     # grade = score.binary_score
    #     # if grade == "yes":
    #     #     print("useful")
    #     print("save question", input_question)
    #     saveHistory(session, message=input_question, role="human")
    #     saveHistory(session, message=generation, role="system")
    #     return "useful"
    #     # else:
    #     #     print("not useful")
    #     #     return "not useful"
    # else:
    #     pprint("not supports")
    #     state["grade"] = "no"
    #     return "not supported"
    










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
# Company One Report
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

# Company ESG Report
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

# Company Global File (ETC)
def etcTask(raw:str, file:str, partition_name:str, start_page:int=1):
    chunks = None
    try:
        chunks = globalFileChunking(content=raw, file_name=file, start_page=start_page, verbose=False)
        if chunks == "Faliure":
            raise ChunkingError("Chunking Error")
    except:
        raise ChunkingError("Chunking Error")
    try:
        core.add_document(name=partition_name, documents=chunks, node_type="c", file_type="etc", file_name=file)
        pass
    except:
        raise EmbeddingError("Embedding Error")
    return "Computation completed"

# Global File
def generalTask(raw:str, file:str, partition_name:str, description:str, start_page:int=1):
    chunks = None
    try:
        chunks = globalFileChunking(content=raw, file_name=file, start_page=start_page, verbose=False)
        if chunks == "Faliure":
            raise ChunkingError("Chunking Error")
    except:
        raise ChunkingError("Chunking Error")
    try:
        # "National disclosure standards for financial climate, climate risk, NFCCC"
        core.add_document(name=partition_name, documents=chunks, node_type="g", description=description)
        pass
    except:
        raise EmbeddingError("Embedding Error")
    return "Computation completed"