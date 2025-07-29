import speech_recognition as sr

def main():
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"{index}: {name}")

if __name__ == "__main__":
    main()