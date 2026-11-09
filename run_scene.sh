#!/usr/bin/env bash
set -euo pipefail
scene_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export GZ_SIM_RESOURCE_PATH="${scene_dir}/models${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
export GZ_PARTITION="${GZ_PARTITION:-inha_songdo_preview}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec gz sim "${scene_dir}/worlds/inha_songdo.sdf" "$@"
