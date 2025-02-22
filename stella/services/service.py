from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from extraction.query_extractor import query_extractorV1, query_extractorV2
from db.service import findDataLoc

from chunking.ndc_file import ndcFileChunking
from chunking.one_report_file import oneReportFileChunking

load_dotenv()

def testLLM():
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


    rag_llm = ChatOpenAI(model="gpt-3.5-turbo",
            api_key=os.getenv("OPEN_AI_API_KEY"),
            temperature=0.7, max_tokens=4096)

    # Chain
    rag_chain = prompt | rag_llm | StrOutputParser()
    return rag_chain

    # out = rag_chain.invoke({"context": context, "question": user_input})
    # return out


# if __name__ == "__main__":
#     pass
    # print(stlQueryInput("bts คือ"))
    # print(loadGeneralFileToLlm())
    # print(stlUseGeneral("มีการตั้งเป้าหมาย climate แต่มีการวัดผลและมี pathway ไหม"))