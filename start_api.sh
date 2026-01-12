#!/bin/bash
# IndexTTS2 API Server 启动脚本

set -e

echo "IndexTTS2 API Server 启动脚本"
echo "================================"

# 检查是否安装了uv
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv 包管理器。请先安装 uv:"
    echo "pip install uv"
    exit 1
fi

# 检查模型文件
echo "检查模型文件..."
MODEL_DIR="checkpoints"
REQUIRED_FILES=(
    "config.yaml"
    "gpt.pth"
    "s2mel.pth"
    "bpe.model"
    "wav2vec2bert_stats.pt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$MODEL_DIR/$file" ]; then
        echo "错误: 找不到必需的文件 $MODEL_DIR/$file"
        echo "请确保已下载完整的模型文件。"
        exit 1
    fi
done

echo "✅ 模型文件检查通过"

# 安装API依赖
echo "安装API依赖..."
uv sync --extra api

# 创建必要的目录
mkdir -p uploads outputs

echo "启动API服务器..."
echo "服务器地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动服务器
uv run api_server.py --host 0.0.0.0 --port 8000
