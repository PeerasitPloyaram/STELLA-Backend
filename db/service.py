import mariadb
import sys
import os
from dotenv import load_dotenv


load_dotenv()
connection = mariadb.connect(
    user=os.getenv("DB_CLIENT_USER"),
    password=os.getenv("DB_CLIENT_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv('DB_DATABASE_NAME')
)



def createNewStorage(collection_name, partition_name):
    sql = "INSERT INTO collection_storage(collection_name, partition_name) VALUES (%s, %s);"

    try:
        cursor = connection.cursor()
        values = (collection_name, partition_name)

        cursor.execute(sql, values)
        id = cursor.lastrowid
        connection.commit()

        return id

    except mariadb.IntegrityError as e:
        print("[DB][ERROR]", e)
        connection.rollback()

    finally:
        # connection.close()
        pass



def insertData(name, type_id, collection_name, partitiion_name):
    storage_id = createNewStorage(collection_name, partitiion_name)

    sql = "INSERT INTO documents (name, is_active, storage_id, type_id) VALUES (%s, %d, %d, %d)";
    values = (name, True, storage_id, type_id)

    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()

# Find Documents Collection and Partition in Vector DB
def findDocumentLoc(names: list)-> dict:
    if not names:
        return
    
    prepare = [f"'{name}'" for name in names]
    name_placeholders = ', '.join(prepare)

    sql = f"""
    SELECT d.name, d.type_id, c.collection_name, c.partition_name
    FROM documents d
    JOIN collection_storage c ON d.storage_id = c.storage_id
    WHERE d.name IN ({name_placeholders}) AND d.is_active = 1;
    """

    cursor = connection.cursor()
    cursor.execute(sql)

    output = {}
    results = cursor.fetchall()
    for row in results:
        name = row[0]
        output[name] = row
    return output


def getALLCompany()-> list:
    sql = f"SELECT documents.name FROM documents WHERE is_active = 1 AND type_id = 1"

    cursor = connection.cursor()
    cursor.execute(statement=sql)
    buffer = cursor.fetchall()
    return [c[0] for c in buffer]


if __name__ == "__main__":
    # insertData("coso", 2, "cnode_2", "coso")
    # print(findDocumentLoc(["aot"]))
    print(getALLCompany())