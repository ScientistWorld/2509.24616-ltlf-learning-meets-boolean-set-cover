#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: about 100 MB for the upstream benchmark zip
# plus two small GitHub clones.
# Estimated disk usage: about 110 MB without extracting the full benchmark suite.
#
# This script writes to workspace-local paths so a fresh clone can be
# prepared without relying on machine-local caches.

set -euo pipefail

cd /home/user

mkdir -p data/downloads

if [ ! -d data/downloads/LTLf_Learning_Benchmarks ]; then
  git clone --depth 1 https://github.com/SynthesisLab/LTLf_Learning_Benchmarks.git data/downloads/LTLf_Learning_Benchmarks
fi

if [ ! -e data/downloads/benchmarks.zip ]; then
  wget -O data/downloads/benchmarks.zip https://github.com/SynthesisLab/LTLf_Learning_Benchmarks/releases/download/benchmark/benchmarks.zip
fi

if [ ! -e data/paper_benchmark_subset/manifest.json ]; then
  python3 data/prepare_paper_subset.py
fi

if [ ! -d method/Bolt ]; then
  git clone --depth 1 https://github.com/SynthesisLab/Bolt.git method/Bolt
fi
