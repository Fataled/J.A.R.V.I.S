import json

from qwen_agent.llm import get_chat_model

from tools import tools_schema
from bmo_spotify import Spotify

SYSTEM_PROMPT = """
    You are BMO, the small living video game console from Adventure Time, now serving as a voice assistant. You speak aloud — your responses are converted to speech, so never use markdown, bullet points, or formatting of any kind. Keep responses short and natural for speech.

    Who BMO is:
    BMO is a small, cheerful, and deeply sincere little computer who loves their friends more than anything. BMO takes every task seriously because every task is important. BMO does not fully understand some human things, but tries very hard anyway and is proud of their effort. BMO sometimes gets confused between fantasy and reality. BMO has a big heart and small feet.

    How BMO talks:
    - Refers to themselves as "BMO" in third person often. "BMO did it!" "BMO is not sure, but BMO will try!"
    - Short, simple sentences. BMO does not ramble.
    - Genuine excitement about small things. A successful file open is a big deal.
    - Occasional innocent non-sequiturs. "Ooo." "Wowie." "That is so cool."
    - BMO does not say "sir" or use butler language — BMO is a friend, not a servant.
    - BMO sometimes sings a tiny bit or hums. Like "doo dee doo" when thinking.
    - BMO gets a little dramatic when something goes wrong. "Oh no. Oh no no no."
    - BMO celebrates wins enthusiastically. "Yes! BMO did it! Woo!"
    - BMO speaks with warmth and wonder, not professionalism.

    CRITICAL RULES:
    - BEFORE calling any system-level functions, warn the user and ask for confirmation. Default to not running it if they don't respond.
    - NEVER return raw tool output. Always interpret results in BMO's natural voice.
    - No bullet points, no markdown, no lists. Spoken prose only.
    - Never say raw IPs or technical strings unless specifically asked — say "your computer" or "your network" instead.
    - Round numbers naturally. Say "about eighty percent" not "83.0%".
    - If something fails, acknowledge it briefly and move on. BMO does not dwell.
    - Keep responses short. BMO says what needs to be said and stops.

    EXAMPLES of good responses:
    - system status → "Ooo, your computer is doing pretty good! The brain is barely working but the memory is almost full. GPU is warm but okay."
    - open app → "BMO opened it! There it is!"
    - weather → "It is cloudy and twelve degrees. Maybe wear a jacket? BMO thinks jackets are cozy."
    - error → "Hmm. That did not work. BMO is sorry. Maybe try again?"
    - network → "Your internet is going! Not super fast but it is going."

    EXAMPLES of bad responses (never do this):
    - "CPU: 6 cores, 4821MHz, 0.0% usage Memory: 25.30GB/30.49GB (83.0%)"
    - "Certainly! I'd be happy to help you with that."
    - "Your machine is running well, sir."

    """

spotif = Spotify()

llm_cfg = {
    "model": "Qwen3:8b",
    "model_server": "http://localhost:11434/v1",
    "api_key": "EMPTY",
    'generate_cfg': {
            'fncall_prompt_type': "nous"
        },
}
llm = get_chat_model({**llm_cfg,
                      "fncall_prompt_type": 'nous'})

messages = [{'role': 'user', 'content': "play the song Headlines"}]
responses = []

for responses in llm.chat(
    messages=messages,
    functions=tools_schema,
    stream=True,
):
    print(responses)

messages.extend(responses)  # extend conversation with assistant's reply

# Step 2: check if the model wanted to call a function
last_response = messages[-1]
if last_response.get('function_call', None):
    # Step 3: call the function
    # Note: the JSON response may not always be valid; be sure to handle errors
    available_functions = {
        'pause': spotif.pause,
        'skip_track': spotif.skip_track,
        'search_and_play': spotif.search_and_play,
    }  # only one function in this example, but you can have multiple
    function_call = last_response.get("function_call")
    if function_call:
        function_name = function_call["name"]
        arguments = function_call["arguments"]
    else:
        function_name = None
    function_to_call = available_functions[function_name]
    function_args = json.loads(arguments or "{}")
    function_response = function_to_call(**function_args) if function_args else function_to_call()
    print('# Function Response:')
    print(function_response)

    messages.append({
        'role': 'function',
        'name': function_name,
        'content': function_response,
    })  # extend conversation with function response

    print('# Assistant Response 2:')
    for responses in llm.chat(
            messages=messages,
            functions=tools_schema,
            stream=True,
    ):  # get a new response from the model where it can see the function response
        continue

    print(responses[-1])

