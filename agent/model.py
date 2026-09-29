import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage

from agent.tool import ALL_TOOLS
from agent.prompt import SYSTEM_PROMPT


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# 2. INITIALIZE GEMINI MODEL
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite"
)


# ============================================================
# 3. CREATE AGENT
# ============================================================

agent = create_agent(
    model=llm,
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT
)


# ============================================================
# 4. ASK AGENT
# ============================================================

def ask_agent(
    question: str,
    previous_messages: list = None
):

    print(f"Received question: {question}")

    try:

        # ----------------------------------------------------
        # Previous messages nahi hain
        # ----------------------------------------------------

        if previous_messages is None:
            previous_messages = []


        # ----------------------------------------------------
        # Convert DB JSON → LangChain messages
        # ----------------------------------------------------

        messages = []

        for message in previous_messages:

            role = message.get("role")
            content = message.get("content", "")

            if role == "user":

                messages.append(
                    HumanMessage(
                        content=content
                    )
                )

            elif role == "assistant":

                messages.append(
                    AIMessage(
                        content=content
                    )
                )


        # ----------------------------------------------------
        # Add current user question
        # ----------------------------------------------------

        messages.append(
            HumanMessage(
                content=question
            )
        )


        # ----------------------------------------------------
        # Send complete conversation to agent
        # ----------------------------------------------------

        result = agent.invoke({
            "messages": messages
        })


        # ----------------------------------------------------
        # Get final AI response
        # ----------------------------------------------------

        response = result["messages"][-1].content

        print(f"AI Response: {response}")

        return response


    except Exception as e:

        print(
            f"Error during agent invocation: {e}"
        )

        raise e