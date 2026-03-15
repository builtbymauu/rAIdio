import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import numpy as np
from scipy.io import wavfile
from PIL import Image
from pysstv.color import MartinM1 
import pygame
import os
import glob
import time

# --- S25 ULTRA HARDWARE BYPASS ---
Image.MAX_IMAGE_PIXELS = None 

# --- INITIALIZE AUDIO ---
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

def play_audio(filename):
    if os.path.exists(filename):
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

def get_latest_photo():
    camera_path = "/storage/emulated/0/DCIM/Camera/*"
    list_of_files = glob.glob(camera_path)
    if not list_of_files: return None
    return max(list_of_files, key=os.path.getctime)

def get_latest_audio():
    # Looks in your primary path first, then fallback
    primary_path = "/storage/emulated/0/Music/Recorders/*.wav"
    fallback_path = "/storage/emulated/0/Music/*.wav"
    
    list_of_files = glob.glob(primary_path)
    if not list_of_files:
        list_of_files = glob.glob(fallback_path)
        
    if not list_of_files: 
        return None
        
    return max(list_of_files, key=os.path.getctime)

def update_timer(seconds_left, total_duration):
    if seconds_left > 0 and pygame.mixer.music.get_busy():
        lbl_status.config(text=f" SENDING: {seconds_left}s", fg="#f44336") 
        progress['value'] = ((total_duration - seconds_left) / total_duration) * 100
        root.after(1000, lambda: update_timer(seconds_left - 1, total_duration))
    else:
        lbl_status.config(text="READY", fg="#333333") 
        progress['value'] = 0

# --- SIGNAL HELPER ---
def generate_beep(duration=1.0, freq=3500, rate=44100):
    """Generates a clean sine wave beep."""
    t = np.linspace(0, duration, int(rate * duration), False)
    beep = np.sin(2 * np.pi * freq * t) * 0.5
    return beep

# --- RADIO MATH ---
def process_audio(filepath):
    if not filepath.lower().endswith('.wav'):
        raise Exception("Error: Please use a .WAV file!")
    
    output_path = "temp_audio_screech.wav"
    sample_rate, audio_data = wavfile.read(filepath)
    
    if len(audio_data.shape) > 1: audio_data = np.mean(audio_data, axis=1)
    audio_data = audio_data.astype(float)
    audio_data = audio_data / (np.max(np.abs(audio_data)) + 1e-9)
    
    # AM Modulation at 3000Hz
    t = np.arange(len(audio_data)) / sample_rate
    carrier = np.cos(2 * np.pi * 3000 * t) 
    modulated = (1 + 0.8 * audio_data) * carrier
    
    # Create 1s Beeps (Start and End)
    beep = generate_beep(duration=1.0, freq=3500, rate=sample_rate)
    
    # Combine: [Beep] + [Message] + [Beep]
    final_signal = np.concatenate([beep, modulated, beep])
    
    final_audio = np.int16(final_signal / (np.max(np.abs(final_signal)) + 1e-9) * 32767)
    wavfile.write(output_path, sample_rate, final_audio)
    return output_path

def process_image(filepath):
    output_wav_path = "temp_image_sstv.wav"
    # Back to standard: No pilot tones for images
    with Image.open(filepath) as img:
        img = img.convert('RGB')
        img_final = img.resize((320, 256), Image.Resampling.LANCZOS)
        sstv = MartinM1(img_final, 44100, 16) 
        sstv.write_wav(output_wav_path)
    return output_wav_path

# --- UI HANDLERS ---
def handle_audio():
    # Attempt to launch Samsung Voice Recorder natively
    try: 
        os.system("am start -n com.sec.android.app.voicenote/com.sec.android.app.voicenote.main.VNMainActivity")
    except: 
        pass
    
    messagebox.showinfo("Microphone", "1. Record your voice message.\n2. Return here and click OK.")
    
    latest = get_latest_audio()
    if latest:
        try:
            lbl_status.config(text="PROCESSING...", fg=ACCENT_BLUE)
            root.update()
            result = process_audio(latest)
            
            rate, data = wavfile.read(result)
            duration = int(len(data) / rate)
            
            play_audio(result)
            update_timer(duration, duration)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    else:
        messagebox.showerror("Error", "No audio file found. Make sure you saved the recording.")

def handle_image_hunt():
    try: os.system("am start -n com.sec.android.app.camera/com.sec.android.app.camera.Camera")
    except: pass
    
    messagebox.showinfo("Camera", "1. Take a photo.\n2. Return here and click OK.")
    
    latest = get_latest_photo()
    if latest:
        try:
            lbl_status.config(text="SSTV ENCODING...", fg=ACCENT_BLUE)
            root.update()
            result = process_image(latest)
            play_audio(result)
            update_timer(114, 114) # Standard Martin M1 duration (No beeps)
        except Exception as e:
            messagebox.showerror("Error", f"Mapping Error: {e}")

# --- CUSTOM TKINTER UI ---
BG_COLOR = "#B0B0B0"  
FONT = "Courier"      
ACCENT_BLUE = "#4B6B82"

root = tk.Tk()
root.title("RAIDIO")
root.configure(bg=BG_COLOR)

main_frame = tk.Frame(root, bg=BG_COLOR)
main_frame.pack(expand=True, fill="both", pady=20)

# --- HEADER SECTION ---
header_frame = tk.Frame(main_frame, bg=BG_COLOR)
header_frame.pack(pady=(10, 5))

tk.Label(header_frame, text="R", font=(FONT, 42, "bold"), fg="black", bg=BG_COLOR).pack(side="left")
tk.Label(header_frame, text="AI", font=(FONT, 42, "bold"), fg=ACCENT_BLUE, bg=BG_COLOR).pack(side="left")
tk.Label(header_frame, text="DIO", font=(FONT, 42, "bold"), fg="black", bg=BG_COLOR).pack(side="left")

tk.Label(main_frame, text="Speak or send a photo", font=(FONT, 16, "bold"), fg="black", bg=BG_COLOR).pack(pady=(0, 20))

# --- NATIVE CANVAS ICON BUTTONS ---
def create_canvas_card(parent, text, icon_type, command):
    w, h = 800, 480
    center_x = w / 2
    
    c = tk.Canvas(parent, width=w, height=h, bg=BG_COLOR, highlightthickness=0)
    c.pack(pady=15)

    def draw_rounded_rect(x1, y1, x2, y2, r, **kwargs):
        points = (x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1)
        return c.create_polygon(points, **kwargs, smooth=True)

    draw_rounded_rect(12, 12, w-3, h-3, 50, fill="#888888")
    card_id = draw_rounded_rect(5, 5, w-10, h-10, 50, fill=ACCENT_BLUE, outline="", width=0)

    mic_inner = None
    if icon_type == "mic":
        c.create_line(center_x, 100, center_x, 180, width=28, capstyle=tk.ROUND, fill="black")
        mic_inner = c.create_line(center_x, 100, center_x, 180, width=14, capstyle=tk.ROUND, fill=ACCENT_BLUE)
        c.create_arc(center_x-55, 120, center_x+55, 230, start=180, extent=180, style=tk.ARC, width=6, outline="black")
        c.create_line(center_x, 230, center_x, 270, width=6, fill="black")
        c.create_line(center_x-45, 270, center_x+45, 270, width=6, fill="black")
    elif icon_type == "img":
        c.create_rectangle(center_x-85, 100, center_x+85, 230, width=6, outline="black")
        c.create_oval(center_x-55, 120, center_x-25, 150, width=5, outline="black")
        c.create_line(center_x-85, 230, center_x-35, 175, center_x+20, 230, width=6, fill="black")
        c.create_line(center_x-25, 230, center_x+30, 185, center_x+85, 230, width=6, fill="black")

    c.create_text(center_x, 360, text=text, font=(FONT, 18, "bold"), fill="black")
    cover = c.create_rectangle(5, 5, w-10, h-10, fill="", outline="")
    
    def on_click(event):
        c.itemconfig(card_id, fill="#3A5365")
        if mic_inner: c.itemconfig(mic_inner, fill="#3A5365")
        root.after(100, lambda: [c.itemconfig(card_id, fill=ACCENT_BLUE), 
                                 c.itemconfig(mic_inner, fill=ACCENT_BLUE) if mic_inner else None])
        command()
    c.tag_bind(cover, "<Button-1>", on_click)

create_canvas_card(main_frame, "Speak", "mic", handle_audio)
create_canvas_card(main_frame, "Send Photo", "img", handle_image_hunt)

# --- STATUS & STOP SECTION ---
bottom_frame = tk.Frame(root, bg=BG_COLOR)
bottom_frame.pack(side="bottom", fill="x", pady=20)

style = ttk.Style()
style.theme_use('clam')
style.configure("TProgressbar", thickness=10, background="black", troughcolor=BG_COLOR, borderwidth=0)
progress = ttk.Progressbar(bottom_frame, orient="horizontal", length=600, mode="determinate", style="TProgressbar")
progress.pack(pady=5)

lbl_status = tk.Label(bottom_frame, text="READY", font=(FONT, 14, "bold"), fg="#333333", bg=BG_COLOR)
lbl_status.pack(pady=5)

btn_stop = tk.Label(bottom_frame, text="STOP", bg=BG_COLOR, fg="#f44336", 
                    font=(FONT, 14, "bold"), cursor="hand2")
btn_stop.pack(pady=10)
btn_stop.bind("<Button-1>", lambda e: pygame.mixer.music.stop())

root.mainloop()