import datetime as dt
import os
import uuid

import aiofiles as aiofiles
import whisper
from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from model import model

app = FastAPI()
os.makedirs("transcriptions", exist_ok=True)

htmlcontent = """
<body>
<form action="/transcribe" enctype="multipart/form-data" method="post" target="output" 
onSubmit="setTimeout(() => this[0].disabled='disabled', 10)">
<fieldset>
<input name="sound" type="file">
<input type="submit">
</fieldset>
</form>
<iframe name="output" width="90%%" height="400px"></iframe>
<br>When the transcription is done, you can reload the page to find a link to the full transcription.
<ul>
%s
</ul>
</body>
    """


def get_html():
    files = os.listdir("transcriptions")
    files.sort()
    files.reverse()
    links = ["<li><a href='/transcriptions/" + x + "'>" + x + "</a></li>" for x in files]
    return HTMLResponse(htmlcontent % "\n".join(links))


@app.get("/")
async def main():
    return get_html()


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


def transcribe(file_name, original_name) -> str:
    print("using tmp file", file_name)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dZ%H-%M-%S")
    for x in whisper.transcribe(model, file_name, verbose=True):
        with open(os.path.join("transcriptions", timestamp + "." + original_name + ".txt"), "a") as f:
            f.write(x + "\n")
        yield x + "\n"

    os.remove(file_name)
