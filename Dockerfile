# FROM nvidia/cuda:12.0.0-runtime-ubuntu22.04
# WORKDIR /app

# RUN apt-get update && apt-get install -y wget git && apt-get clean

# RUN git clone https://github.com/hlky/nataili.git .
# # Check out a specific version of the above repository
# # RUN echo "boto3>=1.21.32">>requirements.txt

# # Download and install Miniconda
# RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
# RUN bash Miniconda3-latest-Linux-x86_64.sh -b -p /miniconda

# # Add miniconda to the PATH
# ENV PATH=/miniconda/bin:$PATH

# # Update conda and install any necessary packages
# RUN conda update --name base --channel defaults conda && \
#     conda env create -f /app/environment.yaml --force && \
#     conda clean -a -y

# # Install conda environment into container so we do not need to install every time.
# ENV ENV_NAME discord-diffusion

# COPY ecs_run.py /app/

# SHELL ["conda", "run", "-n", "discord-diffusion", "/bin/bash", "-c"]

# ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "discord-diffusion", "python", "ecs_run.py"]


FROM golang:1.12-alpine AS build
#Install git
RUN apk add --no-cache git
#Get the hello world package from a GitHub repository
RUN go get github.com/golang/example/hello
WORKDIR /go/src/github.com/golang/example/hello
# Build the project and send the output to /bin/HelloWorld
RUN go build -o /bin/HelloWorld

FROM golang:1.12-alpine
#Copy the build's output binary from the previous build container
COPY --from=build /bin/HelloWorld /bin/HelloWorld
ENTRYPOINT ["/bin/HelloWorld"]