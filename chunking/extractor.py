import tiktoken
import pdfplumber
from langchain_core.documents import Document
import spacy
from transformers import AutoTokenizer
from typing import List
import re
from io import BytesIO

def gptCalToken(string: str, encoding_name: str="cl100k_base") -> int:
    # o200k_base for gpt-4o, gpt-4o-mini
    # cl100k_base gpt-4-turbo, gpt-4, gpt-3.5-turbo, text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def extractPdf(content:BytesIO | str):
    main_file = []
    with pdfplumber.open(content) as pdf:
        for page in pdf.pages:
            main_file.append(page.extract_text())
        pdf.close()

    m_sections = {
        'การประกอบธุรกิจและผลการดำเนินงาน\nโครงสร้างและการดำเนินงานของกลุ่มบริษัท' : ['ลักษณะการประกอบธุรกิจ (1.2)\n','นโยบายและภาพรวมการประกอบธุรกิจ (1.1)\n'],
        'การประกอบธุรกิจและผลการดำเนินงาน\nการบริหารจัดการความเสี่ยง' : ['ปัจจัยความเสี่ยงต่อการดำเนินธุรกิจของบริษัท (2.2)\n', 'นโยบายและแผนการบริหารความเสี่ยง (2.1)\n'],
        'การประกอบธุรกิจและผลการดำเนินงาน\nการขับเคลื่อนธุรกิจเพื่อความยั่งยืน' : ['การจัดการความยั่งยืนในมิติสังคม (3.4)\n', 'การจัดการด้านความยั่งยืนในมิติสิ่งแวดล้อม (3.3)\n', 'การจัดการผลกระทบต่อผู้มีส่วนได้เสียในห่วงโซ่คุณค่าของธุรกิจ (3.2)\n', 'นโยบายและเป้าหมายการจัดการด้านความยั่งยืน (3.1)\n'],
        'การกำกับดูแลกิจการ\nนโยบายการกำกับดูแลกิจการ' : ['การเปลี่ยนแปลงและพัฒนาการที่สำคัญของนโยบาย แนวปฏิบัติ และระบบการกำกับดูแลกิจการในรอบปี ที่ผ่านมา (6.3)\n', 'จรรยาบรรณธุรกิจ (6.2)\n', 'ภาพรวมของนโยบายและแนวปฏิบัติการกำกับดูแลกิจการ (6.1)\n'],
        'การกำกับดูแลกิจการ\nโครงสร้างการกำกับดูแลกิจการ\nและข้อมูลสำคัญเกี่ยวกับ\nคณะกรรมการ คณะกรรมการชุดย่อย ผู้บริหาร\nพนักงานและอื่นๆ': ['ข้อมูลสำคัญอื่นๆ (7.6)\n', 'ข้อมูลเกี่ยวกับพนักงาน (7.5)\n', 'ข้อมูลเกี่ยวกับผู้บริหาร (7.4)\n', 'ข้อมูลเกี่ยวกับคณะกรรมการชุดย่อย (7.3)\n', 'ข้อมูลเกี่ยวกับคณะกรรมการ (7.2)\n', 'โครงสร้างการกำกับดูแลกิจการ (7.1)\n'],
        'การกำกับดูแลกิจการ\nรายงานผลการดำเนินงานสำคัญ\nด้านการกำกับดูแลกิจการ' : ['สรุปผลการปฏิบัติหน้าที่ของคณะกรรมการชุดย่อยอื่นๆ (8.3)\n', 'รายงานผลการปฏิบัติหน้าที่ของคณะกรรมการตรวจสอบในรอบปีที่ผ่านมา (8.2)\n', 'สรุปผลการปฏิบัติหน้าที่ของคณะกรรมการในรอบปีที่ผ่านมา (8.1)\n'],
        'การกำกับดูแลกิจการ\nการควบคุมภายในและรายการระหว่างกัน' : ['รายการระหว่างกัน (9.2)\n', 'สรุปผลการปฏิบัติหน้าที่ของคณะกรรมการในรอบปีที่ผ่านมา (8.1)\n'],
    }

    buffer = {}
    current_section = None
    for d in main_file[2:len(main_file)]:
        for section in m_sections:
            if section in d:
                current_section = section
                buffer[section] = ""
                break

        if current_section:
            d = d + '[END_PAGE]'
            buffer[current_section] += d


    m_buffer = {}
    def cut_paragraph(text_input:str, dict_input):
        split = dict_input.split(text_input)
        if len(split) > 1:
            split[1] = text_input + split[1]
        return split

    for m_section in m_sections:
        sub_section_chunks = []     # Chunk For Storage Sub Section
        chunk_buffer = []           # Chunk Buffer During Segmentation

        if m_section in buffer:
            paragraph = buffer[m_section].replace(m_section + '[END_PAGE]', "")
        else:
            continue

        for sub in m_sections[m_section]:
            if chunk_buffer == []:
                chunk_buffer = paragraph

            a = cut_paragraph(sub, chunk_buffer)
            if len(a) > 1:
                sub_section_chunks.insert(0, a[1])
            
            chunk_buffer = a[0]

        m_buffer[m_section] = sub_section_chunks
        sub_section_chunks = []                     # Clear Chunk

    return m_buffer



nlp = spacy.blank("th")
nlp.add_pipe("sentencizer")
tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2")

def split_large_sentence(sentence: str, max_tokens: int) -> List[str]:
    words = sentence.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        token_count = gptCalToken(word)
        
        if current_length + token_count > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = token_count
        else:
            current_chunk.append(word)
            current_length += token_count

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def semantic_chunking(text: str, max_tokens: int = 1524) -> List[str]:
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        token_count = gptCalToken(sentence)
        
        if re.match(r'\d+\.\s', sentence):
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [sentence]
            current_length = token_count
            continue
        
        if token_count > max_tokens:
            smaller_chunks = split_large_sentence(sentence, max_tokens)
            for chunk in smaller_chunks:
                chunks.append(chunk)
            continue

        if current_length + token_count > max_tokens:
            chunks.append("\n".join(current_chunk))
            current_chunk = [sentence]
            current_length = token_count
        else:
            current_chunk.append(sentence)
            current_length += token_count

    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks

def split_text_by_n_occurrence(text):
    buffer = ""
    result = []
    t = text.split("-----\n")
    counter = 0

    for index in range(0, len(t)):
        if re.search(r"^ข้อมูลทั่วไป", t[index]):
            buffer += t[index]
            counter += 1
        else:
            if buffer != "":
                result.append(buffer)
                result.append(t[index])
                buffer = ""
            else:
                result.append(t[index])

            counter = 0
        if counter == 3:
            result.append(buffer)
            buffer = ""
            counter = 0
    
    return result


def createDocuments(file_path: str, text):
    path = file_path.split("/")
    file_name = path[-1]
    company_name, file_type, year = file_name.split("_")

    company_name = company_name.upper()
    year = year.split(".")[0]

    documents = []

    # print(file_name)
    metadata = {
        "file_name": file_name,
        "company_name": company_name,
        "file_type": file_type,
        "year": year,
        "structured": True,
    }

    for key in text:
        section = key.split("\n",1)[1]
        file_metadata = metadata
        file_metadata["section"] = section

        for data in text[key]:
            # print("SEC", section)
            sub_section = data.split("\n", 1)[0]
            # print("SUB", sub_section)
            metadata["sub_section"] = sub_section

            # 7
            if (section == "โครงสร้างการกำกับดูแลกิจการ\nและข้อมูลสำคัญเกี่ยวกับ\nคณะกรรมการ คณะกรรมการชุดย่อย ผู้บริหาร\nพนักงานและอื่นๆ"):            
                for i in split_text_by_n_occurrence(data):
                    # print([i])
                    document = Document(
                        page_content=i,
                        metadata=file_metadata
                    )
                    documents.append(document)
                # print("\n")

            # 1, 2, 3, 6, 8
            else:
                # pass
                for i in semantic_chunking(data):
                    document = Document(
                        page_content=i,
                        metadata=file_metadata
                    )
                    documents.append(document)
                    # print([i])
                    # print(gptCalToken(i))
                # print("\n")
        # print("====")
    return documents