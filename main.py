import requests, json, subprocess, speech_recognition as sr, re

api = f"http://127.0.0.1:1234/v1/chat/completions"
identifier = "qwen3" # the api identifier that you find in lm studio (ion know how to run it locally elsewhere. i could use ollama but ion wanna) also i love the lm studio api
#            ^^^^ modifying this may ruin the syntax for tool calls. qwen 2.5 used lm studio api's tool call syntax and for some reason qwen 3 uses a different syntax.
# i am using qwen3 1.7b (3b should work fine but i didnt really care about it being mega smart)
mainsysprompt = (
    "You are Jarvis, a helpful assistant based on the LLM AI Model Qwen3. "
    "You will analyze the user's prompt and decide whether to call the `runcmd` tool. "
    #"If you call it, respond with an empty content plus a structured `tool_calls` array." this was before when i thought it used the qwen2.5 syntax
    "If you call it, respond with an empty message other than your tool call. " 
    "Syntax should be: <tool_calls> {\"name\": \"TOOL_NAME\", \"arguments\": {\"ARGUMENT_NAME\": \"ARGUMENT_VALUE\"}} </tool_calls> " # i added this just to solidify the new syntax to make sure it doesn't switch up on me
    "If the tool call finished executing, report on the result of the tool call and continue the conversation. Do not say the tool call output as the user would know that since the command was ran."
)

toolcalls = [
    {
        "type": "function",
        "function": {
            "name": "runcmd",
            "description": "Execute a shell command.",
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
    }
]

def runcmd(command):
    subprocess.run(command, shell=True)
    return "success"
def sendchat(history):
    return requests.post(api, json={
            "model": identifier,
            "messages": history,
            "tools": toolcalls,
            "temperature": 0.8,
            "tool_choice": "auto"
        })

def main():
    history = [{"role": "system", "content": mainsysprompt}]
    while True:
        userinput = input("User: ")
        history.append({"role": "user", "content": userinput})
        chat = sendchat(history)
        content = chat.json()["choices"][0]["message"]["content"]
        message = chat.json()["choices"][0]["message"]
        #calls = message.get("tool_calls", []) or [] not needed anymore
        if (content):
            history.append({"role": "assistant", "content": content})
            coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
            coloredfullresponse += "\033[0m" # sets it back to white
            #print(coloredfullresponse) uncommenting this just makes it so it prints the thought process no matter if there was a tool call or not. good for debugging.
            if "<tool_call>" in content: # this is the tool call syntax that is most used in qwen 3 for some reason. 
                match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
                if match:
                    toolcalljson = json.loads(match.group(1))
                    name = toolcalljson["name"]
                    args = toolcalljson["arguments"]
                    if name == "runcmd":
                        result = runcmd(args["command"])
                        history.append({"role": "tool", "name": "runcmd", "content": result})
                        posttoolcallreq = sendchat(history)
                        content = posttoolcallreq.json()["choices"][0]["message"]["content"]
                        history.append({"role": "assistant", "content": content})
                        coloredfullresponse = re.sub(r'<think>(.*?)<\/think>', lambda m: "\033[91m" + m.group(1).strip() + "\033[92m", content, flags=re.DOTALL) # 91 is red, 92 is green
                        coloredfullresponse += "\033[0m" # sets it back to white
                        print(coloredfullresponse)
            else:
                print(coloredfullresponse)
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

if __name__ == "__main__":
    main()