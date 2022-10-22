1. Specify the model size you need, in [model.py](model/model.py). Note that the large model needs about 12 GB VRAM
2. Create a docker image with the dockerfile, then run it:

```
docker build -t whisper . 
docker run --gpus all whisper:latest
```
