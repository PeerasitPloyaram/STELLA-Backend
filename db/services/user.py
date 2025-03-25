from datetime import datetime, timedelta
import uuid
import mariadb
import sys, os
import bcrypt
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def get_connection():
    return mariadb.connect(
        user=os.getenv("DB_CLIENT_USER"),
        password=os.getenv("DB_CLIENT_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_DATABASE_NAME")
    )

def createUserId():
    session_uuid = str(uuid.uuid4())
    return session_uuid

def creatHash(password:str):
    hash_password = bcrypt.hashpw(password=password.encode('utf-8'), salt=os.getenv("STELLA_PASSWORD_SALT").encode('utf-8'))
    return hash_password

def createUser(username: str, password: str, email: str):
    sql = f'SELECT role_id FROM roles WHERE name = "user"'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    role_id = cursor.fetchall()[0][0]
    hash_password = creatHash(password=password)
    uuid = createUserId()

    sql = f'INSERT INTO users (user_id, role_id, username, password, email) VALUES (%s, %s, %s, %s, %s);'
    cursor.execute(sql, (uuid, role_id, username, hash_password, email))
    connection.commit()
    connection.close()

def findUser(username: str, email: str| None = None):
    sql = f'SELECT username FROM users WHERE username = "{username}"'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchall()
    if not res:
        return False
    fetch_user = res[0][0]
    if username == fetch_user:
        return True
    else:
        return False
    
def findUserById(user_id: str):
    sql = f'SELECT username FROM users WHERE user_id = "{user_id}"'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchone()
    if not res:
        return False
    return True

def checkPassword(username: str, password: str):
    sql = f'SELECT password FROM users WHERE username = "{username}"'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchall()
    if not res:
        return False
    stored_hash = res[0][0]

    if bcrypt.hashpw(password=password.encode('utf-8'), salt=os.getenv("STELLA_PASSWORD_SALT").encode('utf-8')) == stored_hash:
        return True
    else:
        return False
    
def getRole(username:str):
    query = f"""
    SELECT users.username, roles.name AS role_name
    FROM users
    JOIN roles ON users.role_id = roles.role_id
    WHERE users.username = "{username}"
    """

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    return result

def getUserId(username:str):
    query = f"""
    SELECT user_id FROM users WHERE users.username = "{username}"
    """

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    return result[0]


def auth(user_id:str):
    query = f"""
    SELECT roles.name AS role_name FROM users
    JOIN roles ON users.role_id = roles.role_id
    WHERE users.user_id = "{user_id}"
    """

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    return result[0]

if __name__ == "__main__":
    # createUser("e", "e", "test")
    pass

