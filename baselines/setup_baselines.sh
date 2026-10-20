#!/bin/bash
# Fetch, patch and build the baselines at the exact versions used in the report, and download their weights.
#   bash baselines/setup_baselines.sh            (run from the repository root, `sgbase` / `mrproj` envs created)
#
# Envs:  sgbase  python 3.11, see baselines/requirements_sgbase.txt (torch 2.7.1+cu128, torch_geometric 2.5.3, ...)
#        mrproj  environment.yml (TEASER++ python bindings are built here)
set -euo pipefail
cd "$(dirname "$0")"
SGBASE=${SGBASE_PY:-$HOME/miniconda3/envs/sgbase/bin/python}
MRPROJ_PIP=${MRPROJ_PIP:-$HOME/miniconda3/envs/mrproj/bin/pip}
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda} TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-7.5}
export PATH=$CUDA_HOME/bin:$PATH

SGALIGNER_SHA=51cd5723513d7e59145d26433ceb3a0b10298748
GEOTR_SHA=9bba3040d2a258b9cb4272293a4eed87d24a9202      # SGAligner's src/GeoTransformer submodule
SGPGM_SHA=233d852cbc8e40de051352da55d49b3e4466461f
TEASER_SHA=52a9c52ee7d4c838c5e8a75458c33178be5bfb70

fetch() {  # fetch REPO SHA DIR
  [ -d "$3" ] && return
  git clone -q "https://github.com/$1.git" "$3" && git -C "$3" checkout -q "$2"
}

# --- SGAligner (+ GeoTransformer submodule over https), patched -------------------------------------------------
fetch sayands/sgaligner $SGALIGNER_SHA sgaligner
[ -f sgaligner/src/GeoTransformer/setup.py ] || { rm -rf sgaligner/src/GeoTransformer; fetch sayands/GeoTransformer $GEOTR_SHA sgaligner/src/GeoTransformer; }
(cd sgaligner && patch -p1 -N < ../patches/sgaligner.patch || true)
(cd sgaligner && "$SGBASE" -m pip install --no-build-isolation third_party/pointnet2_ops_lib/.)
(cd sgaligner/src/GeoTransformer && "$SGBASE" -m pip install --no-build-isolation -e .)

# --- SG-PGM (unmodified; C++ grid-subsampling / radius-search extension built in place) --------------------------
fetch dfki-av/sg-pgm $SGPGM_SHA sg-pgm
(cd sg-pgm && "$SGBASE" setup.py build_ext --inplace)

# --- TEASER++ python bindings into the mrproj env (needs Eigen 3.x, cmake) ---------------------------------------
mkdir -p third_party
fetch MIT-SPARK/TEASER-plusplus $TEASER_SHA third_party/TEASER-plusplus
(cd third_party/TEASER-plusplus && "$MRPROJ_PIP" install --no-build-isolation . -C cmake.define.BUILD_DOC=OFF)

# --- weights -----------------------------------------------------------------------------------------------------
mkdir -p weights
[ -f weights/geotransformer-3dmatch.pth.tar ] || curl -L -o weights/geotransformer-3dmatch.pth.tar \
  https://github.com/qinzheng93/GeoTransformer/releases/download/1.0.0/geotransformer-3dmatch.pth.tar
# SGAligner checkpoint + 3DSSG vocabulary files (obj_attr.pkl, relationships.txt, classes.txt, attributes.txt)
[ -d weights/sgaligner ] || gdown --folder https://drive.google.com/drive/folders/10-JNxWLxPFQ2q6_zY-9HXIO-Qx-vhmmT -O weights/sgaligner
# SG-PGM checkpoint
[ -d weights/sgpgm ] || gdown --folder https://drive.google.com/drive/folders/1E60DFV7uTdvwgIxf6_eTIbayQH7uYZzP -O weights/sgpgm
echo "baselines ready"
