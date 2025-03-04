from newmm_tokenizer.tokenizer import word_tokenize

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.prompts import PromptTemplate

import pythainlp
import os, sys
from dotenv import load_dotenv

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


def query_extractorV1(user_input:str):
    words = word_tokenize(text=user_input, keep_whitespace=False,engine="newmm")

    en = []
    number = []
    th = []
    for i in words:
        if pythainlp.util.isthai(i):
            th.append(i)
        elif i.isdecimal():
            number.append(i)
        else:
            if i.isalpha() and len(i) <= 8:
                en.append(i.lower())

    # print(en)
    print(number)
    # print(th)

    buffer = []
    foundLoc = findDataLoc(en)
    if foundLoc:
        for i in foundLoc:
            if number:
                template = {
                    "name": foundLoc[i][0],
                    "collection_name": foundLoc[i][1],
                    "partition_name": foundLoc[i][2],
                    "filters": number[0]
                }
            else:
                template = {
                    "name": foundLoc[i][0],
                    "collection_name": foundLoc[i][1],
                    "partition_name": foundLoc[i][2],
                    "filters": '2023'
                }  
            buffer.append(template)
            # print(foundLoc[i])
        return buffer


def query_extractorV2(user_query:str):
    system = """
    You are classifying user questions to determine which companies listed on the SET-listed companies are mentioned and the specific years referenced.
    The questions may be in Thai or English.

    ### SET-listed companies
    {table}

    Instructions:

    Extract ALL company stock name or abbreviations from the user's question that match the SET-listed companies
    Each matching company should be processed separately and included in output
    Matching should be case-insensitive (e.g., "SCB", "scb", "Scb", "'true'" all match)
    Match only the exact stock abbreviation (not the full company names)
    For EACH matched company from the SET list:

    If no specific year is mentioned, assign 2023
    If explicit years are mentioned, use those years


    Output a separate line for EACH matched company in format: stockname:year1,year2,...
    Only output [] if NO companies from the SET list are found

    Rules:

    Check EVERY potential company mention against the SET list
    Include ALL companies that match the SET list in the output
    Ignore companies not in the SET list but still output the valid ones
    All stock names in lowercase in output
    Each valid company gets its own line of output
    Use 2023 as default year for all valid companies when no year specified
    Output must not empty but it can be only [stockname:year1,year2,...] or []

    Format:
    Input: [user question]
    Output:
    [stockname:year1,year2,...]
    [stockname:year1,year2,...]
    or
    []

    Examples:
    Input: "How are SCB and TRUE's incomes different in 2023?"
    Output:
    scb:2023
    true:2023

    Input: "Total income of SCB in 2021 - 2023 compared to the latest TRUE?"
    Output:
    scb:2021,2022,2023
    true:2023

    Input: "What about AOT's performance in 2022?"
    Output:
    []
    """

    table = createTable(GetAllCompanies())
    subquery_decomposition_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "User question: {user_query}"),
    ])

    # print(system.format(table=table))
    subquery_decomposer_chain = subquery_decomposition_prompt | ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPEN_AI_API_KEY"))

    response = subquery_decomposer_chain.invoke({"user_query": user_query, "table": table}).content

    # print(response)
    buffer = []

    if response == "[]":
        print("LLM Decision", [])
        return []
    if not response:
        return response
    
    for q in response.split('\n'):
        line = q.strip()
        sp = line.split(":",1)
        name = sp[0]
        if len(sp) > 1:
            year = sp[1].split(",")

            buffer.append({
                name: year
            })
            
    print("LLM Decision", buffer)

    output = []
    for i in buffer:
        if findCompanies([list(i.keys())[0]]):
            output.append(i) 
    print("LLM Search", output)
    return output
    

def decompose_query(original_query: str):
    subquery_decomposition_template = """
    You have received a user query that involves information about companies, and the question relates to multiple companies. Please decompose the question into smaller, relevant sub-questions, ensuring that the company names and key details from the original question are preserved. Do not change the company names or alter the meaning of the questions.

    User question: {original_query}

    example: What is aot and bts?

    Sub-queries:
    1. What is bts?
    2. What is aot?

    *** Use same language as User question
    *** DONT INCLUDE A LIST NUBMER OF EACH QUESTION.
    *** DONT INCLUDE ANYTHING BEFORE OR AFTER THE QUESTIONS.
    """

    subquery_decomposition_prompt = PromptTemplate(
        input_variables=["original_query"],
        template=subquery_decomposition_template
    )

    subquery_decomposer_chain = subquery_decomposition_prompt | ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPEN_AI_API_KEY"))

    response = subquery_decomposer_chain.invoke(original_query).content
    sub_queries = [q.strip() for q in response.split('\n') if q.strip() and not q.strip().startswith('Sub-queries:')]
    return sub_queries



if __name__ == "__main__":
    queries = [
        "Does aav have any risk regarding esg that is in line with the business?",
        "นโยบาย INDC ของประเทศไทยคืออะไร?",
        "What are Thailand's goals under the Paris Agreement?",
        "How does Thailand plan to reduce greenhouse gas emissions?",
        "การดำเนินงานของประเทศไทยภายใต้ UNFCCC เป็นอย่างไร?",
        "INDC ของไทยช่วยลดโลกร้อนอย่างไร?",

        "what is advanc, scb ,aot, true?",
        "เป้าหมาย Nationally Determined Contributions (NDC) ของประเทศไทย",
        "BTS มีการตั้งเป้าหมาย climate แต่มีการวัดผลและมี pathway ไหม",
        "SCB มี climate อะไรบ้าง",
        "What is Thailand's clean energy policy?",
        "true มีนโยบาย Net Zero ของตัวเองไหม",
        "การเปลี่ยนแปลงสภาพภูมิอากาศกระทบต่อแผนพลังงานอย่างไร"
    ]

    # for i in queries:
    #     print(query_extractorV2(i))
    #     print("==")

    print(decompose_query("aav กับสิ่งแวดล้อมที่เกี่ยวข้องกับ policy มั้ยเปรียบเทียบกับ true"))
    # print(createTable(GetAllCompanies()))
    # print(query_extractorV1("bts"))
    # print(query_extractorV2("true มีการจัดการสิ่งแวดล้อมยังไงบ้าง และแตกต่างกับ aot มั้ย"))
    # print(createTable(GetAllCompanies()))
    # print(query_extractorV3("bts"))