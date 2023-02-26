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

app = FastAPI()
os.makedirs("transcriptions", exist_ok=True)


@app.get("/")
async def main():
    return HTMLResponse(open("chat.html").read())


@app.get("/transcribe")
async def transcribe_page():
    return HTMLResponse(open("transcribe.html").read())

app.mount("/transcriptions", StaticFiles(directory="transcriptions"), name="transcriptions")


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

@app.post("/languagemodel")
async def proxy_to_languagemodel(text: TextInJson):
    input_text = text.text
    print("Proxying to languagemodel", input_text)
    # send the input text in a form to the languagemodel
    response = requests.post("http://localhost:8000", data={"text": input_text}).text
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
