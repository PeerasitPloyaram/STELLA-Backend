import pdfplumber
from langchain_core.documents import Document
import re
from io import BytesIO

def extract_tables(file_path:str, start: str, end: str)-> str:
    with pdfplumber.open(file_path) as pdf:
        page_size = len(pdf.pages)

        pages = []
        for index in range(1, page_size):
            p = pdf.pages[index].within_bbox(bbox=(0, 0, 595, 790))
            dat = p.extract_text()
            if re.findall(pattern=start, string=dat):
                pages.append(index)
            if re.findall(pattern=end, string=dat):
                pages.append(index)
                break
        
        buffer = ""
        for page in pages:
            p = pdf.pages[page].within_bbox(bbox=(0, 0, 595, 790))
            for line in p.extract_table():
                if line[0] != "":
                    head = line[0].replace("\n", " ")
                    if head[-1] != ":":
                        head += ":"
                    buffer += head + "\n" + line[1] + "\n\n"
                else:
                    buffer = buffer[:-1] + line[1] + "\n\n"
        pdf.close()
        return buffer

def ndcFileChunking(content:BytesIO | str, file_name:str)-> list[Document]:
    """
    Extract all text data and table in Nationally Determined Contribution: NDC file and chunking into chunk and create documents.

    with use hybrid chunking (Structure Chunking and Sematic Chunking)
    
    """
    
    if (type(content) is BytesIO) or (type(content) is str):
        pass
    else:
        return

    metadata_file_name = file_name.split("/")[-1]
    context = ""

    with pdfplumber.open(content) as pdf:
        page_size = len(pdf.pages)
        for index in range(1, page_size):
            p = pdf.pages[index].within_bbox(bbox=(0, 0, 595, 790))
            context += p.extract_text()

        start = "Accompanying information"
        end = "Consideration of fairness and ambition, in light of national circumstances and\ncontribution to the ultimate objective of the Convention \\(Article 2\\)"
        table = extract_tables(content, start, end)

        spliter_s =  context.split(end.replace("\\",""))
        end_postfix = end.replace("\\","")
        spliter_e = spliter_s[0].split(start)

        prefix = spliter_e[0] + start + table
        postfix = end_postfix + "\n" + spliter_s[1]

        context = prefix + postfix
        pdf.close()

    documents = []
    buffer = context.split("Accompanying information")
    doc1 = buffer[0]
    documents.append(doc1)

    doc = "Accompanying information" + buffer[1]
    buffer2 = doc.split("Consideration of fairness and ambition, in light of national circumstances and\ncontribution to the ultimate objective of the Convention (Article 2)")
    doc2 = buffer2[0]
    documents.append(doc2)

    buffer2[1].replace(".\n", ".\n\n")
    doc = buffer2[1].replace(".\n", ".\n\n").split("\n\n")
    doc[1] = "Consideration of fairness and ambition, in light of national circumstances and\ncontribution to the ultimate objective of the Convention (Article 2)" + doc[1]

    for i in doc[1:]:
        documents.append(i)


    documents_chunk = []
    for document in documents:
        documents_chunk.append(Document(page_content=document, metadata={"file_name": metadata_file_name}))

    return documents_chunk


if __name__ == "__main__":
    result = ndcFileChunking("/Users/peerasit/senior_project/STELLA-Backend/chunking/pdfs/general/Thailand_INDCs_2015.pdf", "/Users/peerasit/senior_project/STELLA-Backend/chunking/pdfs/general/Thailand_INDCs_2015.pdf")