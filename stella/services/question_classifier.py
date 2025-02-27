from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from dotenv import load_dotenv
import os

load_dotenv()

def classifier():
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPEN_AI_API_KEY"))
    class ClassifyQuestion(BaseModel):
        binary_score: str = Field(
            description="Answer addresses the question, 'yes' or 'no'"
        )

    system_prompt = """
    You are a classifier assessing whether an user question
    you task is classify the following user question as either 'extract' or 'generate'.
    Give a binary score 'yes' or 'no'. 'Yes' means use 'extract' if the question requires retrieving external knowledge.
    'No' means use 'generate' if it can be answered using only conversation history.
    """
    structured_llm_grader = llm.with_structured_output(ClassifyQuestion)
    decision_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}")
        ])

    decision_maker = decision_prompt | structured_llm_grader
    return decision_maker


if __name__ == "__main__":
    pass