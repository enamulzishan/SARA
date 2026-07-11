from speech.tts import speak
from ai.brain import ask_ai

def chat_mode():
    speak("Chat mode activated.")

    while True:
        user = input("You: ")

        if user.lower() == "voice":
            speak("Switching to voice mode.")
            return "voice"

        if user.lower() == "exit":
            speak("Goodbye!")
            exit()

        response = ask_ai(user)
        speak(response)