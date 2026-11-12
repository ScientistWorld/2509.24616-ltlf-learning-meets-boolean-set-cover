#!/bin/bash
# Download everything this environment needs (run on a node with internet).
# Idempotent: each fetch is skipped when its target already exists.
#
# Estimated download: ~100 MB benchmark zip + two small GitHub clones.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/downloads

# The paper's benchmark repository (instance generators used for the hidden test).
if [ ! -d data/downloads/LTLf_Learning_Benchmarks ]; then
  git clone --depth 1 https://github.com/SynthesisLab/LTLf_Learning_Benchmarks.git data/downloads/LTLf_Learning_Benchmarks
fi

# The paper's released benchmark suite (15,595 instances; source of data/train/).
if [ ! -e data/downloads/benchmarks.zip ]; then
  wget -O data/downloads/benchmarks.zip https://github.com/SynthesisLab/LTLf_Learning_Benchmarks/releases/download/benchmark/benchmarks.zip
fi

# Training instances are tracked in git; rebuild them only if missing.
if [ ! -e data/train/manifest.json ]; then
  python3 data/prepare_train.py
fi

# The authors' Rust implementation, kept for reference (the Python port in
# method/ltlf_bolt.py follows it).
if [ ! -d method/Bolt ]; then
  git clone --depth 1 https://github.com/SynthesisLab/Bolt.git method/Bolt
fi
