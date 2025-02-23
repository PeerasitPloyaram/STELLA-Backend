import mariadb
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()
connection = mariadb.connect(
    user=os.getenv("DB_CLIENT_USER"),
    password=os.getenv("DB_CLIENT_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv('DB_DATABASE_NAME')
)


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
    # except:
        #     print("error")


def insertGeneralData(document_name:str, collection_name: str, partition_name: str)-> None:
    sql = """INSERT INTO documents (document_name, is_active, location_storage_id)
    VALUES (%s, %d, %d)
    """
    # try:
    loc_id = createNewLocStorage(collection_name=collection_name, partition_name=partition_name)
    values = (document_name, 1, loc_id)
    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()
    # except:
        #     print("error")


def getALLAbbrCompany()-> list:
    sql = f"SELECT companies.abbr FROM companies WHERE is_active = 1"

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    return [c[0] for c in buffer]


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

def GetAllCompanies():
    sql = f"SELECT companies.abbr, companies.company_name_th, companies.company_name_en FROM companies WHERE is_active = 1"
    
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    return buffer


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

if __name__ == "__main__":
    print(getALLAbbrCompany())
    # print(getALLDocumentName())

    # print(findDataLoc(["scb", "ndc", 'eee']))
    # findCompanies(["bts", "aot"])
    # print(loadGeneralFileToLlm())