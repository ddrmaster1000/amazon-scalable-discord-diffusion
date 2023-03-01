FROM nvidia/cuda:12.0.0-runtime-ubuntu22.04
WORKDIR /app

RUN apt-get update && apt-get install -y wget git libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && apt-get clean

# Download and install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash Miniconda3-latest-Linux-x86_64.sh -b -p /miniconda

# Add miniconda to the PATH
ENV PATH=/miniconda/bin:$PATH

COPY environment.yaml /app/

# Update conda and install any necessary packages
RUN conda update --name base --channel defaults conda && \
    conda env create -f /app/environment.yaml --force -q && \
    conda clean -a -y

# Install conda environment into container so we do not need to install every time.
ENV ENV_NAME discord-diffusion

COPY ecs_run.py /app/

SHELL ["conda", "run", "-n", "discord-diffusion", "/bin/bash", "-c"]

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "discord-diffusion", "python", "ecs_run.py"]