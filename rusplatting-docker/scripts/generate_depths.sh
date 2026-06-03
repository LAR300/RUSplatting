#!/bin/bash

# --- CONFIGURATION (Update this to your actual absolute path!) ---
# DATASET_PATH="../RUSplatting/Submerged3D" 
DATASET_PATH="../RUSplatting/brs_container" 
# -----------------------------------------

echo "========================================"
echo "Generating depth maps for: $DATASET_PATH"
echo "========================================"

# Run Depth-Anything-V2 using the vitl (Large) model
python3 run.py \
  --encoder vitl \
  --img-path "$DATASET_PATH/images" \
  --outdir "$DATASET_PATH/depthmap" \
  --pred-only \
  --grayscale
  
echo "Finished $DATASET_PATH!"
echo ""

echo "All depth maps successfully generated!"
