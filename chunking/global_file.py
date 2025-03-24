import pdfplumber
from io import BytesIO
from langchain_text_splitters import RecursiveCharacterTextSplitter

def globalFileChunking(content:BytesIO | str, file_name:str, verbose=False, start_page:int=1):
    path = file_name.split("/")
    file = path[-1]

    with pdfplumber.open(content) as pdf:
        page_size = len(pdf.pages)
        if start_page < 0 or start_page > page_size:
            pdf.close()
            return "Faliure"
            
        if verbose:
            print("Start Chunk at page:", start_page)
            print("End Chunk at page:", page_size)

        buffer = []
        for i in range(start_page, page_size):
            p = pdf.pages[i]
            buffer.append(p.extract_text())
        pdf.close()

    chunk_size:int = 1000
    if page_size > 40:
        chunk_size = 1200

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="o200k_base", chunk_size=chunk_size, chunk_overlap=500
    )

    metadata = [{"file_name": file} for _ in buffer]
    text_chunks = text_splitter.create_documents(buffer, metadata)

    if verbose:
        print("Chunking Size:", len(text_chunks))

    return text_chunks

if __name__ == "__main__":
    chunks = globalFileChunking(start_page=7, verbose=True, content="/Users/peerasit/senior_project/STELLA-Backend/chunking/pdfs/general/th-nbsap-v4-th.pdf", file_name="th-nbsap-v4-th.pdf")
