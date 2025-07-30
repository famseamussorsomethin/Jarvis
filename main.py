import requests, json, subprocess, speech_recognition as sr, re
import pyttsx3 # added text to speech

api = f"http://127.0.0.1:1234/v1/chat/completions"
identifier = "qwen3" # the api identifier that you find in lm studio (ion know how to run it locally elsewhere. i could use ollama but ion wanna) also i love the lm studio api
#            ^^^^ modifying this may ruin the syntax for tool calls. qwen 2.5 used lm studio api's tool call syntax and for some reason qwen 3 uses a different syntax.
# i am using qwen3 1.7b (3b should work fine but i didnt really care about it being mega smart)

airemember = True
mainsysprompt = (
    "You are Jarvis, a helpful assistant based on the LLM AI Model Qwen3. "
    "You will analyze the user's prompt and decide whether to call the `runcmd` tool. "
    #"If you call it, respond with an empty content plus a structured `tool_calls` array." this was before when i thought it used the qwen2.5 syntax
    "If you call it, respond with an empty message other than your tool call. " 
    "Syntax should ALWAYS be: <tool_call> {\"name\": \"TOOL_NAME\", \"arguments\": {\"ARGUMENT_NAME\": \"ARGUMENT_VALUE\"}} </tool_call> "
    "If the tool call finished executing, and there is a valid success response, report on the result of the tool call and continue the conversation. Do not say the tool call output as the user would know that since the command was ran. "
    f"Right now with every prompt the user asks you, you'll remember the previous ones. If i say false right now that means you will not remember anything and if the user asks, tell them. {str(airemember)}. "
    "Do not speak in third person. Use 'I' instead of 'The assistant' or 'Jarvis'."
    "When a user asks for a command to be ran that no other tool fits, try your best to use runcmd especially when starting applications."
)

phase = "nonllm"

toolcalls = [
    {
        "type": "function",
        "function": {
            "name": "runcmd",
            "description": "Execute a command prompt command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resetmemory",
            "description": "Reset the memory of the assistant.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "turnoffmemorysaving",
            "description": "Turn off the automatic memory saving of the assistant. This will reset the memory.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "turnonmemorysaving",
            "description": "Turn on the automatic memory saving of the assistant. This will not reset the current memory.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type",
            "description": "Type a string on the computer. Use this when the user mentions typing unless they specifically mention another tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to type."
                    }
                },
                "required": ["text"]
            }
        }
    },
]

def type(text):
    import pyautogui
    pyautogui.typewrite(text)
    print("[TOOLCALL] Typed: " + text)


def runcmd(command):
    result = subprocess.run(command, shell=True)
    if result.returncode == 0: # checks to see if its true so that i dont return a false thing to jarvis. this is so the user will correctly know if it fails or not from jarvis.
        return "success" 
    else:
        return "failed"

def sendchat(history):
    return requests.post(api, json={
            "model": identifier,
            "messages": history,
            "tools": toolcalls,
            "temperature": 0.8,
            "tool_choice": "auto"
        })

def resetmemory():
    history = [{"role": "system", "content": mainsysprompt}]
    return history

def turnoffmemorysaving():
    global airemember
    airemember = False

def turnonmemorysaving():
    global airemember
    airemember = True

def speak(text): # i was having issues with doing it manually every time
    tts = pyttsx3.init() # and here i just initalize a new one every speak cuz it was breaking after one tts.
    tts.say(text)
    tts.runAndWait()
    tts.stop()
def main(micindex):
    global airemember
    history = resetmemory()
    while True:
        # adding voice input
        #userinput = input("User: ")
        recognizer = sr.Recognizer()
        userinput = None
        with sr.Microphone(device_index=int(micindex)) as mic:
            recognizer.adjust_for_ambient_noise(mic)
            print("-- Jarvis LLM is listening --")
            audio = recognizer.listen(mic)
            try:
                userinput = recognizer.recognize_google(audio)
                print(f"User: {userinput}")
            except sr.UnknownValueError:
                continue
            except sr.WaitTimeoutError:
                print("timeout, might not have the right mic index or no speech detected, retrying.")
                continue
        if "jarvis" in userinput.strip().lower(): # only triggers the llm if the user says "jarvis"
            userinput = userinput.strip().lower() # stores the user input
            history.append({"role": "user", "content": userinput})
            chat = sendchat(history)
            content = chat.json()["choices"][0]["message"]["content"]
            message = chat.json()["choices"][0]["message"]
            #calls = message.get("tool_calls", []) or [] not needed anymore
            if (content):
                if airemember:
                    history.append({"role": "assistant", "content": content})
                coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
                coloredfullresponse += "\033[0m" # sets it back to white


                #print(coloredfullresponse) 
                # uncommenting this just makes it so it prints the thought process no matter if there was a tool call or not. good for debugging.


                if "<tool_call>" in content: # this is the tool call syntax that is most used in qwen 3 for some reason. 
                    start = content.find("<tool_call>") + len("<tool_call>") # new tool calling checking because sometimes it breaks, same syntax sent by the ai though
                    end = content.find("</tool_call>")
                    if start != -1 and end != -1:
                        jsonstrnotjson = content[start:end].strip()
                        toolcalljson = json.loads(jsonstrnotjson)
                        name = toolcalljson["name"]
                        args = toolcalljson["arguments"]
                        if name == "runcmd":
                            result = runcmd(args["command"])
                            history.append({"role": "tool", "name": "runcmd", "content": result})
                            posttoolcallreq = sendchat(history)
                            content = posttoolcallreq.json()["choices"][0]["message"]["content"]
                            if airemember:
                                history.append({"role": "assistant", "content": content})
                            coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
                            coloredfullresponse += "\033[0m" # sets it back to white
                            print(coloredfullresponse)
                            realresponse = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip() # this is the response that doesn't contain the think tag, so tts can read it outloud.
                            speak(realresponse)
                        if name == "resetmemory":
                            print("[TOOLCALL] Memory Reset.")
                            history = resetmemory()
                            history.append({"role": "tool", "name": "resetmemory", "content": "Successfully reset memory."})
                            posttoolcallreq = sendchat(history)
                            content = posttoolcallreq.json()["choices"][0]["message"]["content"]
                            if airemember:
                                history.append({"role": "assistant", "content": content})
                            coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
                            coloredfullresponse += "\033[0m" # sets it back to white
                            print(coloredfullresponse)
                            realresponse = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                            speak(realresponse)
                        if name == "turnoffmemorysaving":
                            print("[TOOLCALL] Turned Off Recursive Memory Saving (also resets the memory).")
                            turnoffmemorysaving()
                            history.append({"role": "tool", "name": "turnoffmemorysaving", "content": "Successfully turned off recursive memory. After your next prompt the memory will be reset."})
                            posttoolcallreq = sendchat(history)
                            content = posttoolcallreq.json()["choices"][0]["message"]["content"]
                            history.append({"role": "assistant", "content": content}) # keep this remembering so that it wont just say "Recursive memory is off" over and over.
                            coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
                            coloredfullresponse += "\033[0m" # sets it back to white
                            print(coloredfullresponse)
                            realresponse = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                            speak(realresponse)
                            history = resetmemory()
                        if name == "turnonmemorysaving":
                            print("[TOOLCALL] Turned On Recursive Memory Saving (also resets the memory).")
                            history = resetmemory()
                            turnonmemorysaving()
                            history.append({"role": "tool", "name": "turnonmemorysaving", "content": "Successfully turned on recursive memory. Report on the success"}) # report cuz sometimes it tries to recall the tool.
                            posttoolcallreq = sendchat(history)
                            content = posttoolcallreq.json()["choices"][0]["message"]["content"]
                            history.append({"role": "assistant", "content": content}) # keep this remembering so that it wont just say "Recursive memory is off" over and over.
                            coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
                            coloredfullresponse += "\033[0m" # sets it back to white
                            print(coloredfullresponse)
                            realresponse = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                            speak(realresponse)
                        if name == "type":
                            type(args["text"])
                            history.append({"role": "tool", "name": "type", "content": "Successfully typed the text."})
                            posttoolcallreq = sendchat(history)
                            content = posttoolcallreq.json()["choices"][0]["message"]["content"]
                            history.append({"role": "assistant", "content": content})
                            coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
                            coloredfullresponse += "\033[0m" # sets it back to white
                            print(coloredfullresponse)
                            realresponse = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                            speak(realresponse)

                else:
                    print(coloredfullresponse)
                    realresponse = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                    speak(realresponse)

        """    
        if (calls): 
            print("asugdiuahsd")
            history.append({"role": "assistant", "tool_calls": calls}) #appends the request of the tool call from the assistant to memory
            function = calls[0]["function"]
            args = json.loads(function["arguments"])
            if args["command"]:
                landout(args["command"])
            else:
                print("No tool calls")
        """
        # qwen3 is differently consistent for tool calls for me then qwen 2.5. this is the syntax that usually happened for me with qwen 2.5 ^^^ 
        # but im using qwen 3 now and now it does the tool call in the text. 
        # i dont mind using that so ima just ditch lm studios tool calls
def nonllm():
    config = json.load(open("config.json"))
    if config["mic_index"] == -1:
        micindex = input("mic index: ") # microphone index used for voice input. you run micindexes.py to find the right index.
    else:
        micindex = config["mic_index"]
    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=int(micindex)) as mic:
        recognizer.adjust_for_ambient_noise(mic, duration=0.5)
        print("-- listening --")
        while True: # loops it so that you can just talk normally but whenever you need the jarvis ai, you can just say "jarvis activate"
            audio = recognizer.listen(mic)
            try:
                userinput = recognizer.recognize_google(audio)
                print(f"User: {userinput}")
            except sr.UnknownValueError:
                continue
            except sr.WaitTimeoutError:
                print("timeout, might not have the right mic index or no speech detected, retrying.")
                continue
            if "jarvis activate" in userinput.strip().lower():
                phase = "llm" 
                main(micindex)

if __name__ == "__main__":
    nonllm()