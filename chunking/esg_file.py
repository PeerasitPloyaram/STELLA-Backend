import pdfplumber
import os, sys
import re
from langchain_core.documents import Document
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)+"./")))

sub_sector = [
    ["2.1 ขอบเขตการเปิดเผยการจัดการพลังงาน","2.2 ปริมาณการใช้ไฟฟ้าของบริษัท"],
    ["2.2 ปริมาณการใช้ไฟฟ้าของบริษัท", "2.3 ปริมาณการใช้ไฟฟ้าต่อหน่วยของบริษัท"],
    ["2.3 ปริมาณการใช้ไฟฟ้าต่อหน่วยของบริษัท","2.4 ค่าใช้จ่ายการใช้ไฟฟ้าของบริษัท"],
    ["2.4 ค่าใช้จ่ายการใช้ไฟฟ้าของบริษัท","2.5 ปริมาณการใช้น้ำมันและเชื้อเพลิงของบริษัท"],
    ["2.5 ปริมาณการใช้น้ำมันและเชื้อเพลิงของบริษัท","2.6 ค่าใช้จ่ายการใช้น้ำมันและเชื้อเพลิงของบริษัท"],
    ["2.6 ค่าใช้จ่ายการใช้น้ำมันและเชื้อเพลิงของบริษัท","2.7 ปริมาณการใช้พลังงานของบริษัท"],
    ["2.7 ปริมาณการใช้พลังงานของบริษัท","2.8 ปริมาณการใช้พลังงานต่อหน่วยของบริษัท"],
    ["2.8 ปริมาณการใช้พลังงานต่อหน่วยของบริษัท","3 การจัดการน้ำ"],

    ["3.1 ขอบเขตการเปิดเผยการจัดการน้ำ", "3.2 ปริมาณการใช้น้ำของบริษัท จำแนกตามแหล่งน้ำ"],
    ["3.2 ปริมาณการใช้น้ำของบริษัท จำแนกตามแหล่งน้ำ","3.3 ปริมาณน้ำทิ้งของบริษัท จำแนกตามแหล่งปล่อย"],
    ["3.3 ปริมาณน้ำทิ้งของบริษัท จำแนกตามแหล่งปล่อย","3.4 ปริมาณการใช้น้ำของบริษัท"],
    ["3.4 ปริมาณการใช้น้ำของบริษัท","3.5 ปริมาณการใช้น้ำต่อหน่วยของบริษัท"],
    ["3.5 ปริมาณการใช้น้ำต่อหน่วยของบริษัท","3.6 ค่าใช้จ่ายการใช้น้ำของบริษัท"],
    ["3.6 ค่าใช้จ่ายการใช้น้ำของบริษัท","4 การจัดการขยะและของเสีย"],
    
    # ["4 การจัดการขยะและของเสีย","4.1 ขอบเขตการเปิดเผยการจัดการขยะและของเสีย"],
    ["4.1 ขอบเขตการเปิดเผยการจัดการขยะและของเสีย", "4.2 ปริมาณขยะและของเสียของบริษัท"],
    ["4.2 ปริมาณขยะและของเสียของบริษัท", "4.3 ปริมาณขยะและของเสียที่นำไป Reuse/Recycle ของบริษัท"],
    ["4.3 ปริมาณขยะและของเสียที่นำไป Reuse/Recycle ของบริษัท", "5 การจัดการก๊าซเรือนกระจก"],

    # "5 การจัดการก๊าซเรือนกระจก",
    ["5.1 ขอบเขตการเปิดเผยการจัดการก๊าซเรือนกระจก","5.2 แผนการจัดการก๊าซเรือนกระจกของบริษัท"],
    # "5.2 แผนการจัดการก๊าซเรือนกระจกของบริษัท",
    ["5.3 ปริมาณการปล่อยก๊าซเรือนกระจกของบริษัท","5.4 ปริมาณการปล่อยก๊าซเรือนกระจกต่อหน่วยของบริษัท"],
    ["5.4 ปริมาณการปล่อยก๊าซเรือนกระจกต่อหน่วยของบริษัท","5.5 การทวนสอบปริมาณการปล่อยก๊าซเรือนกระจกของบริษัท"],
    ["5.5 การทวนสอบปริมาณการปล่อยก๊าซเรือนกระจกของบริษัท","5.6 ปริมาณการลดก๊าซเรือนกระจกของบริษัท"],
    ["5.6 ปริมาณการลดก๊าซเรือนกระจกของบริษัท","5.7 ปริมาณการดูดซับก๊าซเรือนกระจกของบริษัท"],
    ["5.7 ปริมาณการดูดซับก๊าซเรือนกระจกของบริษัท","ข้อมูลการดําเนินงานด้าน ESG"],

    ["2.1 ขอบเขตการเปิดเผยการปฏิบัติต่อแรงงานอย่างเป็นธรรม", "2.2.1 จำนวนพนักงาน จำแนกตามเพศ"],
    ["2.2.1 จำนวนพนักงาน จำแนกตามเพศ", "2.2.2 จำนวนพนักงาน จำแนกตามอายุ"],
    ["2.2.2 จำนวนพนักงาน จำแนกตามอายุ", "2.2.3 จำนวนพนักงานชาย จำแนกตามอายุ"],
    ["2.2.3 จำนวนพนักงานชาย จำแนกตามอายุ", "2.2.4 จำนวนพนักงานหญิง จำแนกตามอายุ"],
    ["2.2.4 จำนวนพนักงานหญิง จำแนกตามอายุ", "2.2.5 จำนวนพนักงาน จำแนกตามระดับตำแหน่ง"],
    ["2.2.5 จำนวนพนักงาน จำแนกตามระดับตำแหน่ง", "2.2.6 จำนวนพนักงานชาย จำแนกตามระดับตำแหน่ง"],
    ["2.2.6 จำนวนพนักงานชาย จำแนกตามระดับตำแหน่ง", "2.2.7 จำนวนพนักงานหญิง จำแนกตามระดับตำแหน่ง"],
    ["2.2.7 จำนวนพนักงานหญิง จำแนกตามระดับตำแหน่ง", '2.2.8 การจ้างงานผู้พิการ'],
    ["2.2.8 การจ้างงานผู้พิการ", "2.3.1 ค่าตอบแทนของพนักงาน จำแนกตามเพศ"],
    ["2.3.1 ค่าตอบแทนของพนักงาน จำแนกตามเพศ", "2.3.2 ข้อมูลเกี่ยวกับกองทุนสำรองเลี้ยงชีพพนักงาน"],
    ["2.3.2 ข้อมูลเกี่ยวกับกองทุนสำรองเลี้ยงชีพพนักงาน", "2.4 การพัฒนาพนักงาน"], 
    ["2.4.1 ชั่วโมงอบรมความรู้เฉลี่ยของพนักงาน", "2.4.2 ค่าใช้จ่ายในการอบรมความรู้และพัฒนาพนักงาน"],
    ['2.4.2 ค่าใช้จ่ายในการอบรมความรู้และพัฒนาพนักงาน', "2.5 ความปลอดภัย อาชีวอนามัย และสภาพแวดล้อมในการทำงานของพนักงาน"],
    ["2.5.1 จำนวนชั่วโมงการทำงาน", "2.5.2 สถิติการบาดเจ็บหรืออุบัติเหตุจากการทำงาน"],
    ["2.5.2 สถิติการบาดเจ็บหรืออุบัติเหตุจากการทำงาน", "2.6 การส่งเสริมความสัมพันธ์และการมีส่วนร่วมกับพนักงาน"],
    ["2.6.1 จำนวนพนักงานที่ลาออกโดยความสมัครใจ จำแนกตามเพศ", "\n"],
]

def extractfix(content: BytesIO | str):
    with pdfplumber.open(content) as pdf:
        page_size = len(pdf.pages)
        buffer = []

        next = []
        # for index in range(0,page_size):
        # p = pdf.pages[page]
        # t = p.search("5.7 ปริมาณการดูดซับก๊าซเรือนกระจกของบริษัท")
        # crop = p.within_bbox(bbox=(0, t[0]["top"], 595, 842))
        table = ""
        for i in range(0, page_size):
            p = pdf.pages[i]
            t = p.search("5.7 ปริมาณการดูดซับก๊าซเรือนกระจกของบริษัท")
            if t:
                crop = p.within_bbox(bbox=(0, t[0]["top"], 595, 842))
                table = crop.extract_tables()
        
        for i in table:
            if not i[0][0].startswith("ข้อมูล"):
                if i [0][0] != "รายละเอียด":
                    next = next + i
                else:
                    buffer.append(next)
                    next = i
        buffer.append(next)
        del(buffer[0])

        table_index = 0
        table_extraction = []
        for i in buffer:
            if table_index == 39:       # Limiter Table
                break
            count = 0
            buffer_table = "\nรายละเอียด:\n"
            for j in i[1:]:
                for index in range(0, len(j)):
                    if j[index] == None:
                        count += 1
                    else:
                        if j[index].isnumeric():
                            start_year = int(j[index])
                        break
                des = j[:count]
                data = j[count:]
                year_offset = start_year
                for d in data:
                    if des[0] != None:
                        about = des[0].replace("\n","")
                        if count > 1:
                            buffer_table += f"{about} (ปี{year_offset}): {d} {des[1].replace("\n", "").replace(" ","")}\n"
                        else:
                            buffer_table += f"{about} (ปี{year_offset}): {d}\n"
                    year_offset += 1
            buffer_table += "==========\n"
            table_extraction.append(buffer_table)
            table_index += 1
            # Cut and stop page 19
        pdf.close()
    return table_extraction[0]

def extractTable(content: BytesIO | str):
    with pdfplumber.open(content) as pdf:
        page_size = len(pdf.pages)
        buffer = []

        next = []
        for index in range(0,page_size):
            p = pdf.pages[index]
            d = p.extract_tables()
            
            for i in d:
                if not i[0][0].startswith("ข้อมูล"):
                    if i [0][0] != "รายละเอียด":
                        next = next + i
                    else:
                        buffer.append(next)
                        next = i
        buffer.append(next)
        del(buffer[0])

        table_index = 0
        table_extraction = []
        for i in buffer:
            if table_index == 39:       # Limiter Table
                break
            count = 0
            buffer_table = "\nรายละเอียด:\n"
            for j in i[1:]:
                for index in range(0, len(j)):
                    if j[index] == None:
                        count += 1
                    else:
                        if j[index].isnumeric():
                            start_year = int(j[index])
                        break
                des = j[:count]
                data = j[count:]
                year_offset = start_year
                for d in data:
                    if des[0] != None:
                        about = des[0].replace("\n","")
                        if count > 1:
                            buffer_table += f"{about} (ปี{year_offset}): {d} {des[1].replace("\n", "").replace(" ","")}\n"
                        else:
                            buffer_table += f"{about} (ปี{year_offset}): {d}\n"
                    year_offset += 1
            buffer_table += "==========\n"
            table_extraction.append(buffer_table)
            table_index += 1
            # Cut and stop page 19
        pdf.close()
    return table_extraction


def extractAll(content: BytesIO | str, verbose=False):
    table_extraction = extractTable(content=content)

    with pdfplumber.open(content) as pdf:
        page_size = len(pdf.pages)
        main_text = ""
        for index in range(0,page_size):
            p = pdf.pages[index]
            d = p.extract_text()
            main_text += d
    buffer = main_text
    sec5p2_start = "5.2 แผนการจัดการก๊าซเรือนกระจกของบริษัท" + buffer.split("5.2 แผนการจัดการก๊าซเรือนกระจกของบริษัท")[1]
    sec5p2_end = sec5p2_start.split("5.3 ปริมาณการปล่อยก๊าซเรือนกระจกของบริษัท")[0]
    
    soc = "ข้อมูลด้านสังคม" + buffer.split("ข้อมูลด้านสังคม")[1]
    soc_end = soc.split("2 การปฏิบัติต่อแรงงานอย่างเป็นธรรม")[0]


    count = 0
    for i in range(0, len(sub_sector)):
        sub_sec = buffer.split(sub_sector[i][0])
        if len(sub_sec) > 1:
            # Find Limiter

            # Limiter at end
            if i == len(sub_sector) - 1:
                # print("END", sub_sector[i][0])
                insider = sub_sec[1].split(sub_sector[i][1])
                if len(insider) > 1:
                    if verbose:
                        print(f"Table: {count} Found {sub_sector[i][0]}")
                        # print("Table:", count,len(sub_sec), "Found", sub_sector[i][0])
                    start = sub_sec[0] + sub_sector[i][0]
                    end = sub_sector[j][0] + insider[0]
                else:
                    if verbose:
                        print("Table:", count,len(sub_sec), "Found", sub_sector[i][0])
                    else:
                        pass

            # Limiter at start
            for j in range(i + 1, len(sub_sector)):
                insider = sub_sec[1].split(sub_sector[j][0])
                if len(insider) > 1:
                    if verbose:
                        print(f"Table: {count} Found {sub_sector[i][0]}")
                        # print("Found", "Table:", count,len(sub_sec), sub_sector[i][0])
                    tail = insider[1]
                    break
        else:
            if verbose:
                print(f"Table: {count} Not Found {sub_sector[i][0]}")
                # print("Not Found", "Table:", count,len(sub_sec), sub_sector[i][0])
            else:
                pass


        start = sub_sec[0] + sub_sector[i][0]
        # ddd = sub_sec[1]
        end = sub_sector[j][0] + tail

        if count < len(sub_sector) -1 :
            # print("|",sub_sector[i][1],"|")
            buffer = start + table_extraction[count] + end
        else:
            buffer = start + table_extraction[count]
        count += 1
    enviroment = buffer

    dd = enviroment.split("5.3 ปริมาณการปล่อยก๊าซเรือนกระจกของบริษัท")
    enviroment = dd[0] + sec5p2_end +"==========\n"  + "5.3 ปริมาณการปล่อยก๊าซเรือนกระจกของบริษัท" + dd[1]

    hj = enviroment.split("2.1 ขอบเขตการเปิดเผยการปฏิบัติต่อแรงงานอย่างเป็นธรรม")
    enviroment = hj[0] + soc_end + "==========\n" + "2 การปฏิบัติต่อแรงงานอย่างเป็นธรรม\n2.1 ขอบเขตการเปิดเผยการปฏิบัติต่อแรงงานอย่างเป็นธรรม" + hj[1]

    ee = enviroment.split("5.7 ปริมาณการดูดซับก๊าซเรือนกระจกของบริษัท")
    enviroment = ee[0] + "5.7 ปริมาณการดูดซับก๊าซเรือนกระจกของบริษัท" + extractfix(content=content) + "ข้อมูลด้านสังคม"+ee[1].split("ข้อมูลด้านสังคม")[1]


    with pdfplumber.open(content) as pdf:
        page_size = len(pdf.pages)
        buffer2 = ""

        for i in range(0, page_size):
            p = pdf.pages[i]
            buffer2 += p.extract_text()

        b = buffer2.split("ข้อมูลด้านบรรษัทภิบาลและเศรษฐกิจ")
        start = "ข้อมูลด้านบรรษัทภิบาลและเศรษฐกิจ" + b[1]
        eco = start.split("2 โครงสร้างการกำกับดูแลกิจการ")[0]
        sdg = "4นโยบายและกลยุทธ์ด้านความยั่งยืน" + b[1].split("นโยบายและกลยุทธ์ด้านความยั่งยืน")[1]

    return enviroment + eco + "\n==========\n" + sdg


def esgFileChunking(content: BytesIO | str,file_path:str, verbose=False):
    documents = []

    path = file_path.split("/")
    file_name = path[-1]
    company_name, file_type, year = file_name.split("_")

    buffer = extractAll(content=content, verbose=verbose)
    doc = buffer.split("\n==========\n")

    counter = 0
    s = ["ข้อมูลด้านสิ่งแวดล้อม", "ข้อมูลด้านสังคม", "ข้อมูลด้านบรรษัทภิบาลและเศรษฐกิจ"]
    section = ""

    file_metadata = {
        "file_name": file_name,
        "company_name": company_name,
        "file_type": "esg",
        "year": year.split(".",1)[0],
        "structured": True,
    }

    for i in doc:
        if re.findall(s[counter], i):
            section = s[counter]
            # print(section)
            # print([i])
            file_metadata["section"] = section
            if len(s) != counter + 1:
                counter += 1
        else:
            file_metadata["section"] = section
            # print(section)
            # print([i])

        documents.append(Document(
            page_content=i,
            metadata=file_metadata
        ))
    return documents


if __name__ == "__main__":
    file = "/Users/peerasit/senior_project/STELLA-Backend/chunking/pdfs/true_esg_2022.pdf"
    for i in (esgFileChunking(content=file, file_path=file, verbose=False)):
        print(i)

    # print(esgFileChunking(file_path=file, verbose=False))
