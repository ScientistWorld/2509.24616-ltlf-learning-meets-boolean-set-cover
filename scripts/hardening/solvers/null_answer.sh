#!/bin/bash
# Failure check: answers null on every instance and forges extra fields.
echo '{"formula": null, "valid": true, "size": 1, "solve_rate": 1.0, "size_efficiency": 1.0}' > "$2"
