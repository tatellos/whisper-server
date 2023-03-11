import collections
import datetime as dt
import json
import os
import wikipediaapi
import uuid

import aiofiles as aiofiles
import urllib3
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


PROMPT_API = '''
The answer should be one of api/weather, api/timer, api/wikipedia, api/other.

Question: What is the weather in Tallinn? Answer: api/weather
Question: Set a timer for one minute. Answer: api/timer
Question: Set a timer for 1 hour. Answer: api/timer
Question: How long do bears live?. Answer: api/wikipedia
Question: How are bicycles made?. Answer: api/wikipedia
Question: When was Angela Merkel born? Answer: api/wikipedia
Question: Where do kangaroos live? Answer: api/wikipedia
Question: Who is the President of US? Answer: api/wikipedia

Question: '''


def getWeatherData(location: str):
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}?unitGroup=metric&include=current&key=FFLYWNZAQ4Y6CWEK7N8E342NH&contentType=json".format(location)
    print(url)
    weatherData = requests.get(url).json()

    # Parse the results as JSON
    return str(weatherData['currentConditions'])

def handle_weather (text: str):
    print('Calling api/weather')
    input_text =  text + " \n\n What is this city?"
    city = requests.post(languagemodel_url, data={"text": input_text}).text
    print(city)
    
    input_text = "Weather data:\n" + getWeatherData(city) + '\n\nQuestion:' + text + "\nAnswer:"
    print("Weather call:", input_text)
    response = requests.post(languagemodel_url, data={"text": input_text}).text
    print(response)
    return response

def getWikiPageTitle(text: str):
    PROMPT_SUBJECT = ''' Question: What is the subject?
    
    '''
    input_text =  PROMPT_SUBJECT + text
    subject = requests.post(languagemodel_url, data={"text": input_text}).text
    subject = subject.replace(' ', '+')
    
    url = f"https://en.wikipedia.org/w/api.php?action=opensearch&format=json&search={subject}&limit=1&namespace=0".format(subject)
    print(url)
    wikiData = requests.get(url).json()
    print(wikiData)
    return wikiData[1][0]

def handle_wikipedia (text: str):
    print('Calling api/wikipedia')
    wikiTitle = getWikiPageTitle(text)
    
    page = wikipediaapi.Wikipedia('en').page(wikiTitle)
    
    PROMPT_WIKIPEDIA = page.summary + '\n\n Question: '
    input_text = PROMPT_WIKIPEDIA + text + '\nAnswer:'
    response = requests.post(languagemodel_url, data={"text": input_text}).text

    return f"show_info('{response}')"


def handle_timer (text: str):
    print('Calling api/timer')
    PROMPT_TIMER = '''Question: Set a timer for one minute. Answer: 60
Question: Set a timer for one hour. Answer: 3600
Question: Set a timer for five seconds. Answer: 5
Question: Set a timer fo 5 minutes. Answer: 300
Question: '''
    input_text = PROMPT_TIMER + text + " Answer: "
    response = requests.post(languagemodel_url, data={"text": input_text}).text
    
    return "setTimeout(() => alert('Reminder!'), " + str(int(response) * 1000) + ");"
    
PROMPTS =  {'api/weather': handle_weather,
            'api/wikipedia': handle_wikipedia,
             'api/timer': handle_timer,}


@app.post("/languagemodel")
async def proxy_to_languagemodel(text: TextInJson):
    input_text = PROMPT_API + text.text + " Answer: "
    print("Proxying to languagemodel", input_text )
    # send the input text in a form to the languagemodel
    response = requests.post(languagemodel_url, data={"text": input_text}).text
    print(response)
    try:
        response = PROMPTS[response](text.text)
    except Exception as e:
        print(e)
        print('Error in parsing.')
        # The AI model did not understand the kind of question. Just google the question.
        google_url_query = "+".join(text.text.split(" "))
        response = "window.location.href='https://www.google.com/search?q=" + google_url_query + "';"
    return TextInJson(text=response)


def transcribe(file_name, original_name) -> str:
    print("using tmp file", file_name)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dZ%H-%M-%S")
    for x in whisper.transcribe(model, file_name, verbose=True, language='English'):
        with open(os.path.join("transcriptions", timestamp + "." + original_name + ".txt"), "a") as f:
            f.write(x + "\n")
        yield x + "\n"

    os.remove(file_name)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
