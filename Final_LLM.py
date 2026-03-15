import os
import time
import pygame
from google import genai
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from gtts import gTTS
from PIL import Image, ImageOps, ImageEnhance

# ==========================================
# CONFIGURATION
# ==========================================
API_KEY = "API_HERE" 
WATCH_PATH = r"C:\Users\meher\Desktop\sstv images"
TARGET_LANGUAGE = "English"
TTS_LANG_CODE = "en"
# ==========================================

# Initialize Gemini client
client = genai.Client(api_key=API_KEY)

# Initialize audio
pygame.mixer.init()

# ==========================================
# IMAGE PRE-PROCESSING
# ==========================================
def clean_sstv_image(image_path):
    print(f"[>] Pre-processing: {image_path}")
    try:
        img = Image.open(image_path).convert("RGB")
        img = ImageOps.autocontrast(img, cutoff=2)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.5)

        cleaned_path = "processed_signal.jpg"
        img.save(cleaned_path)
        return cleaned_path
    except Exception as e:
        print(f"[!] Pre-processing failed: {e}")
        return image_path

# ==========================================
# RADIO SIGNAL HANDLER
# ==========================================
class RadioHandler(FileSystemEventHandler):

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = event.src_path.lower()

        # 1. IMAGE PIPELINE
        if filepath.endswith((".jpg", ".jpeg", ".png")):
            print(f"\n[!] Image Signal Detected: {os.path.basename(filepath)}")
            time.sleep(3) # Wait for file to finish writing
            self.process_image_query(event.src_path)
            
        # 2. TEXT PIPELINE (From Audio Receiver)
        elif filepath.endswith(".txt"):
            print(f"\n[!] Voice Text Detected: {os.path.basename(filepath)}")
            time.sleep(1) # Wait for text to finish saving
            self.process_text_query(event.src_path)

    # ======================================
    # IMAGE PROCESSING
    # ======================================
    def process_image_query(self, image_path):
        ai_ready_image = clean_sstv_image(image_path)
        print("[>] Analyzing image with Gemini Flash...")

        try:
            with Image.open(ai_ready_image) as img:
                prompt = f"""
                Rate visibility 1-10.
                If below 4 say: signal too weak.

                If above 4:
                identify the object and give 2 sentences of advice
                in {TARGET_LANGUAGE}.

                Be concise for radio transmission.
                """

                # Using your stable model string
                response = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=[prompt, img]
                )

            answer = response.text
            print(f"[AI]: {answer}")
            self.broadcast_answer(answer)

        except Exception as e:
            print(f"[!] Image AI Error: {e}")
            print("[*] Ready for next signal.")

    # ======================================
    # TEXT (VOICE) PROCESSING
    # ======================================
    def process_text_query(self, text_path):
        print("[>] Reading transcribed audio...")
        try:
            with open(text_path, "r", encoding="utf-8") as f:
                user_message = f.read().strip()

            if not user_message:
                print("[!] Text file was empty.")
                return

            print(f"[>] Prompting Gemini with: '{user_message}'")
            
            prompt = f"""
            A radio user just asked: "{user_message}"
            Give 2 sentences of advice or a brief answer in {TARGET_LANGUAGE}.
            Keep response short for radio transmission.
            """

            # Using the same stable model string for text!
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
            )

            answer = response.text
            print(f"[AI]: {answer}")
            self.broadcast_answer(answer)

        except Exception as e:
            print(f"[!] Text AI Error: {e}")
            print("[*] Ready for next signal.")

    # ======================================
    # RADIO BROADCAST
    # ======================================
    def broadcast_answer(self, text):
        try:
            tts = gTTS(text=text, lang=TTS_LANG_CODE)
            tts.save("radio_response.mp3")

            print("[PTT] BROADCASTING...")

            pygame.mixer.music.load("radio_response.mp3")
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            pygame.mixer.music.unload()
            
            # Remove file so it can be cleanly overwritten next time
            if os.path.exists("radio_response.mp3"):
                os.remove("radio_response.mp3")

            print("[*] Audio file released. Ready for next signal.")

        except Exception as e:
            print(f"[!] Broadcast Error: {e}")


# ==========================================
# MAIN SYSTEM LOOP
# ==========================================
if __name__ == "__main__":

    if not os.path.exists(WATCH_PATH):
        os.makedirs(WATCH_PATH)

    event_handler = RadioHandler()

    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=False)
    observer.start()

    print("\n--- RURAL AI HUB 2026 ACTIVE ---")
    print(f"Monitoring: {WATCH_PATH}")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()

    observer.join()