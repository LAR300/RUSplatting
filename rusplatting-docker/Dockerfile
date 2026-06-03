# Use NVIDIA CUDA 12.1 Development base image
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# Prevent interactive prompts during apt installations
ENV DEBIAN_FRONTEND=noninteractive
# VRAM-saving PyTorch tweak
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

ENV QT_QPA_PLATFORM=offscreen

# 1. Install System Dependencies (COLMAP, Vulkan, Python)
RUN apt-get update && apt-get install -y \
    git wget curl unzip nano colmap xvfb \
    libxcb-xinput0 libxcb-xinerama0 libxcb-cursor-dev qtbase5-dev \
    vulkan-tools libvulkan1 mesa-vulkan-drivers \
    python3 python3-pip python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Map python3 to python
RUN ln -s /usr/bin/python3 /usr/bin/python

# 2. Install PyTorch (Matching CUDA 12.1)
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

WORKDIR /workspace

# 3. Setup Preprocessing Tools (RIFE & Real-ESRGAN)
RUN mkdir -p /tools/rife /tools/realesrgan && \
    wget https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-ubuntu.zip -O rife.zip && \
    unzip rife.zip -d /tools/rife && rm rife.zip && \
    wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip -O realesrgan.zip && \
    unzip realesrgan.zip -d /tools/realesrgan && rm realesrgan.zip

# 4. Setup Depth-Anything-V2 (With the Inversion Patch)
RUN git clone https://github.com/DepthAnything/Depth-Anything-V2 /tools/Depth-Anything-V2 && \
    cd /tools/Depth-Anything-V2 && \
    pip3 install -r requirements.txt && \
    mkdir checkpoints && \
    wget https://huggingface.co/depth-anything/Depth-Anything-V2-Large/resolve/main/depth_anything_v2_vitl.pth -O checkpoints/depth_anything_v2_vitl.pth && \
    sed -i '62a\    depth = 255.0 - depth' run.py

# 5. Clone and Compile RUSplatting
RUN git clone https://github.com/theflash987/RUSplatting /workspace/RUSplatting && \
    cd /workspace/RUSplatting && \
    pip3 install plyfile tqdm scipy wandb opencv-python scikit-learn lpips imageio && \
    export TORCH_CUDA_ARCH_LIST="8.6" && \
    pip3 install ./submodules/diff-gaussian-rasterization --no-build-isolation && \
    pip3 install ./submodules/simple-knn --no-build-isolation

# 6. Apply the Render.py CPU Patch (To prevent device mismatch errors)
RUN sed -i 's/error_map = torch.abs(image - gt)/error_map = torch.abs(image.cpu() - gt.cpu())/g' /workspace/RUSplatting/render.py

# 7. Import Automation Scripts
COPY scripts/ /workspace/RUSplatting/scripts/
RUN chmod +x /workspace/RUSplatting/scripts/*.sh

WORKDIR /workspace/RUSplatting
CMD ["/bin/bash"]
