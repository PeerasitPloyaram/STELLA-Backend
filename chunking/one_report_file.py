from extractor import extractPdf, createDocuments
from s56in1 import extractor56Section7V1


def oneReportFileChunking(file_name: str, verbose=False):
    """
    Extract all text data and table in one-report file and chunking into chunk then create documents.

    with use hybrid chunking (Structure Chunking and Sematic Chunking)
    """

    buffer = extractPdf(file_path=file_name)

    section7 = extractor56Section7V1(file_name, buffer['การกำกับดูแลกิจการ\nโครงสร้างการกำกับดูแลกิจการ\nและข้อมูลสำคัญเกี่ยวกับ\nคณะกรรมการ คณะกรรมการชุดย่อย ผู้บริหาร\nพนักงานและอื่นๆ'], verbose=verbose)
    buffer['การกำกับดูแลกิจการ\nโครงสร้างการกำกับดูแลกิจการ\nและข้อมูลสำคัญเกี่ยวกับ\nคณะกรรมการ คณะกรรมการชุดย่อย ผู้บริหาร\nพนักงานและอื่นๆ'] = section7

    documents = createDocuments(file_name, buffer)
    return documents

if __name__ == "__main__":
    result = oneReportFileChunking("/Users/peerasit/senior_project/STELLA-Backend/chunking/pdfs/aav_56-1_2023.pdf", verbose=True)
    print(result)