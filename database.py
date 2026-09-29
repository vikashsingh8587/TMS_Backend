import mysql.connector
import uuid
import json

def get_db_connection():
    connection = mysql.connector.connect(
       host="localhost",
        port=3306,
        user="root",
        password="1234",
        database="TMC"
    )

    return connection

# ============================================================
# CREATE NEW CHAT SESSION
# ============================================================

def create_chat_session():
    session_id = str(uuid.uuid4())

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO chat_sessions
            (session_id, title, messages)
            VALUES (%s, %s, %s)
            """,
            (
                session_id,
                "New Chat",
                json.dumps([])
            )
        )

        connection.commit()

        return session_id

    finally:
        cursor.close()
        connection.close()


# ============================================================
# GET ALL CHAT SESSIONS
# ============================================================

def get_chat_sessions():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                session_id,
                title,
                created_at,
                updated_at
            FROM chat_sessions
            ORDER BY updated_at DESC
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# ============================================================
# GET PARTICULAR CHAT
# ============================================================

def get_chat_session(session_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                session_id,
                title,
                messages,
                created_at,
                updated_at
            FROM chat_sessions
            WHERE session_id = %s
            """,
            (session_id,)
        )

        chat = cursor.fetchone()

        if not chat:
            return None

        # MySQL JSON may already be returned as dict/list
        if isinstance(chat["messages"], str):
            chat["messages"] = json.loads(chat["messages"])

        return chat

    finally:
        cursor.close()
        connection.close()


# ============================================================
# SAVE MESSAGE
# ============================================================

def save_chat_message(
    session_id: str,
    user_message: str,
    ai_message: str
):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Get existing messages
        cursor.execute(
            """
            SELECT messages
            FROM chat_sessions
            WHERE session_id = %s
            """,
            (session_id,)
        )

        result = cursor.fetchone()

        if not result:
            raise ValueError("Session not found")

        messages = result["messages"]

        if isinstance(messages, str):
            messages = json.loads(messages)

        # Add new conversation
        messages.append({
            "role": "user",
            "content": user_message
        })

        messages.append({
            "role": "assistant",
            "content": ai_message
        })

        # Create title from first user message
        title = user_message.strip()

        if len(title) > 50:
            title = title[:50] + "..."

        # Update database
        cursor.execute(
            """
            UPDATE chat_sessions
            SET
                messages = %s,
                title = CASE
                    WHEN title = 'New Chat' THEN %s
                    ELSE title
                END
            WHERE session_id = %s
            """,
            (
                json.dumps(messages),
                title,
                session_id
            )
        )

        connection.commit()

        return messages

    finally:
        cursor.close()
        connection.close()


# ============================================================
# DELETE CHAT
# ============================================================

def delete_chat_session(session_id: str):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM chat_sessions
            WHERE session_id = %s
            """,
            (session_id,)
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        cursor.close()
        connection.close()