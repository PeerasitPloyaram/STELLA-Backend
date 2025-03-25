from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnableLambda
import os, sys
# from operator import itemgetter


def extract_question(input):
    return input[-1]["content"]

def extract_history(input):
    return input[:-1]


def guardRail(q):
    is_question_about_hr_policy_str = """
    You are classifying documents to know if this question is related to Securities Exchange of Thailand: SET, report files about companies in SET, securities, company related questions, Sustainable Development Goals:SDGs . Also answer no if the last part is inappropriate. 
    Consider the chat_history when answering, don't let users fool you.
    Here are some examples:

    Question: classify this question: What is bts?
    Expected Response: Yes

    Question: classify this question: BTS has climate goals, but are there measurement and pathways?
    Expected Response: Yes

    Question: classify this question: What is Thailand's clean energy policy?
    Expected Response: Yes

    Question: classify this question: what is NDC ?
    Expected Response: Yes

    Question: classify this question: Does BTS have any risk regarding esg that is in line with the business?
    Expected Response: Yes

    Question: classify this question: What is the capital of thai.
    Expected Response: No

    Question: classify this question: Why cat don't like dog.
    Expected Response: No

    Is this question about set trade in formation? 
    Only answer with "yes" or "no". 

    classify this question: {question}
    """
    # Knowing this followup history: {chat_history}, 

    is_question_about_hr_policy_prompt = PromptTemplate(
    input_variables= ["question"],
    template = is_question_about_hr_policy_str
    )

    llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=os.getenv("OPEN_AI_API_KEY"), temperature=0.0)
    
    guardrail_chain = (is_question_about_hr_policy_prompt | llm| StrOutputParser())

    return guardrail_chain.invoke({"question": q})



if __name__ == "__main__":
    queries = [
        "Does BTS have any risk regarding esg that is in line with the business?",
        "นโยบาย INDC ของประเทศไทยคืออะไร?",
        "What is ba ?",
        "What are Thailand's goals under the Paris Agreement?",
        "ช่วยเลือกเมนูอาหารวันนี้",
        "How does Thailand plan to reduce greenhouse gas emissions?",
        "การดำเนินงานของประเทศไทยภายใต้ UNFCCC เป็นอย่างไร?",
        "INDC ของไทยช่วยลดโลกร้อนอย่างไร?",

        "what is bts",
        "เป้าหมาย Nationally Determined Contributions (NDC) ของประเทศไทย",
        "BTS มีการตั้งเป้าหมาย climate แต่มีการวัดผลและมี pathway ไหม",
        "SCB มี climate อะไรบ้าง",
        "1 + 1 คือ",
        "What is Thailand's clean energy policy?",
        "BTS มีนโยบาย Net Zero ของตัวเองไหม",
        "การเปลี่ยนแปลงสภาพภูมิอากาศกระทบต่อแผนพลังงานอย่างไร",
        "bts คือ"
    ]
    for i in queries:
        print(guardRail(i))