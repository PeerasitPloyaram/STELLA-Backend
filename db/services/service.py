import mariadb
from pymilvus import connections, MilvusClient, Collection
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/")
sys.path.insert(0, "/Users/peerasit/senior_project/STELLA-Backend/db/")

from milvus.schema import INDEX_PARAMS, DATA_SOURCE_SCHEMA
from services.vector_data import (
    updateVectorFrontendNodeGeneral,
    deleteVectorFrontendNodeGeneral,
    deleteVectorGeneral,
    deleteVectorCompany,
    deleteVectorEachCompanyFile
)

load_dotenv()
connection = mariadb.connect(
    user=os.getenv("DB_CLIENT_USER"),
    password=os.getenv("DB_CLIENT_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv('DB_DATABASE_NAME')
)

client = MilvusClient(db_name=os.getenv("MILVUS_DATABASE_NAME"))


# Create New Location Storage of Collection name and Partition name
def createNewLocStorage(collection_name:str, partition_name:str):
    sql = "INSERT INTO location_storages (collection_name, partition_name) VALUES (%s, %s)"
    values = (collection_name, partition_name)

    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()
    return cursor.lastrowid

#  Insert Data Related About company
def insertCompanyData(sector_id:int, abbr:str, collection_name: str, partition_name: str, company_name_th=None, company_name_en=None)-> None:
    sql = """INSERT INTO companies (abbr, is_active, sector_id, location_storage_id, company_name_th, company_name_en)
    VALUES (%s, %d, %d, %d, %s, %s)
    """

    name_th_insert = None
    name_en_insert = None
    if company_name_th != None:
        name_th_insert = company_name_th
    if company_name_en != None:
        name_en_insert = company_name_en

    # try:
    loc_id = createNewLocStorage(collection_name=collection_name, partition_name=partition_name)
    values = (abbr, 1, sector_id, loc_id, name_th_insert, name_en_insert)
    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()
    print("[DB] Commit new Company")
    
    return cursor.lastrowid

def getCompanyId(name:str):
    sql = f"""
    SELECT company_id FROM companies WHERE companies.abbr = "{name}";
    """
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchone()
    if not res:
        return
    return res[0]

def getCompanyLocation(name:str):
    sql = f"""
    SELECT ls.collection_name, ls.partition_name, ls.location_storage_id FROM companies c
    JOIN location_storages ls ON c.location_storage_id = ls.location_storage_id
    WHERE c.abbr = '{name}';
    """

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchone()
    if not res:
        return
    
    return {"collection_name": res[0], "partition_name": res[1], "storage_id": res[2]}

def getALLSQLCompanyDataFile(company_abbr: str):
    sql = """
    SELECT cf.file_id, cf.file_name, cf.file_type FROM company_files cf
    JOIN companies c ON cf.company_id = c.company_id
    WHERE c.abbr = %s;
    """
    
    cursor = connection.cursor()
    cursor.execute(sql, (company_abbr,))
    files = cursor.fetchall()
    
    if not files:
        return []
    
    return [{"id": file[0], "file_name": file[1], "file_type": file[2]} for file in files]

def getAllCompaniesInfo()-> list:
    sql = """
    SELECT companies.abbr, companies.company_name_th, companies.company_name_en, sectors.sector_name
    FROM companies
    JOIN sectors ON sectors.sector_id = companies.sector_id
    WHERE companies.is_active = 1;
    """
    data = []
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    for c in buffer:
        data.append({"abbr":c[0], "name_th":c[1], "name_en":c[2], "sector":c[3]})
    return data

def getALLAbbrCompany()-> list:
    sql = f"SELECT companies.abbr FROM companies WHERE is_active = 1"

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    return [c[0] for c in buffer]

def GetAllCompanies():
    sql = f"SELECT companies.abbr, companies.company_name_th, companies.company_name_en FROM companies WHERE is_active = 1"
    
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    return buffer


def addSQLCompanyDataFile(company_id:str, file_name:str, file_type:str):
    sql = f"""
    INSERT INTO company_files (file_name, file_type, company_id) VALUES ("{file_name}", "{file_type}", "{company_id}");
    """
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    connection.commit()

def findSQLComapnyDataFile(company_id:str, file_name:str):
    sql = f"""
    SELECT file_name FROM company_files WHERE (company_files.file_name = "{file_name}" AND company_files.company_id = "{company_id}");
    """
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchone()
    if not res:
        return False
    return True

def deleteSQLCompanyData(name_abbr:str):
    sql = f"""
    DELETE FROM companies WHERE (abbr = "{name_abbr}");
    """
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    connection.commit()

# Delete Company FIle Data in SQL and Vector
def deleteCompanyData(name:str):
    res:dict = getCompanyLocation(name=name)
    if not res:
        return
    
    company_id:str = getCompanyId(name=name)
    deleteVectorCompany(collection=res["collection_name"], partition=res["partition_name"])
    deleteSQLCompanyFile(company_id=company_id)
    deleteSQLCompanyData(name_abbr=name)
    deleteLocationStorage(id=res["storage_id"])

def deleteSQLCompanyFile(company_id:str):
    sql = f"""
    DELETE FROM company_files WHERE (company_id = "{company_id}");
    """
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    connection.commit()

def deleteSQLEachCompanyFile(file_name:str):
    sql = f"""
    DELETE FROM company_files WHERE (file_name = "{file_name}");
    """
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    connection.commit()

# Delete General FIle Data in SQL and Vector
def deleteGeneralFile(name:str):
    location:dict = getDocumentLocation(name=name)
    if not location:
        return

    deleteVectorGeneral(collection=location["collection_name"], partition=location["partition_name"])
    deleteVectorFrontendNodeGeneral(file_name=name)

    deleteSQLGeneralData(name=name)
    deleteLocationStorage(id=location['storage_id'])


def insertGeneralData(document_name:str, description:str, collection_name: str, partition_name: str)-> None:
    sql = """INSERT INTO documents (document_name, description, is_active, location_storage_id)
    VALUES (%s, %s, %d, %d)
    """
    # try:
    loc_id = createNewLocStorage(collection_name=collection_name, partition_name=partition_name)
    values = (document_name,description, 1, loc_id)
    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()

def updateSQLDescriptionGeneralData(name:str, new_description:str):
    sql = f'''
    UPDATE documents SET description = "{new_description}" WHERE (document_name = "{name}");
    '''
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    connection.commit()

# Update Description in SQL and Frontend Node 
def updateDescriptionGeneralData(name:str, new_description:str):
    updateVectorFrontendNodeGeneral(file_name=name, new_description=new_description)
    updateSQLDescriptionGeneralData(name=name, new_description=new_description)


def deleteSQLGeneralData(name:str):
    sql = f"""
    DELETE FROM documents WHERE (document_name = "{name}");
    """

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    connection.commit()


def deleteLocationStorage(id):
    sql = f"""
    DELETE FROM location_storages WHERE (location_storage_id = '{id}');
    """
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    connection.commit()


def getALLDocumentName()-> list:
    sql = f"SELECT documents.document_name FROM documents WHERE is_active = 1"

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    return [c[0] for c in buffer]


def findDataLoc(names: list)-> dict:
    if not names:
        return
    
    prepare = [f"'{name}'" for name in names]
    name_placeholders = ', '.join(prepare)

    sql = f"""
    SELECT 'company' AS type, c.abbr AS name, lc.collection_name, lc.partition_name
    FROM companies c
    JOIN location_storages lc ON c.location_storage_id = lc.location_storage_id
    WHERE c.abbr IN ({name_placeholders}) AND c.is_active = 1

    UNION ALL

    SELECT 'document' AS type, d.document_name AS name, lc.collection_name, lc.partition_name
    FROM documents d
    JOIN location_storages lc ON d.location_storage_id = lc.location_storage_id
    WHERE d.document_name IN ({name_placeholders}) AND d.is_active = 1
    
    ORDER BY 3, 4;
    """

    cursor = connection.cursor()
    cursor.execute(sql)

    results = cursor.fetchall()
    return results


def findCompany(name:str):
    sql = f"""
    SELECT companies.abbr FROM companies
    WHERE is_active = 1 AND companies.abbr = "{name}";
    """

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    if not buffer:
        return False
    return True

def findCompanies(names: list):
    prepare = [f"'{name}'" for name in names]
    name_placeholders = ', '.join(prepare)

    sql = f"SELECT companies.abbr FROM companies WHERE is_active = 1 AND companies.abbr IN ({name_placeholders})"

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()

    a = []
    for i in buffer:
        a.append(i[0])
    return a

def getDocumentLocation(name:str):
    sql = f"""
    SELECT ls.collection_name, ls.partition_name, ls.location_storage_id FROM documents d
    JOIN location_storages ls ON d.location_storage_id = ls.location_storage_id
    WHERE d.document_name = '{name}';
    """

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchone()
    if not res:
        return
    
    return {"collection_name": res[0], "partition_name": res[1], "storage_id": res[2]}


def findDocument(names):
    sql = f'SELECT document_name FROM documents WHERE is_active = 1 AND documents.document_name = "{names}";'

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchone()
    if not res:
        return False
    return True


def getAllSector():
    sql = f"SELECT sector_id, sector_name, abbr FROM sectors"
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchall()
    if not res:
        return
    data = []
    for i in res:
        data.append({"id": i[0], "name": i[1], "abbr": i[2]})
    return data

def getAllGeneralFile():
    sql = f"SELECT document_name, description FROM documents"
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchall()
    if not res:
        return
    data = []
    for i in res:
        data.append({"name": i[0], "description": i[1]})
    return data

def findCollectionCNode():
    client = MilvusClient(db_name=os.getenv("MILVUS_DATABASE_NAME"))
    collections = client.list_collections()
    cnode_items = [item for item in collections if item.startswith("cnode_")]
    cnode_items.sort()
    if cnode_items == []:
        return []
    return cnode_items

def createCnodeCollection()-> str:
    current_node = findCollectionCNode()
    current_node = current_node[-1]


    if current_node == []:
        collection_name = f"cnode_{1}"
    else:
        if isinstance(id := int(current_node.split("_")[1]), int):
            collection_name = f"cnode_{id + 1}"
            # print("Create", collection_name)
    connections.connect(host="localhost", port="19530", db_name=os.getenv("MILVUS_DATABASE_NAME"))
    collection = Collection(name=collection_name,
                            schema=DATA_SOURCE_SCHEMA,
                            consistency_level="Strong",
                            num_shards=4,
                            )
    collection.create_index("dense_vector", INDEX_PARAMS)
    collection.flush()
    print(f'[DB] Collection "{collection_name}" Is Ready.')
    return collection_name


def createNewCompany(abbr:str, name_th:str, name_en:str, sector_id:str):
    limit_size = 5
    nodes = findCollectionCNode()
    poiter = None


    for node in nodes:
        if len(client.list_partitions(node)) - 1 < limit_size:
            poiter = node
            create = False
            break
        else:
            create = True
    if create:
        new_node = createCnodeCollection()
        poiter = new_node

    client.create_partition(collection_name=poiter, partition_name=abbr)
    client.flush(collection_name=poiter)
    insertCompanyData(sector_id=sector_id, abbr=abbr, collection_name=poiter, partition_name=abbr, company_name_th=name_th, company_name_en=name_en)
    print("Create New Company")



def deleteEachCompanyFileData(file_name:str, company_abbr:str):
    company_loc:str = getCompanyLocation(name=company_abbr)
    if not company_loc:
        return
    
    collection_name:str = company_loc["collection_name"]
    partition_name:str = company_loc["partition_name"]

    deleteVectorEachCompanyFile(collection=collection_name, partition=partition_name, file_name=file_name)
    deleteSQLEachCompanyFile(file_name=file_name)

if __name__ == "__main__":
    pass
    # print(createNewCompany("true", "บริษัท ทรู คอร์ปอเรชั่น จำกัด (มหาชน)", "True Corporation PCL", "Banking"))
    # print(createNewCompany("bts", "บริษัท บีทีเอส กรุ๊ป โฮลดิ้งส์ จำกัด (มหาชน)", "BTS Group Holdings PCL", "Banking"))
    # print(getAllSector())

    # print(getALLSQLCompanyDataFile("true"))
    # print(deleteSQLEachCompanyFile("bts_56-1_2023.pdf"))
    # print(deleteEachCompanyFileData(file_id="1", company_abbr="bts"))
    # print(deleteLocationStorage('ndc'))
    # print(findDataLoc(["scb", "ndc", 'eee']))
    # print(findCompanies(["bts", "aot"]))
    # print(findDocument("bv"))
    # print(deleteSQLGeneralData("b"))
    # updateDescriptionGeneralData("b", "rolemssssd")
    # print(loadGeneralFileToLlm())