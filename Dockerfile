ARG REGION
FROM 763104351884.dkr.ecr.$REGION.amazonaws.com/huggingface-pytorch-inference-neuronx:1.13.1-transformers4.34.1-neuronx-py310-sdk2.15.0-ubuntu20.04
# Images: https://github.com/aws/deep-learning-containers/blob/master/available_images.md

WORKDIR /app
SHELL ["/bin/bash", "-c"]

RUN python --version
# Upgrade neuron to version >=v0.0.15 for LCM support and Data parallelism https://github.com/huggingface/optimum-neuron/releases/tag/v0.0.15
RUN python -m pip install optimum-neuron diffusers --upgrade --user

COPY ecs-run-inf2.py /app
ENTRYPOINT ["python", "ecs-run-inf2.py"]


# docker build -f DockerfileHug .
# RUN python3 /sd/sdxl_generate.py
# docker container run --device=/dev/neuron0 -it c988e82fb474 /bin/bash