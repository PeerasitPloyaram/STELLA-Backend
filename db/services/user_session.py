from langchain_core.messages import AIMessage, HumanMessage
from datetime import datetime, timedelta
import uuid
import mariadb
import sys, os

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.user import findUserById
load_dotenv()

def get_connection():
    return mariadb.connect(
        user=os.getenv("DB_CLIENT_USER"),
        password=os.getenv("DB_CLIENT_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_DATABASE_NAME")
    )


def createExpireDate():
    now = datetime.now()
    expire_time = now + timedelta(minutes=30)
    return expire_time.strftime("%Y-%m-%d %H:%M:%S")

def createUserSession(user_id:str):
    """
    Create new guest session return: UUID
    """
    if not findUserById(user_id=user_id):
        return "User not found"

    sql = "INSERT INTO chat_sessions (chat_session_uuid, user_id, user_type) VALUES (%s, %s, %s)"

    session_uuid = str(uuid.uuid4())
    values = (session_uuid, user_id, "user")

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()
    connection.close()
    return session_uuid

def createGuestSession():
    """
    Create new guest session return: UUID
    """
    sql = "INSERT INTO chat_sessions (chat_session_uuid, user_type, expire_at) VALUES (%s, %s, %s)"

    expire_date = createExpireDate()
    session_uuid = str(uuid.uuid4())
    values = (session_uuid, "guest", expire_date)

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)
    connection.commit()
    connection.close()
    return session_uuid


def changeGuestSesionToUserSession(session_id:str, user_id:str):
    sql = f"""
    UPDATE chat_sessions SET user_id = "{user_id}", user_type = "user", expire_at = NULL WHERE (chat_session_uuid = "{session_id}");
    """

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(sql)
    connection.commit()
    connection.close()

def SessionIsExpire(session_id):
    sql = f'SELECT expire_at FROM chat_sessions WHERE chat_session_uuid = "{session_id}"'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(sql)

    expire_time = cursor.fetchall()[0][0]
    if datetime.now() > expire_time:
        return True
    else:
        return False

def findSession(session_id):
    sql = f'SELECT chat_session_uuid FROM chat_sessions WHERE chat_session_uuid = "{session_id}"'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(sql)

    session = cursor.fetchone()
    if not session:
        return False
    
    return True

def findSessionIsGuest(session_id):
    sql = f'SELECT user_type FROM chat_sessions WHERE chat_session_uuid = "{session_id}"'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(sql)

    session = cursor.fetchone()
    if not session:
        return
    
    if session[0] == "guest":
        return True
    elif session[0] == "user":
        return False

def saveHistory(session_uuid, message, role):
    sql = "INSERT INTO messages (chat_session_uuid, message, role) VALUES (%s, %s, %s)"

    values = (session_uuid, message, role)

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql, data=values)

    new_expire = createExpireDate()
    sql = f'UPDATE chat_sessions SET expire_at = "{new_expire}" WHERE chat_session_uuid = "{session_uuid}";'
    cursor.execute(statement=sql)
    connection.commit()
    connection.close()

def getHistory(session_uuid):
    sql = f'SELECT messages.message, messages.role, created_at FROM messages WHERE messages.chat_session_uuid = "{session_uuid}";'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    respone = cursor.fetchall()
    session_messages = []
    for message, role, date in respone:
        if role == "human":
            session_messages.append(HumanMessage(content=message))
        else:
            session_messages.append(AIMessage(content=message))
    return session_messages

def findSessionIsOwnByUser(user_id:str, session:str):
    sql = f'SELECT chat_session_uuid FROM chat_sessions WHERE (user_id = "{user_id}" AND chat_session_uuid = "{session}");'
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    res = cursor.fetchone()
    if not res:
        return False
    return True

def getAllChatHistoryName(user_id:str, session:str|None = None):
    if findUserById(user_id=str(user_id)):
        if not session:
            message_history = []
        elif findSessionIsOwnByUser(user_id=user_id, session=session):
            message_history = getHistoryFormat(session_uuid=session)
            first_message:str = getFirstMessageHistory(session_uuid=session)
        else:
            message_history = []

        sql = f'SELECT chat_session_uuid, created_at FROM chat_sessions WHERE user_id = "{user_id}" ORDER BY chat_sessions.created_at ASC;'

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(statement=sql)
        respone = cursor.fetchall()

        if not respone:
            return {
                "type": "user",
                "last_chat": None,
                "last_message": None,
            }

        buffer = {
            "type": "user",
            "last_chat": session,
            "last_message": message_history,
            "chat_history": [{"type":"user","chat_session": b[0], "chat_name": getFirstMessageHistory(b[0]), "create_date": b[1].strftime("%Y-%m-%d %H:%M:%S")} for b in respone]
        }
    
        return buffer
        
    else:
        if not session:
            return {"type":"guest", "last_chat": session, "last_message": []}
        if not findSessionIsGuest(session_id=session):
            return {"type":"guest", "last_chat": session, "last_message": []}
        if SessionIsExpire(session_id=session):
            return {"type":"guest", "last_chat": session, "last_message": []}
        message_history = getHistoryFormat(session_uuid=session)
        first_message:str = getFirstMessageHistory(session_uuid=session)
        return {"type":"guest", "chat_session": session, "chat_name": first_message, "message": message_history}


def getFirstMessageHistory(session_uuid:str):
    sql = f'SELECT messages.message FROM messages WHERE messages.chat_session_uuid = "{session_uuid}" ORDER BY messages.created_at ASC LIMIT 1;'
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    response = cursor.fetchone()
    if not response:
        return
    return response[0]

def getHistoryFormat(session_uuid:str):
    sql = f'SELECT messages.message, messages.role, created_at FROM messages WHERE messages.chat_session_uuid = "{session_uuid}" ORDER BY messages.created_at ASC;'

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(statement=sql)
    respone = cursor.fetchall()

    session_messages = []
    for message, role, date in respone:
        if role == "human":
            session_messages.append({"text": message, "isUser":True})
        else:
            session_messages.append({"text": message, "isUser":False})
    return session_messages


def dropUserSession(user_id:str, session_id:str):
    if findUserById(user_id=user_id):
        sql = f"""
        DELETE FROM chat_sessions WHERE (chat_session_uuid = "{session_id}");
        """
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(statement=sql)
        connection.commit()
        connection.close()

if __name__ == "__main__":
    # print(connection)
    # print(getFirstMessageHistory("2ce0f745-a2f0-412f-aecd-3755f786559b"))
    # print(createUserSession("2"))
    # a = (createGuestSession())
    # print(findSession("f7c8979d-7535-4d0b-9c2b-af3af5deb93f"))
    # changeGuestSesionToUserSession("af4ee190-cef5-4c66-a966-efd0692bab70", "3")
    # print(findSessionIsGuest("137efee5-a48e-44a3-85d4-4bf98d272ed7"))
    # print(getAllChatHistoryName("1"))
    # dropUserSession("15","88556938-32a2-4104-8aca-ff1862601e51")
    # print(findSessionIsOwnByUser("4","8e14e0c1-7143-4686-98d8-86c0797586d1"))
    pass