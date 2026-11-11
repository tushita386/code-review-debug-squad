
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
import importlib.metadata as m

print("langchain-google-genai", m.version("langchain-google-genai"))

for name in ["gemini-2.5-flash", "gemini-3.8-flash"]:
    try:
        llm = ChatGoogleGenerativeAI(
            model=name,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        print(name, "->", llm.invoke("Say hi in 3 words").content)

    except Exception:
        print(name, "FAILED")
        traceback.print_exc(limit=2)
