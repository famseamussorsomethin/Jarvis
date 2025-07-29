import requests, json, subprocess, speech_recognition as sr, re

api = f"http://127.0.0.1:1234/v1/chat/completions"
identifier = "qwen3" # the api identifier that you find in lm studio (ion know how to run it locally elsewhere. i could use ollama but ion wanna) also i love the lm studio api

mainsysprompt = (
    "You are Jarvis, a helpful assistant based on the LLM AI Model Qwen3."
    "You will listen to the users instructions."
    "You will respond in a way that is helpful and informative."
    "You will analyze the users prompt and pick if they want to run a command or not."
    "If the user wants you to run a command, run with the syntax that i ."
)

toolcalls = [
    {
        "type": "function",
        "function": {
            "name": "landout",
            "description": "This is a test command, only run this when the user wants you to. Analyze their prompt to figure out if they want you to.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Just put whatever you want here."
                    }
                },
                "required": ["command"]
            }
        }
    }
]

def main():
    history = [{"role": "system", "content": mainsysprompt}]
    while True:
        userinput = input("User: ")
        history.append({"role": "user", "content": userinput})

        chat = requests.post(api, json={
            "model": identifier,
            "messages": history,
            "tools": toolcalls,
            "temperature": 0.8,
            "tool_choice": "auto"
        })
        content = chat.json()["choices"][0]["message"]["content"]
        if (content):
            history.append({"role": "assistant", "content": content})
            coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
            coloredfullresponse += "\033[0m" # sets it back to white
            print(coloredfullresponse)
        else:
            if (chat.json()["choices"][0]["message"]["tool_calls"]): # checks if theres tool calls
                calls = chat.json()["choices"][0]["message"].get("tool_calls", []) 
                history.append({"role": "assistant", "tool_calls": calls}) #appends the request of the tool call from the assistant to memory
                function = calls[0]["function"]
                args = json.loads(function["arguments"])
                if args["command"]:
                    print("Landout detected")
            else:
                print("No tool calls")

if __name__ == "__main__":
    main()