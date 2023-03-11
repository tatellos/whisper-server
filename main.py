import collections
import datetime as dt
import os
import uuid

import aiofiles as aiofiles
import whisper
from fastapi import FastAPI, UploadFile
import requests
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from model import model

# Read URL of languagemodel from environment variable
languagemodel_url = os.environ.get("LANGUAGEMODEL_URL", "http://127.0.0.1:5000")
app = FastAPI()
os.makedirs("transcriptions", exist_ok=True)
app.mount("/transcriptions", StaticFiles(directory="transcriptions"), name="transcriptions")


@app.get("/")
async def main():
    return HTMLResponse(open("chat.html").read())


@app.get("/transcribe")
async def transcribe_page():
    return HTMLResponse(open("transcribe.html").read())


@app.post("/transcribe")
async def create_upload_file(sound: UploadFile):
    print("Transcribing", sound.filename)
    out_file_path = str(uuid.uuid4())
    async with aiofiles.open(out_file_path, 'wb') as out_file:
        content = await sound.read()
        await out_file.write(content)

    text = transcribe(out_file_path, sound.filename)

    return StreamingResponse(text, media_type="text/plain")


class TextInJson(BaseModel):
    text: str


PROMPT_API = '''The answer should be one of api/weather, api/timer, api/date, api/other.
Question: What is the weather in Tallinn? Answer: api/weather
Question: Set a timer for one minute. Answer: api/timer
Question: Set a timer for 1 hour. Answer: api/timer
Question: What day is it tomorrow? Answer: api/date
Question: What day is it? Answer: api/date
Question: '''



def handle_weather (text: str):
    print('Calling api/weather')
    PROMPT_WEATHER = '''Question: What is the weather in Hamburg? Answer: https://www.wetteronline.de/wetter/Hamburg
Question: What is the weather in Tallinn? Answer: https://www.wetteronline.de/wetter/Tallinn
Question: What is the weather in Hamburg tomorrow? Answer: https://www.wetteronline.de/wettertrend/Hamburg/
Question: '''
    input_text = PROMPT_WEATHER + text + " Answer: "
    response = requests.post(languagemodel_url, data={"text": input_text}).text
    return "window.location.href=" + response+";"


def handle_timer (text: str):
    print('Calling api/timer')
    PROMPT_TIMER = '''Question: Set a timer for one minute. Answer: 60
Question: Set a timer for one hour. Answer: 3600
Question: Set a timer for five seconds. Answer: 5
Question: Set a timer fo 5 minutes. Answer: 300
Question: '''
    input_text = PROMPT_TIMER + text + " Answer: "
    response = requests.post(languagemodel_url, data={"text": input_text}).text
    
    return "setTimeout(() => alert('Reminder!', " + str(int(response) * 1000) + ");"
    
PROMPTS =  {'api/weather': handle_weather,
             'api/timer': handle_timer}


@app.post("/languagemodel")
async def proxy_to_languagemodel(text: TextInJson):
    input_text = PROMPT_API + text.text + " Answer: "
    print("Proxying to languagemodel", input_text )
    # send the input text in a form to the languagemodel
    response = requests.post(languagemodel_url, data={"text": input_text}).text
    print(response)
    try:
        response = PROMPTS[response](text.text)
    except:
        print('Error in parsing.')
        input_text = text.text + " Answer: "
        response = requests.post(languagemodel_url, data={"text": input_text}).text
        response = "fallbackResponse('" + response + "');"
    return TextInJson(text=response)


def transcribe(file_name, original_name) -> str:
    print("using tmp file", file_name)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dZ%H-%M-%S")
    for x in whisper.transcribe(model, file_name, verbose=True):
        with open(os.path.join("transcriptions", timestamp + "." + original_name + ".txt"), "a") as f:
            f.write(x + "\n")
        yield x + "\n"

    os.remove(file_name)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
