import sounddevice as sd
import numpy as np
import time
import os
import wave
from scipy.io import wavfile
from scipy.signal import butter, lfilter
import speech_recognition as sr

# ==========================================
# CONFIGURATION
# ==========================================
WATCH_PATH = r"C:\Users\meher\Desktop\sstv images"
RATE = 44100
SILENCE_LIMIT = 2.0  
CALIBRATION_TIME = 3.0

if not os.path.exists(WATCH_PATH):
    os.makedirs(WATCH_PATH)
# ==========================================

def lowpass_filter(data, cutoff, fs, order=5):
    nyq = 0.5 * fs
    b, a = butter(order, cutoff / nyq, btype='low', analog=False)
    return lfilter(b, a, data)

def demodulate_am(input_data, sample_rate):
    signal = input_data.astype(float)
    rectified = np.abs(signal)
    recovered = lowpass_filter(rectified, 2500, sample_rate)
    recovered -= np.mean(recovered)
    if np.max(np.abs(recovered)) > 0:
        recovered /= np.max(np.abs(recovered))
    return np.int16(recovered * 32767)

def get_peak_freq(data, sample_rate):
    analysis_len = int(sample_rate * 1.5)
    chunk = data[:analysis_len] 
    if len(chunk) < 1024: return 0
    fft_data = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1.0/sample_rate)
    mask = (freqs > 1000) & (freqs < 4000)
    if not np.any(mask): return 0
    return freqs[mask][np.argmax(fft_data[mask])]

def calibrate():
    print(f"--- CALIBRATING NOISE FLOOR ({CALIBRATION_TIME}s) ---")
    levels = []
    def stream_cb(indata, frames, time, status):
        levels.append(np.linalg.norm(indata) * 10)
        
    with sd.InputStream(samplerate=RATE, channels=1, callback=stream_cb):
        sd.sleep(int(CALIBRATION_TIME * 1000))
        
    thresh = np.max(levels) * 1.8 
    print(f"[*] Squelch set to: {thresh:.4f}")
    return thresh

def process_signal(audio_data):
    audio_data = audio_data.flatten()
    peak = get_peak_freq(audio_data, RATE)
    print(f"[>] Dominant Frequency: {int(peak)}Hz")

    # 1. Check for Voice Pilot (3500Hz)
    if 3300 < peak < 3700:
        print("[!] PILOT DETECTED: Demodulating Voice...")
        recovered_signal = demodulate_am(audio_data, RATE)
        
        # Save temporary wav for the SpeechRecognizer
        temp_wav = "temp_decode.wav"
        wavfile.write(temp_wav, RATE, recovered_signal)
        
        # PLAY THROUGH LAPTOP SPEAKERS
        print("[>] Replaying audio locally...")
        sd.play(recovered_signal, RATE)
        sd.wait()

        # LOCAL SPEECH-TO-TEXT
        print("[>] Running Local STT Translation...")
        r = sr.Recognizer()
        try:
            with sr.AudioFile(temp_wav) as source:
                audio = r.record(source)
            text_result = r.recognize_google(audio)
            print(f"[*] STT Success: '{text_result}'")
            
            # Write to TXT file for the Ground Station Watcher
            txt_filename = f"STT_RCVD_{int(time.time())}.txt"
            txt_path = os.path.join(WATCH_PATH, txt_filename)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text_result)
            print(f"[*] Saved text payload to: {txt_path}")
            
        except sr.UnknownValueError:
            print("[!] STT could not understand audio.")
        except Exception as e:
            print(f"[!] STT Error: {e}")

    # 2. Check for SSTV (1900Hz)
    elif 1800 < peak < 2000:
        print("[!] SSTV HEADER DETECTED: Saving raw signal.")
        path = os.path.join(WATCH_PATH, f"RAW_SSTV_{int(time.time())}.wav")
        wavfile.write(path, RATE, np.int16(audio_data * 32767))
        
    else:
        print("[?] Interference. Ignored.")

def run_listener(threshold):
    print("\n--- RAIDIO LISTENER ACTIVE ---")
    def callback(indata, frames, time_info, status):
        vol = np.linalg.norm(indata) * 10
        if vol > threshold:
            if not callback.is_rec: print("\n[!] SIGNAL DETECTED...")
            callback.is_rec = True
            callback.data.append(indata.copy())
            callback.silence = 0
        elif callback.is_rec:
            callback.data.append(indata.copy())
            callback.silence += frames / RATE
            if callback.silence > SILENCE_LIMIT:
                callback.is_rec = False
                captured = np.concatenate(callback.data)
                callback.data = []
                process_signal(captured)

    callback.is_rec, callback.data, callback.silence = False, [], 0
    with sd.InputStream(samplerate=RATE, channels=1, callback=callback):
        while True: sd.sleep(500)

if __name__ == "__main__":
    try:
        sq_thresh = calibrate()
        run_listener(sq_thresh)
    except KeyboardInterrupt:
        print("\n[!] Listener Terminated.")