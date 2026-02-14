import os
import time
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(__file__)
SERVICE_ACCOUNT = os.path.join(BASE_DIR, "service_accountkey.json")
BOT_NAME = "KMC AI BOT"
GEMINI_API_KEY = "AIzaSyBzyOSY7JQWm0c1NwNLmu9IPzUg8-DYonA"

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("kmc-bot")

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    log.info("✅ Firebase Connected")
except Exception as e:
    log.error(f"❌ Firebase Error: {e}")
    exit()

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_ID = "gemini-2.5-flash-lite"

def clean_command_text(text: str) -> str:
    cleaned = text.lower().replace("@bot", "").strip()
    return " ".join(cleaned.split())

def on_snapshot(col_snapshot, changes, read_time):
    for change in changes:
        try:
            if change.type.name != 'ADDED':
                continue

            data = change.document.to_dict()
            text = data.get('text', '')
            sender = data.get('sender', '')

            if not text or not isinstance(text, str) or sender == BOT_NAME:
                continue

            if "@bot" in text.lower():
                user_query = clean_command_text(text)
                log.info(f"🤖 AI Processing: {user_query}")

                try:
                    prompt = (
                        f"System Instruction: You are the KMC School AI. "
                        f"Provide your answer in plain text ONLY. Never use bolding (**) or markdown symbols. "
                        f"User Question: {user_query}"
                    )

                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=prompt
                    )
                    
                    if response.text:
                        db.collection("group_messages").add({
                            "text": response.text.strip(),
                            "sender": BOT_NAME,
                            "createdAt": firestore.SERVER_TIMESTAMP
                        })
                        log.info("✉️ Plain text response posted.")
                    else:
                        log.warning("⚠️ AI returned no text.")

                except Exception as ai_err:
                    log.error(f"❌ Gemini Error: {ai_err}")

        except Exception as e:
            log.error(f"❌ Error: {e}")

db.collection("group_messages").on_snapshot(on_snapshot)
log.info(f"🚀 {BOT_NAME} IS ONLINE!")

if __name__ == '__main__':
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping bot...")