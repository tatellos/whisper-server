# whisper-server

A server to give easy access to the [whisper](https://github.com/openai/whisper) model using browser APIs.

Currently under development is a feature to forward the recognized speech to a language model.

## Usage

1. Specify the model size you need, in [model.py](model/model.py). Note that the large model needs about 12 GB VRAM
2. Create a docker image with the dockerfile, then run it:

```
docker build -t whisper . 
docker run --gpus all whisper:latest
```

The server will now listen on port 80.
