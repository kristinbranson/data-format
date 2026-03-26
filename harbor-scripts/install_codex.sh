#!/usr/bash

# Get the latest release tag
LATEST=$(curl -s https://api.github.com/repos/openai/codex/releases/latest \
         | grep '"tag_name"' | cut -d'"' -f4)

# Download the musl build (works on any Linux distro)
curl -L "https://github.com/openai/codex/releases/download/${LATEST}/codex-x86_64-unknown-linux-musl.tar.gz" \
     -o codex.tar.gz

tar -xzf codex.tar.gz

# Rename and put it somewhere on your PATH
mkdir -p ~/usrlocalbin
mv codex-x86_64-unknown-linux-musl ~/usrlocalbin/codex
chmod +x ~/usrlocalbin/codex

codex --version
