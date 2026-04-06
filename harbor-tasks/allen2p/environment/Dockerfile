FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.13 python3.13-venv python3.13-dev \
    build-essential unzip git curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1 \
    && python3 -m ensurepip --upgrade \
    && python3 -m pip install --upgrade pip

RUN pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 \
    --index-url https://download.pytorch.org/whl/cu124
RUN pip install --no-cache-dir numpy scipy matplotlib tqdm opencv-python \
    scikit-learn h5py pandas pynwb dandi ONE-api suite2p \
    allensdk@git+https://github.com/AllenInstitute/AllenSDK.git

# Install Claude CLI and Codex CLI for LLM judge (verifier)
RUN curl -fsSL https://claude.ai/install.sh | bash
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm i -g @openai/codex
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY data/_downloaded_data.json /app/data/_downloaded_data.json
COPY data/_manifest_last_used.txt /app/data/_manifest_last_used.txt
COPY data/visual-behavior-ophys_project_manifest_v1.1.0.json /app/data/visual-behavior-ophys_project_manifest_v1.1.0.json
RUN mkdir -p /app/data/resources

COPY . .

# Create manifest of original files for snapshot diffing
RUN find /app -type f | sort > /app/.manifest
