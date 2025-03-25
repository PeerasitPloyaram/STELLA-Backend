from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os,sys
from dotenv import load_dotenv
from langchain_core.documents import Document

from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

from langchain_core.pydantic_v1 import BaseModel, Field
class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )


# GRADER
llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=os.getenv("OPEN_AI_API_KEY"))
structured_llm_grader = llm.with_structured_output(GradeDocuments)
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




### GENERATE
system_prompt = """
    You are STELLA, a helpful search assistant.

    # General Instructions

    Write an accurate, detailed, and comprehensive response to the user's query located at INITIAL_QUERY.
    Additional context is provided as "USER_INPUT" after specific questions.
    Your answer must be precise, of high-quality, and written by an expert using an unbiased and journalistic tone.
    Your answer must be written in the same language as the query, even if language preference is different.

    You MUST NEVER use moralization or hedging language. AVOID using the following phrases:

    - "It is important to ..."
    - "It is inappropriate ..."
    - "It is subjective ..."

    You MUST ADHERE to the following formatting instructions:

    - Use markdown to format paragraphs, lists, tables, and quotes whenever possible.
    - Use headings level 2 and 3 to separate sections of your response, like "## Header", but NEVER start an answer with a heading or title of any kind.
    - Use single new lines for lists and double new lines for paragraphs.
    - Use markdown to render images given in the search results.
    - NEVER write URLs or links.
\n\n
{context}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{question}"),
    ]
)

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)
# Chain
rag_chain = prompt | llm | StrOutputParser()







### Hallucination Grader
class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""

    binary_score: str = Field(
        description="Answer is grounded in the facts, 'yes' or 'no'"
    )
structured_llm_grader = llm.with_structured_output(GradeHallucinations)

# Prompt
system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. \n 
     Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
hallucination_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
    ]
)
hallucination_grader = hallucination_prompt | structured_llm_grader







### Answer Grader
# Data model
class GradeAnswer(BaseModel):
    """Binary score to assess answer addresses question."""

    binary_score: str = Field(
        description="Answer addresses the question, 'yes' or 'no'"
    )
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




### Question Re-writer
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






sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend")
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/milvus")
from milvus.core import Core
from milvus.schema import DATA_SOURCE_SCHEMA, FRONTEND_QUERY_SOURCE_SCHEMA, INDEX_PARAMS, FRONTEND_QUERY_PARAMS
core = Core(
            database_name="new_core",
            schema=DATA_SOURCE_SCHEMA,
            dense_embedding_model=HuggingFaceEmbeddings(model_name=os.getenv("DENSE_EMBEDDING_MODEL")),
            create_first_node=False,
            system_prune_first_node=False,
            token=os.getenv('TOKEN'),
        )



	
from typing import List
from pprint import pprint
from typing_extensions import TypedDict


class GraphState(TypedDict):
    """
    Represents the state of our graph.
    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
    """

    question: str
    generation: str
    documents: List[str]




### Nodes
def retrieve(state):
    print("RETRIEVE")
    question = state["question"]
    documents = core.stlRetreiver(user_query_input=question)
    return {"documents": documents, "question": question}


def generate(state):
    print("GENERATE")
    question = state["question"]
    documents = state["documents"]
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}


def grade_documents(state):
    print("Check document relevance to question")
    question = state["question"]
    documents = state["documents"]

    filtered_docs = []
    for d in documents:
        score = retrieval_grader.invoke(
            {"question": question, "document": d.page_content}
        )
        print("Question:", question)
        print("content:", d.metadata)

        if score == None:
            print("GRADE: DOCUMENT NOT RELEVANT")
            continue

        if score.binary_score == "yes" or score.binary_score == "YES":
            print("GRADE: DOCUMENT RELEVANT")
            filtered_docs.append(d)
        else:
            print("GRADE: DOCUMENT NOT RELEVANT")
            continue
    return {"documents": filtered_docs, "question": question}


def transform_query(state):
    print("Transform query")
    question = state["question"]
    documents = state["documents"]

    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question}


def decide_to_generate(state):
    print("ASSESS GRADED DOCUMENTS")
    state["question"]
    filtered_documents = state["documents"]

    if not filtered_documents:
        print("DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY")
        return "transform_query"
    else:
        print("DECISION: Gereate")
        return "generate"


def grade_generation_v_documents_and_question(state):
    print("CHECK Hullucination")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    score = hallucination_grader.invoke(
        {"documents": documents, "generation": generation}
    )
    grade = score.binary_score

    if grade == "yes":
        print("DECISION: GENERATION IS GROUNDED IN DOCUMENTS")
        # Check question-answering
        print("GRADE GENERATION vs QUESTION")
        score = answer_grader.invoke({"question": question, "generation": generation})
        grade = score.binary_score
        if grade == "yes":
            print("DECISION: GENERATION ADDRESSES QUESTION")
            return "useful"
        else:
            print("DECISION: GENERATION DOES NOT ADDRESS QUESTION")
            return "not useful"
    else:
        pprint("DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY")
        return "not supported"







from langgraph.graph import END, StateGraph, START

workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("retrieve", retrieve)  # retrieve
workflow.add_node("grade_documents", grade_documents)  # grade documents
workflow.add_node("generate", generate)  # generatae
workflow.add_node("transform_query", transform_query)  # transform_query

# Build graph
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "transform_query": "transform_query",
        "generate": "generate",
    },
)
workflow.add_edge("transform_query", "retrieve")
workflow.add_conditional_edges(
    "generate",
    grade_generation_v_documents_and_question,
    {
        "not supported": "generate",
        "useful": END,
        "not useful": "transform_query",
    },
)

# Compile
app = workflow.compile()




inputs = {"question": "ndc thailand คือ (ภาษาไทย)"}
for output in app.stream(inputs):
    for key, value in output.items():
        # Node
        pprint(f"Node '{key}':")
    pprint("\n\n")

# Final generation
pprint(value["generation"])