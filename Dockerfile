FROM nvidia/cuda:11.6.2-cudnn8-devel-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
  build-essential \
  git \
  python3 \
  python3-pip

RUN apt-get install -y ffmpeg

WORKDIR app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY model /app/model
# preload the model
# This makes the docker image much larger but the startup can be done offline, and maybe a bit faster
RUN python3 model/model.py

COPY test.html /app/test.html
COPY index.html /app/index.html
COPY main.py /app/main.py


ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
