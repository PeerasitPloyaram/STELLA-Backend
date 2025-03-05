from langchain_core.messages import AIMessage, HumanMessage
from datetime import datetime, timedelta
import uuid
import mariadb
import sys, os

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


def createExpireDate():
    now = datetime.now()
    expire_time = now + timedelta(hours=2)
    return expire_time.strftime("%Y-%m-%d %H:%M:%S")


def createGuestSession():
    """
    Create new guest session return: UUID
    """
    sql = "INSERT INTO chat_sessions (chat_session_uuid, user_type, expire_at) VALUES (%s, %s, %s)"

    expire_date = createExpireDate()
    session_uuid = str(uuid.uuid4())
    values = (session_uuid, "guest", expire_date)

    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()
    return session_uuid

def SessionIsExpire(session_id):
    sql = f'SELECT expire_at FROM chat_sessions WHERE chat_session_uuid = "{session_id}"'
    cursor = connection.cursor()
    cursor.execute(sql)

    expire_time = cursor.fetchall()[0][0]
    if datetime.now() > expire_time:
        return True
    else:
        return False

def findSession(session_id):
    sql = f'SELECT chat_session_uuid FROM chat_sessions WHERE chat_session_uuid = "{session_id}"'
    cursor = connection.cursor()
    cursor.execute(sql)

    session = cursor.fetchall()
    if not session:
        return False
    
    return True

def saveHistory(session_uuid, message, role):
    sql = "INSERT INTO messages (chat_session_uuid, message, role) VALUES (%s, %s, %s)"

    values = (session_uuid, message, role)

    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)

    new_expire = createExpireDate()
    sql = f'UPDATE chat_sessions SET expire_at = "{new_expire}" WHERE chat_session_uuid = "{session_uuid}";'
    cursor.execute(statement=sql)
    connection.commit()

def getHistory(session_uuid):
    sql = f'SELECT messages.message, messages.role, created_at FROM messages WHERE messages.chat_session_uuid = "{session_uuid}";'
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    respone = cursor.fetchall()
    # print(respone)
    session_messages = []
    for message, role, date in respone:
        if role == "human":
            session_messages.append(HumanMessage(content=message))
        else:
            session_messages.append(AIMessage(content=message))
        # session_messages.append({"role": role, "message": message, "date": date.strftime("%Y-%m-%d %H:%M:%S")})

    return session_messages

if __name__ == "__main__":
    # print(connection)
    # a = (createGuestSession())
    # print(findSession("f7c8979d-7535-4d0b-9c2b-af3af5deb93f"))
    pass