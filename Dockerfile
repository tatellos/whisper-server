FROM nvidia/cuda:11.6.2-cudnn8-devel-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
  build-essential \
  git \
  python3 \
  python3-pip

RUN pip install git+https://github.com/tatellos/whisper.git
RUN pip install "fastapi[all]"
RUN apt-get install -y ffmpeg
RUN pip install aiofiles

WORKDIR app
COPY model /app/model
# preload the model
RUN python3 model/model.py

COPY main.py /app/main.py


ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
