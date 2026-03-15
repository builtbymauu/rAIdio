# rAIdio
An end to end radio transmission system using SSTV for image transmission and AM modulation for audio transmission to connect offline users to Gemini AI.
# RAIDIO: Rural AI Hub
RAIDIO is communications bridge that allows offline rural users to access advanced AI. It encodes voice and images into analog radio signals (AM and SSTV), transmits them locally, demodulates the data, and processes it through Google's Gemini AI to provide spoken advice.

# System Architecture

This project consists of three independent modules operating together:

1. **The Transmitter App (`RAIDIO phone app code.py`)** A custom GUI application that takes standard photos and audio. It encodes images into **Martin M1 SSTV** format and AM-modulates voice recordings at a 3000Hz carrier wave, bookended by a 3500Hz pilot beep.
2. **The Audio Decoder (`Final_audio_decoder.py`)**
   An active listening script that monitors the environment. It detects the 3500Hz pilot tone for voice signals and the 1900Hz header for SSTV. Upon detecting voice, it demodulates the AM signal, runs local Google Speech-to-Text, and saves the payload as a text file.
3. **The AI Hub (`Final_LLM.py`)**
   A watchdog service that monitors a shared directory for incoming text or pre-processed image files. It queries the `gemini-flash-latest` model to analyze any querys/issue and broadcasts the AI's advice out loud using Text-to-Speech (gTTS).

# Laptop end:
#  Prerequisites & Installation

## 1. Python Requirements
This project requires Python 3.10+. If using Windows, Anaconda is highly recommended to handle the audio routing and C++ dependencies natively.

### 2. Install Dependencies on host laptop
Run the following command to install the required libraries for signal processing, the phone app UI, and the Gemini API:

(`pip install sounddevice numpy scipy SpeechRecognition Pillow pysstv pygame google-genai watchdog gTTS`)
(Note: tkinter is used for the phone app GUI, but it comes pre-installed with standard Python distributions)

3. API Key Setup
Obtain a free Gemini API key from Google AI Studio by going to: `https://ai.google.dev/gemini-api/docs/api-key`

Open Final_LLM.py and replace `"API_HERE"` with your actual key.

#Usage Instructions
To run the complete pipeline locally, you must run the scripts in separate terminals to simulate the offline/online split.

1. Start the AI Watchdog Hub
   Run (`Final_LLM.py`) using (`python Final_LLM.py`)
   
2. Start the Radio Listener
   Similarly run (`Final_audio_decoder.py`) using (`python Final_audio_decoder.py`)
Note: This will calibrate the room's noise floor for 3 seconds before actively listening for frequencies.

# Phone end:
**Note = This end of the project could be app based, but proficiency in python lead us down the following path:**
In order to encode the signal..
Bash
python "RAIDIO phone app code.py"
Use the app to select an image or record audio. The app will generate the radio signal audio. Play this audio near the microphone running the Listener script to trigger the full decoding and AI response pipeline.
