# RUSplatting: Configuração do Docker e Guia de Pré-processamento de Datasets

---
Este repositório contém o ambiente Dockerizado e o pipeline de pré-processamento para executar o **RUSplatting** (*Underwater 3D Gaussian Splatting* - Splatting Gaussiano 3D Subaquático). Ele suporta tanto datasets de **Visão Esparsa** (*Sparse-View*, que exigem interpolação de frames por IA) quanto datasets de **Visão Densa** (*Dense-View*), incluindo mitigações para treinamento com baixa VRAM.

---

## 🏗️ 1. Estrutura do Projeto

```text
rusplatting-docker/
├── Dockerfile
├── docker-compose.yml
├── scripts/                  # (Opcional) Seus scripts bash de automação
├── host_outputs/             # Pasta mapeada automaticamente para os modelos 3D salvos
└── datasets/
    ├── Submerged3D/          # Datasets esparsos (ex: Cormoran, 20 imagens)
    │   └── Cormoran/
    │       └── input/
    └── brs_container/        # Datasets densos (ex: mais de 1000 imagens)
        └── input/
```

Configure sua máquina host com a seguinte estrutura de diretórios antes de fazer o *build* do contêiner Docker:

## 🐳 2. Configuração do Ambiente Docker

Como o *3D Gaussian Splatting* depende de requisitos extremamente sensíveis (CUDA, PyTorch, compiladores C++ e bibliotecas de interface gráfica), este projeto é totalmente conteinerizado.

### Pré-requisitos

- Docker instalado na sua máquina host.
- NVIDIA Container Toolkit instalado (para permitir que o Docker use a GPU).

### Build e Execução

Abra seu terminal no diretório `rusplatting-docker`.

Faça o *build* do contêiner (isso fará o download do CUDA, PyTorch, compilará as extensões CUDA personalizadas do RUSplatting e instalará ferramentas como `xvfb` para renderização *headless* - sem interface gráfica):

```Bash
docker compose up -d --build
```

Entre no contêiner em execução para rodar seus scripts:

```Bash
docker exec -it rusplatting_env bash
```

> **Nota sobre a Arquitetura da GPU:** Se o build falhar durante a etapa `diff-gaussian-rasterization` com um erro `IndexError`, edite o `Dockerfile` para exportar a arquitetura específica da sua GPU (por exemplo, `export TORCH_CUDA_ARCH_LIST="8.6"` para a série RTX 30).

## 📂 3. Pré-processamento de Datasets

Uma vez dentro do contêiner (`/workspace/RUSplatting`), você deve preparar o seu dataset. As etapas mudam dependendo de quantas imagens você possui.

### Caminho A: Datasets de Visão Esparsa (*Sparse-View* - aprox. 20 imagens)

Para datasets como o Submerged3D, você precisa gerar os frames sobrepostos ausentes para que a IA possa reconstruir a geometria.

**Poses de Câmera:** Execute o COLMAP. (Nota: Como o Docker é *headless*, você deve usar o prefixo `xvfb-run -a` para simular um display para o OpenGL).

```Bash
xvfb-run -a python convert.py -s datasets/Submerged3D/Cormoran
```

**Interpolar & Fazer Upscaling:** Use o RIFE para gerar frames intermediários e o Real-ESRGAN para restaurar a clareza.

```Bash
cd Submerged3D/Cormoran
mkdir -p interpolated_raw
/tools/rife/rife-ncnn-vulkan-20221029-ubuntu/rife-ncnn-vulkan -i input -o interpolated_raw
chmod +x /tools/realesrgan/realesrgan-ncnn-vulkan-20220424-ubuntu/realesrgan-ncnn-vulkan

mkdir -p /workspace/RUSplatting/Submerged3D/Cormoran/upscaled
cd /tools/realesrgan
./realesrgan-ncnn-vulkan -i /workspace/RUSplatting/Submerged3D/Cormoran/interpolated_raw -o /workspace/RUSplatting/Submerged3D/Cormoran/upscaled -n realesrgan-x4plus
```

**Formatar Nomes de Arquivos:** Renomeie as imagens que passaram por upscaling para que os frames interpolados sigam o formato `Nome1_to_Nome2.jpg`.

```Bash
python3 scripts/format_frames.py Submerged3D/Cormoran
```

**Mapas de Profundidade:** Execute o Depth-Anything-V2 para gerar *priors* de profundidade invertidos.

### Caminho B: Datasets de Visão Densa (*Dense-View* - mais de 1.000 imagens)

Para datasets como o `brs_container`, há bastante sobreposição. Pule a interpolação e o upscaling.

**Poses de Câmera:**

```bash
xvfb-run -a python convert.py -s datasets/brs_container
```

**Copiar Imagens:** Crie o diretório `images/` esperado.

```Bash
cp -r datasets/brs_container/input datasets/brs_container/images
```

**Gerar Mapas de Profundidade:**

```Bash
cd /tools/Depth-Anything-V2
python run.py --encoder vitl --img-path /workspace/RUSplatting/datasets/brs_container/images --outdir /workspace/RUSplatting/datasets/brs_container/depthmap --pred-only --grayscale
cd /workspace/RUSplatting
```

**Corrigir Extensões de Profundidade:** Certifique-se de que os mapas de profundidade correspondam à extensão de suas imagens originais usando um script rápido em Python para renomear (o Depth-Anything-V2 força o uso de `.png`).

## 🚀 4. Treinando o Modelo (Guia para Baixa VRAM)

O treinamento requer bastante VRAM (memória da GPU). Se você tem uma GPU com memória limitada (ex: 6GB), a fase de densificação causará travamentos por falta de memória (*Out-Of-Memory - OOM*). Use as seguintes *flags* para evitar isso:

- `-r 8`: Reduz a resolução do treinamento.
- `--data_device cpu`: Mantém as imagens de origem na memória RAM do sistema em vez da VRAM.
- `--densify_grad_threshold 0.0005`: Limita a clonagem de pontos 3D.

**Para Datasets Esparsos (Requer `--adaptive`)**

```Bash
python train.py -s datasets/Submerged3D/Cormoran --adaptive -r 8 --data_device cpu --densify_grad_threshold 0.0005
```

**Para Datasets Densos (NÃO use `--adaptive`)**

```Bash
python train.py -s datasets/brs_container -r 8 --data_device cpu --densify_grad_threshold 0.0005
```

## 📸 5. Renderizando & Extraindo Resultados

Assim que o treinamento for concluído (30.000 iterações), a sua nuvem de pontos 3D `.ply` e os arquivos de configuração serão salvos.

**Renderizando visualizações 2D:**
Se você usou `--data_device cpu` durante o treinamento, certifique-se de que seu script `render.py` foi corrigido para lidar com tensores de CPU (`error_map = torch.abs(image.cpu() - gt.cpu())`). Depois execute:

```Bash
python render.py -m output/<seu-id-de-execucao>
```

**Acessando os Arquivos na sua Máquina Host:**

Como o seu arquivo `docker-compose.yml` mapeia o diretório `output/` do contêiner para `./host_outputs/` no seu computador físico, você não precisa extrair nada manualmente.
Basta verificar a pasta `host_outputs/` na sua máquina local para arrastar e soltar seus arquivos `.ply` em visualizadores web como SuperSplat ou WebGL Gaussian Splat Viewer.