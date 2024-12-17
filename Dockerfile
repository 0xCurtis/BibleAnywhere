# Install Python and pip
RUN sudo apt-get update && \
    sudo apt-get install -y --no-install-recommends python3 python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set pip as the default pip
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,id=q0c0wcscg08480cos4kgkggg-/root/cache/pip,target=/root/.cache/pip \
    pip install --no-cache-dir -r /app/requirements.txt
