from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ClassModel import ChatRequest
from agent.model import ask_agent

from services.database_service import (
    get_all_students,
    create_chat_session,
    get_chat_session,
    save_chat_message,
    get_chat_sessions,
)


app = FastAPI(
    title="TMS Backend API",
    description="Tuition Management System API Service",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
       "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/", tags=["Health Check"])
def home():
    return {
        "message": "Hello World"
    }


# ============================================================
# CREATE NEW CHAT
# ============================================================

@app.post("/chat/new", tags=["Chat"])
def new_chat():

    try:

        session_id = create_chat_session()

        return {
            "status": "success",
            "session_id": session_id
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# GET ALL CHAT HISTORY
# ============================================================

@app.get("/chat/history", tags=["Chat"])
def chat_history():

    try:

        sessions = get_chat_sessions()

        return {
            "status": "success",
            "data": sessions
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# GET ONE PARTICULAR CHAT
# ============================================================

@app.get("/chat/{session_id}", tags=["Chat"])
def get_chat(session_id: str):

    try:

        chat = get_chat_session(session_id)

        if not chat:

            raise HTTPException(
                status_code=404,
                detail="Chat session not found"
            )

        return {
            "status": "success",
            "data": chat
        }

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# CHAT AGENT
# ============================================================

@app.post("/chat", tags=["Agent"])
def chat(request: ChatRequest):

    try:

        # ----------------------------------------------------
        # 1. Check session
        # ----------------------------------------------------

        session = get_chat_session(
            request.session_id
        )

        if not session:

            raise HTTPException(
                status_code=404,
                detail="Chat session not found"
            )


        # ----------------------------------------------------
        # 2. Get previous conversation
        # ----------------------------------------------------

        previous_messages = session["messages"]


        # ----------------------------------------------------
        # 3. Ask AI
        # ----------------------------------------------------

        result = ask_agent(
            request.question,
            previous_messages
        )


        # ----------------------------------------------------
        # 4. Save user + AI message
        # ----------------------------------------------------

        messages = save_chat_message(
            request.session_id,
            request.question,
            result
        )


        # ----------------------------------------------------
        # 5. Return response
        # ----------------------------------------------------

        return {
            "status": "success",
            "session_id": request.session_id,
            "response": result,
            "messages": messages
        }


    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the request: {str(e)}"
        )


# ============================================================
# STUDENTS
# ============================================================

@app.get("/students", tags=["Database"])
def fetch_students():

    try:

        students = get_all_students()

        return {
            "status": "success",
            "data": students
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )