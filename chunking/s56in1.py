import pdfplumber
import pandas as pd
from io import BytesIO

def extract_table(content:BytesIO | str, config: dict[str, any]) -> str:
    """
    file_name: name,
    config:
    {
        'search': {'search_string': [1,2,3]},
        'name_col': ['ข้อมูลทั่วไป', 'ตำแหน่งของกรรมการ', 'ระยะเวลาดำรงตำแหน่ง', 'กรรมการที่มาดำรงตำแหน่งแทน']
    }
    """

    def compute(tables, columns_names):
        buffer = ""
        if len(tables[0][0]) == 3:
            columns = [0, 1, 2]
        else:
            columns = [0, 1, 2, 3]

        # if tables[0][0][0] == "ข้อมูลทั่วไป":
        if tables[0][0][0] == config["name_col"][0]:
            update_tables = tables[0][1:]
        else:
            update_tables = tables[0]
        
        df = pd.DataFrame(data=update_tables, columns=columns)
        for index, row in df.iterrows():
            buffer += f"{columns_names[0]}:\n {row[0]}\n\n{columns_names[1]}:\n {row[1]}\n\n{columns_names[2]}:\n {row[2]}"
            if len(tables[0][0]) != 3:
                buffer += f"\n\n{columns_names[3]}:\n {row[3]}\n-----\n"
            else:
                buffer += "\n-----\n"
        
        return buffer

    with pdfplumber.open(content) as pdf:
        buffers = ""
        for s, page in config[list(config.keys())[0]].items():
            name_col = config["name_col"]

            p = pdf.pages[page[0] - 1]
            focus = p.search(s)
            # print(s, "In Page:", page[0] - 1)
            if focus:
                # print("FOUND")
                # print("START EXTRACT Page:", page[0] - 1)
                p = p.within_bbox(bbox=(0, focus[0]["top"], 595, 842))
                tables = p.extract_tables()
                buffers += compute(tables, name_col)
            else:
                # print("NOT FOUND")
                # print("REVERSE")
                # print(page[0]-2)
                p = pdf.pages[page[0] - 2]
                focus = p.search(s)
                # print(focus)
                # print("START EXTRACT Page:", page[0] - 1)
                p = pdf.pages[page[0] - 1]
                # print(p.find_table())
                p = p.within_bbox(bbox=(0, 0, 595, 842))
                tables = p.extract_tables()
                buffers += compute(tables, name_col)

            for i in page[1:]:
                # print("MOVE EXTRACT Page:", i - 1)
                p = pdf.pages[i - 1]
                # print(p.find_table())
                tables = p.extract_tables()
                buffers += compute(tables, name_col)

        return buffers



def extractor56Section7V1(content:BytesIO | str, section_data: dict, verbose=False) -> list:
    
    def compute_struct(nav: list[dict[str, any]], input) -> str:
        final = input
        for index in range(0, len(nav)):
            start = final.split(nav[index]["replace_start"])
            if len(start) > 1:
                end = start[1].split(nav[index]["replace_end"])
            else:
                end = start[0].split(nav[index]["replace_end"])
            a = start[0] + nav[index]["replace_start"] + "\n"
            nav_mapping = {key: nav[index][key] for key in ["search", "name_col"]}
            b = extract_table(content=content, config=nav_mapping)

            if len(end) > 1:
                c = nav[index]["replace_end"] + end[1] + "\n"
            else:
                c = nav[index]["replace_end"] + end[0] + "\n"
            final = a + b + c
        return final


    def generateNav(content:BytesIO | str):
        navs = []
        def compute_nav(cut_start, cut_end):
            with pdfplumber.open(content) as pdf:        
                enable = True
                finals_pages = []
                for pointer in range(0, len(cut_start)):
                    pages_nav = []
                    for page_index in range(0, len(pdf.pages)):
                        if pdf.pages[page_index].search(cut_start[pointer]) and enable:
                            # print("start page",page_index + 1, cut_start[pointer])
                            enable = False

                            if pdf.pages[page_index].search(cut_end[pointer]):
                                # print("  end page in start", page_index + 1, cut_end[pointer])
                                enable = True
                                pages_nav.append(page_index + 1)
                                continue

                        if pdf.pages[page_index].search(cut_end[pointer]):
                            # print("  end page", page_index + 1, cut_end[pointer])
                            enable = True
                            p = pdf.pages[page_index]
                            focus = p.search(cut_end[pointer])                              # Search Tail Cut
                            # print(focus)
                            crop_page = p.within_bbox(bbox=(0, 0, 595, focus[0]["bottom"])) # Crop to Find Table

                            if (crop_page.find_table()):                # Found Table Over Tail Cut
                                pages_nav.append(page_index + 1)         # Add Page If Found

                        elif not enable:
                            p = pdf.pages[page_index]
                            focus = p.search(cut_start[pointer])
                            # print("  table", page_index + 1)
                            if focus:
                                crop_page = p.within_bbox(bbox=(0, focus[0]["top"] + 50, 595, 842))
                                if crop_page.find_table():
                                    pages_nav.append(page_index + 1)
                            else:
                                pages_nav.append(page_index + 1)
                    sol = {
                        "pages": pages_nav,
                        "start": cut_start[pointer],
                        "end": cut_end[pointer]
                    }
                    finals_pages.append(sol)

                return finals_pages
                    

        def compute_dynamic_page():
            commitee_list = [
                "รายชื่อกรรมการตรวจสอบชุดปัจจุบัน",
                "รายชื่อกรรมการตรวจสอบที่ลาออก/พ้นจากตำแหน่งระหว่างปี",
                "รายชื่อกรรมการบริหารชุดปัจจุบัน",
                "รายชื่อกรรมการบริหารที่ลาออก/พ้นตำแหน่งระหว่างปี",
                "คณะกรรมการชุดย่อยอื่นๆ"
            ]

            with pdfplumber.open(content) as pdf:
                found = False
                finals_pages = []
                for i in range(0, len(commitee_list)):
                    for j in range(0, len(commitee_list)):
                        if found:
                            found = False
                            break

                        start = commitee_list[i]
                        end = commitee_list[j]
                        page_nav = []
                        enable = True
                        start_found = False
                        end_found = False

                        for page_index in range(0, len(pdf.pages)):
                            if pdf.pages[page_index].search(start) and enable:
                                start_found = True
                                enable = False
                                if pdf.pages[page_index].search(end):
                                        end_found = True
                                        enable = True
                                        page_nav.append(page_index + 1)
                                        continue
                            
                            if pdf.pages[page_index].search(end):
                                end_found = True
                                enable = True
                                p = pdf.pages[page_index]
                                focus = p.search(end)
                                crop_page = p.within_bbox(bbox=(0, 0, 595, focus[0]["bottom"]))
                                if crop_page.find_table():
                                    page_nav.append(page_index + 1)
                            elif not enable:
                                p = pdf.pages[page_index]
                                focus = p.search(start)
                                if focus:
                                    crop_page = p.within_bbox(bbox=(0, focus[0]["top"] + 100, 595, 842))
                                    if crop_page.find_table():
                                        page_nav.append(page_index + 1)
                        
                        if page_nav:
                            if not (page_nav[-1] == len(pdf.pages)):
                                if (start_found and end_found) and i < j:
                                    found = True
                            else:
                                found = False
                        if found:
                            sol = {
                                "pages": page_nav,
                                "start": start,
                                "end": end
                            }
                            finals_pages.append(sol)
                pdf.close()
                return finals_pages
            
        def compute_dynamic_pageV2():
            commitee_list = [
                "รายชื่อกรรมการชุดปัจจุบัน",
                "รายชื่อกรรมการที่ลาออก/พ้นจากตำแหน่งระหว่างปี",
                "ข้อมูลเกี่ยวกับคณะกรรมการอื่นๆ"
            ]

            with pdfplumber.open(content) as pdf:
                found = False
                finals_pages = []
                for i in range(0, len(commitee_list)):
                    for j in range(0, len(commitee_list)):
                        if found:
                            found = False
                            break

                        start = commitee_list[i]
                        end = commitee_list[j]
                        page_nav = []
                        enable = True
                        start_found = False
                        end_found = False

                        for page_index in range(0, len(pdf.pages)):
                            if pdf.pages[page_index].search(start) and enable:
                                # print("START", pdf.pages[page_index], pdf.pages[page_index].search(start))
                                # print("FOUND")
                                start_found = True
                                enable = False
                                if pdf.pages[page_index].search(end):
                                        end_found = True
                                        enable = True
                                        page_nav.append(page_index + 1)
                                        continue
                            
                            if pdf.pages[page_index].search(end):
                                # print("END",pdf.pages[page_index], pdf.pages[page_index].search(end))
                                # print("FOUND END")
                                end_found = True
                                enable = True
                                p = pdf.pages[page_index]
                                focus = p.search(end)
                                crop_page = p.within_bbox(bbox=(0, 0, 595, focus[0]["bottom"]))
                                if crop_page.find_table():
                                    page_nav.append(page_index + 1)
                            elif not enable:
                                p = pdf.pages[page_index]
                                focus = p.search(start)
                                # print("CON", focus)
                                if focus:
                                    crop_page = p.within_bbox(bbox=(0, focus[0]["top"] + 50, 595, 842))
                                    if crop_page.find_table():
                                        page_nav.append(page_index + 1)
                                else:
                                    page_nav.append(page_index + 1)
                        
                        if page_nav:
                            if not (page_nav[-1] == len(pdf.pages)):
                                if (start_found and end_found) and i < j:
                                    found = True
                            else:
                                found = False
                        if found:
                            sol = {
                                "pages": page_nav,
                                "start": start,
                                "end": end
                            }
                            finals_pages.append(sol)
                pdf.close()
                return finals_pages
        
        def createNav(cut_start, cut_end, col):
            result = compute_nav(cut_start, cut_end)
            nav = []
            for i in result:
                nav.append({
                    "search": {i["start"].replace("\\",""): i["pages"]},
                    "name_col": col,
                    "replace_start": i["start"].replace("\\",""),
                    "replace_end": i["end"].replace("\\",""),
                })
            return nav


        # ======================================
        # 2 Possible way
        #   1. layoff
        #   2. no layoff

        # col = ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "วันเริ่มดำรงตำแหน่ง", "ประสบการณ์และความชำนาญ"]
        # cut_start = ["รายชื่อกรรมการชุดปัจจุบัน"]
        # cut_end = ["รายชื่อกรรมการที่ลาออก/พ้นจากตำแหน่งระหว่างปี"]
        # b = createNav(cut_start, cut_end, col)

        # col = ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "ระยะเวลาดำรงตำแหน่ง", "กรรมการที่มาดำรงตำแหน่งแทน"]
        # cut_start = ["รายชื่อกรรมการที่ลาออก/พ้นจากตำแหน่งระหว่างปี"]
        # cut_end = ["ข้อมูลเกี่ยวกับคณะกรรมการอื่นๆ"]
        # c = createNav(cut_start, cut_end, col)
        # print(b[0])
        # print(c[0])
        # navs.append([b[0], c[0]])
        # print(compute_dynamic_pageV2())

        bbuffer = []
        for i in compute_dynamic_pageV2():
            if i["start"] == "รายชื่อกรรมการชุดปัจจุบัน":
                bbuffer.append(createNav([i["start"]], [i["end"]], ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "วันเริ่มดำรงตำแหน่ง", "ประสบการณ์และความชำนาญ"])[0])
            elif i["start"] == "รายชื่อกรรมการที่ลาออก/พ้นจากตำแหน่งระหว่างปี":
                bbuffer.append(createNav([i["start"]], [i["end"]], ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "ระยะเวลาดำรงตำแหน่ง", "กรรมการที่มาดำรงตำแหน่งแทน"])[0])
        navs.append(bbuffer)
        # print(bbuffer)
        # ====== 


        buffer = []
        for i in compute_dynamic_page():
            # print(i)
            if i["start"] == "รายชื่อกรรมการตรวจสอบชุดปัจจุบัน":
                buffer.append(createNav([i["start"]], [i["end"]], ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "วันเริ่มดำรงตำแหน่ง", "ประสบการณ์และความชำนาญ"])[0])
            elif i["start"] == "รายชื่อกรรมการตรวจสอบที่ลาออก/พ้นจากตำแหน่งระหว่างปี":
                buffer.append(createNav([i["start"]], [i["end"]], ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "ระยะเวลาดำรงตำแหน่ง", "กรรมการที่มาดำรงตำแหน่งแทน"])[0])
            elif i["start"] == "รายชื่อกรรมการบริหารชุดปัจจุบัน":
                buffer.append(createNav([i["start"]], [i["end"]], ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "วันเริ่มดำรงตำแหน่ง"])[0])
            elif i["start"] == "รายชื่อกรรมการบริหารที่ลาออก/พ้นตำแหน่งระหว่างปี":
                buffer.append(createNav([i["start"]], [i["end"]], ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ","ระยะเวลาดำรงตำแหน่ง", "กรรมการที่มาดำรงตำแหน่งแทน"])[0])
        
        navs.append(buffer)


        col = ["ชื่อของคณะกรรมการชุดย่อย", "รายชื่อกรรมการ", "ตำแหน่ง"]
        cut_start = ["คณะกรรมการชุดย่อยอื่นๆ\nข้อมูลคณะกรรมการชุดย่อย"]
        cut_end = ["บทบาทหน้าที่ของคณะกรรมการชุดย่อย"]
        d = createNav(cut_start, cut_end, col)
        navs.append(d)



        col = ["ข้อมูลทั่วไป", "ตำแหน่งของกรรมการ", "วันเริ่มดำรงตำแหน่ง", "ประสบการณ์และความชำนาญ"]
        cut_start = ["รายชื่อผู้บริหารสูงสุดและผู้บริหาร 4 รายแรกนับจากผู้บริหารสูงสุด"]
        cut_end = ["นโยบายการจ่ายค่าตอบแทนผู้บริหาร \\(7\\.4\\.2 - 7\\.4\\.3\\)"]
        e = createNav(cut_start, cut_end, col)
        # print(d)
        navs.append(e)

        return navs

    def extract_etc_commitee(file_name, page_num):
        with pdfplumber.open(file_name) as pdf:
            page = pdf.pages[page_num - 1]
            table = page.extract_table(table_settings={
                "vertical_strategy": "lines", 
                "horizontal_strategy": "lines", 
                "snap_tolerance": 3
            })

        buffers = ""
        for col in table[1:]:
            commitee = col[0]
            name_committee = col[1].split('\n')
            pos = col[2].split('\n')

            buffers += f"{table[0][0]}: {commitee.replace("\n", "")}\n"
            buffers += f"{table[0][1]}:\n"
            for i in range(0, len(name_committee)):
                buffers += f"{i+1}. {name_committee[i]} {table[0][2]}: {pos[i]}\n"
            buffers += "-----\n"
        return buffers

    # def extract_etc_commiteev2(file_name, page_num):
    #     buffers = ""
    #     for p in page_num:
    #         with pdfplumber.open(file_name) as pdf:
    #             page = pdf.pages[p - 1]
    #             # print(page.find_table())
    #             table = page.extract_table(table_settings={
    #                 "vertical_strategy": "lines", 
    #                 "horizontal_strategy": "lines", 
    #                 "snap_tolerance": 3
    #             })
    #             # print(table[0][0])
    #             # commitee = ""
    #             name_committee = ""
    #             pos = ""
    #             if table[0][0] == "ชื่อของคณะกรรมการชุดย่อย":
    #                 for col in table[1:]:
    #                     commitee = col[0]
    #                     name_committee = col[1].split('\n')
    #                     pos = col[2].split('\n')

    #                     buffers += f"{"ชื่อของคณะกรรมการชุดย่อย"}: {commitee.replace("\n", "")}\n"
    #                     buffers += f"{"รายชื่อกรรมการ"}:\n"
    #                     for i in range(0, len(name_committee)):
    #                         buffers += f"{i+1}. {name_committee[i]} {table[0][2]}: {pos[i]}\n"
    #                     buffers += "-----\n"
    #             else:
    #                 pos = table[0][2].split('\n')
    #                 name_committee = table[0][1].split('\n')
    #                 buffers += f"{"ชื่อของคณะกรรมการชุดย่อย"}:{table[0][0]}\n"
    #                 buffers += f"{"รายชื่อกรรมการ"}:\n"
    #                 for i in range(0, len(name_committee)):
    #                     buffers += f"{i+1}. {name_committee[i]} {"ตำแหน่ง"}:{pos[i]}\n"
    #                 buffers += "-----\n"
    #     return buffers

    def extract_etc_commiteev2(content:BytesIO | str, page_num):
        buffers = ""
        for p in page_num:
            with pdfplumber.open(content) as pdf:
                page = pdf.pages[p - 1]
                # print(page.find_table())
                table = page.extract_table(table_settings={
                    "vertical_strategy": "lines", 
                    "horizontal_strategy": "lines", 
                    "snap_tolerance": 3
                })

                # print(table[0])
                name_committee = ""
                pos = ""
                if table[0][0] == "ชื่อของคณะกรรมการชุดย่อย":
                    for col in table[1:]:
                        commitee = col[0]
                        name_committee = col[1].split('\n')
                        pos = col[2].split('\n')

                        buffers += f"{"ชื่อของคณะกรรมการชุดย่อย"}: {commitee.replace("\n", "")}\n"
                        buffers += f"{"รายชื่อกรรมการ"}:\n"
                        for i in range(0, len(name_committee)):
                            buffers += f"{i+1}. {name_committee[i]} {table[0][2]}: {pos[i]}\n"
                        buffers += "-----\n"
                else:
                    for col in table:
                        pos = col[2].split('\n')
                        name_committee = col[1].split('\n')
                        buffers += f"{"ชื่อของคณะกรรมการชุดย่อย"}:{col[0]}\n"
                        buffers += f"{"รายชื่อกรรมการ"}:\n"
                        # print(name_committee)
                        for i in range(0, len(name_committee)):
                            buffers += f"{i+1}. {name_committee[i]} {"ตำแหน่ง"}:{pos[i]}\n"
                        buffers += "-----\n"
        return buffers

    def extractorSec7(navs, data):
        bu = []
        offset = 0
        for i in range(0, len(navs)):
            # print(i)
            # print(navs[i])
            if list(navs[i][0]["search"].keys())[0] == "คณะกรรมการชุดย่อยอื่นๆ\nข้อมูลคณะกรรมการชุดย่อย":
                final = compute_struct(navs[i-1], bu[i-1])

                # ======
                #  page in 7.3 [23] not dynamic
                # ======
                page = list(navs[i][0]["search"].items())[0][1]
                # print((navs[i][0]))
                # print(page)
                a = "คณะกรรมการชุดย่อยอื่นๆ\nข้อมูลคณะกรรมการชุดย่อย"
                # b = extract_etc_commitee(file_name, page[0])
                b = extract_etc_commiteev2(content, page)

                replace_start = "ข้อมูลคณะกรรมการชุดย่อย"
                replace_end = "บทบาทหน้าที่ของคณะกรรมการชุดย่อย"

                start = final.rsplit(replace_start, 1)
                end = start[1].split(replace_end)
                c = replace_end + end[1]
                dfs = a + b + c
                # print(dfs)
                # bu.append(dfs)

                jj = final.split("คณะกรรมการชุดย่อยอื่นๆ")
                jjj = jj[0] + dfs
                bu[i-1] = (jjj)
                # print(i-1)
                offset += 1
                
                
            else:
                # print(i - offset)
                an = compute_struct(navs[i],data[i - offset])
                bu.append(an)
        return bu

    # Generate Navigations for Extractor Extract Data
    navs = generateNav(content)
    if verbose:
        print("Navigations for Extract Data:")
        for i in navs:
            for j in i:
                print(j)


    # Extract Subsection 7.2 - 7.4
    section7 = extractorSec7(navs, section_data)
    for i in range(0, len(section7)):
        section7[i] = section7[i].replace("รายชื่อกรรมการบริหารชุดปัจจุบัน", "คณะกรรมการบริหาร\nรายชื่อกรรมการบริหารชุดปัจจุบัน")
        section7[i] = section7[i].replace("คณะกรรมการชุดย่อยอื่นๆ\nข้อมูลคณะกรรมการชุดย่อย","คณะกรรมการชุดย่อยอื่นๆ\nข้อมูลคณะกรรมการชุดย่อย\n")

    # Extract Subsection 7.5
    for i in range(3, len(section_data)):
        section7.append(section_data[i])

    return section7