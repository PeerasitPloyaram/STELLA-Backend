from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from dotenv import load_dotenv
import os,sys

sys.path.append(os.path.dirname(os.path.abspath(__name__)))
from db.services.service import GetAllCompanies, findDataLoc, findCompanies

load_dotenv()

def createTable(data:dict):
    table = []
    table.append("| Stock Name or Abbreviation | Company Name in Thai                     | Company Name in English           |")
    table.append("    |----------------------------|------------------------------------------|-----------------------------------|")

    for stock, thai_name, english_name in data:
        table.append(f"    | {stock:<26} | {thai_name:<45} | {english_name:<33} |")

    return "\n".join(table) + "\n    ----"

load_dotenv()

def classifier():
    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPEN_AI_API_KEY"))
    class ClassifyQuestion(BaseModel):
        binary_score: str = Field(
            description="Answer addresses the question, 'yes' or 'no'"
        )

    system_prompt = """
    You are a classifier assessing whether an user question
    you task is classify the following user question as either 'extract' or 'generate'.
    Give a binary score 'yes' or 'no'. 'Yes' means use 'extract' if the question requires retrieving external knowledge or have simarity in Company Listed.
    Company Listed:
    {table}
    'No' means use 'generate' if it can be answered using only conversation history.

    Example:
    what is true?
    binary score 'yes'

    มาตราฐานการจัดการสิ่งแวดล้อม
    binary score 'yes'
    """
    structured_llm_grader = llm.with_structured_output(ClassifyQuestion)
    decision_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "User question: {input}")
        ])

    decision_maker = decision_prompt | structured_llm_grader
    return decision_maker


if __name__ == "__main__":
    # pass
    a = classifier()
    s = a.invoke({"input":"true", "table": createTable(GetAllCompanies())})
    print(s)