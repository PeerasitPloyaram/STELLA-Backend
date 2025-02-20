from newmm_tokenizer.tokenizer import word_tokenize
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import pythainlp
import os
import sys
from dotenv import load_dotenv
sys.path.insert(0, "./")

from db.service import findDataLoc
load_dotenv()


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
    subquery_decomposition_template = """

    You are an AI assistant tasked with extracting company abbreviations in SET (Securities Exchange of Thailand) along with relevant years from a user query.
    Mapping each company's abbreviation to the correct years mentioned in the query.
    **** If a company is mentioned without a specific year, assume the latest available year (2023).

    **Instructions:**
    - Identify all company abbreviations in the user query.
    - Extract the years associated with each company.
    - If no year is explicitly mentioned, default to "2023".
    - Format the output as a string copany_name: year where the key is the company abbreviation (lowercase) and the value is a year devider with comma

    User-query: {user_query}

    **Examples:**

    User query: *How are BTS and AOT's incomes different in 2023?*  
    Output:
    bts:2023
    aot:2023

    **Examples:**

    User query: *Total income of scb in 2021 - 2023 compared to the latest aot*  
    Output:
    scb:2021,2022,2023
    aot:2023

    **Examples:**

    User query: what is bts
    Output:
    bts:2023

    *** If can't find company abbreviation return "NoCompanyName"
    """

    subquery_decomposition_prompt = PromptTemplate(
        input_variables=["user_query"],
        template=subquery_decomposition_template
    )

    subquery_decomposer_chain = subquery_decomposition_prompt | ChatOpenAI(model=os.getenv("OPEN_AI_MODEL_DECOM"), api_key=os.getenv("OPEN_AI_API_KEY"))

    response = subquery_decomposer_chain.invoke(user_query).content
    buffer = []
    # print(response)
    if response == "NoCompanyName" or (not response):
        return []
    # print(response)
    for q in response.split('\n'):
        line = q.strip()
        if not line.startswith("Output:"):
            if not line.startswith("NoCompanyName"):
                sp = line.split(":",1)
                name = sp[0]
                year = sp[1].split(",")

                buffer.append({
                    name: year
                })
    return buffer
    

def decompose_query(original_query: str):
    """
    Decompose the original query into simpler sub-queries.
    
    Args:
    original_query (str): The original complex query
    
    Returns:
    List[str]: A list of simpler sub-queries
    """

    subquery_decomposition_template = """
    You are an AI assistant tasked with breaking down complex queries about Company in SET: Securities Exchange of Thailand into simpler sub-queries for a RAG system.
    Given the original query, decompose it into 2-4 simpler sub-queries that, when answered together, would provide a comprehensive response to the original query.

    Original query: {original_query}

    example: What are the impacts of climate change on the environment?

    Sub-queries:
    1. What are the impacts of climate change on biodiversity?
    2. How does climate change affect the oceans?
    3. What are the effects of climate change on agriculture?
    4. What are the impacts of climate change on human health?

    *** Use same language as Original query
    """

    subquery_decomposition_prompt = PromptTemplate(
        input_variables=["original_query"],
        template=subquery_decomposition_template
    )

    subquery_decomposer_chain = subquery_decomposition_prompt | ChatOpenAI(model=os.getenv("OPEN_AI_MODEL_DECOM"), api_key=os.getenv("OPEN_AI_API_KEY"))

    response = subquery_decomposer_chain.invoke(original_query).content
    sub_queries = [q.strip() for q in response.split('\n') if q.strip() and not q.strip().startswith('Sub-queries:')]
    return sub_queries



if __name__ == "__main__":
    queries = [
        # "Does BTS have any risk regarding esg that is in line with the business?",
        # "นโยบาย INDC ของประเทศไทยคืออะไร?",
        # "What are Thailand's goals under the Paris Agreement?",
        # "How does Thailand plan to reduce greenhouse gas emissions?",
        # "การดำเนินงานของประเทศไทยภายใต้ UNFCCC เป็นอย่างไร?",
        # "INDC ของไทยช่วยลดโลกร้อนอย่างไร?",

        # "what is bts",
        # "เป้าหมาย Nationally Determined Contributions (NDC) ของประเทศไทย"
        # "BTS มีการตั้งเป้าหมาย climate แต่มีการวัดผลและมี pathway ไหม",
        # "SCB มี climate อะไรบ้าง",
        # "What is Thailand's clean energy policy?",
        # "BTS มีนโยบาย Net Zero ของตัวเองไหม",
        # "การเปลี่ยนแปลงสภาพภูมิอากาศกระทบต่อแผนพลังงานอย่างไร"
    ]

    # for i in queries:
        # print(query_extractorV2(i))

    # print(decompose_query("bts คือ"))
    # print(query_extractorV1("bts"))
    print(query_extractorV2("What is aav"))