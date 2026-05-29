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
# Estimated total download size: 100 MB if the optional upstream benchmark zip is fetched.
# Estimated disk usage after extraction: about 2 GB for the optional full benchmark suite.
#
# This script writes to workspace-local paths so a fresh clone can be
# prepared without relying on machine-local caches.

set -euo pipefail

cd /home/user

mkdir -p data/downloads

if [ ! -d data/downloads/LTLf_Learning_Benchmarks ]; then
  git clone --depth 1 https://github.com/SynthesisLab/LTLf_Learning_Benchmarks.git data/downloads/LTLf_Learning_Benchmarks
fi

if [ ! -d method/Bolt ]; then
  git clone --depth 1 https://github.com/SynthesisLab/Bolt.git method/Bolt
fi

# Optional full benchmark release used by the paper. The reproduction scripts
# use the small tracked subset generated in data/selected_benchmarks.
if [ "${DOWNLOAD_FULL_BENCHMARKS:-0}" = "1" ] && [ ! -e data/downloads/benchmarks.zip ]; then
  wget -O data/downloads/benchmarks.zip https://github.com/SynthesisLab/LTLf_Learning_Benchmarks/releases/download/benchmark/benchmarks.zip
fi
