# IndexTTS2 API Server

基于FastAPI的IndexTTS2文本到语音合成API服务。

## 安装依赖

```bash
# 安装包含API服务器的依赖
uv sync --extra api

# 或者安装所有额外功能
uv sync --all-extras
```

## 启动服务器

```bash
# 启动API服务器
uv run api_server.py

# 或者指定主机和端口
uv run api_server.py --host 0.0.0.0 --port 8000

# 开发模式（自动重载）
uv run api_server.py --reload
```

服务器将在 `http://localhost:8000` 启动。

## API文档

启动服务器后，你可以访问以下地址查看API文档：

- **交互式API文档**: http://localhost:8000/docs (Swagger UI)
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## API端点

### 1. 健康检查
- **URL**: `GET /health`
- **描述**: 检查服务状态和模型加载情况

```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "2.0.0"
}
```

### 2. 文本到语音合成
- **URL**: `POST /tts`
- **Content-Type**: `multipart/form-data`
- **描述**: 将文本转换为语音

#### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `text` | string | 是 | 要合成的文本 (1-1000字符) |
| `speaker_audio` | file | 否 | 说话人参考音频文件 (WAV格式)，不提供则使用默认文件 `uploads/lyq_01.wav` |
| `emo_control_mode` | int | 否 | 情感控制模式 (0=同音色参考, 1=情感参考音频, 2=情感向量, 3=情感描述文本) 默认: 0 |
| `emo_alpha` | float | 否 | 情感权重 (0.0-1.0) 默认: 1.0 |
| `emotion_audio` | file | 否 | 情感参考音频文件 (当emo_control_mode=1时必需) |
| `emo_vector` | string | 否 | 8维情感向量JSON字符串 (当emo_control_mode=2时使用) |
| `emo_text` | string | 否 | 情感描述文本 (当emo_control_mode=3时使用) |
| `use_random` | bool | 否 | 是否启用随机情感采样 默认: false |
| `max_text_tokens_per_segment` | int | 否 | 每段最大文本token数 (50-500) 默认: 120 |
| `verbose` | bool | 否 | 是否启用详细输出 默认: false |

#### 情感向量格式
8维向量对应：[高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静]

```json
[0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 0.1]
```

#### 响应格式

```json
{
  "success": true,
  "audio_url": "/audio/12345678-1234-1234-1234-123456789abc",
  "task_id": "12345678-1234-1234-1234-123456789abc",
  "message": "TTS synthesis completed successfully"
}
```

### 3. 获取音频文件
- **URL**: `GET /audio/{task_id}`
- **描述**: 下载生成的音频文件

## 默认音频文件设置

API支持使用默认说话人音频文件，这样就不需要在每次请求时都上传音频文件。

### 设置默认音频文件

1. 将你的默认说话人音频文件命名为 `lyq_01.wav`
2. 将文件放置在 `uploads/lyq_01.wav` 路径
3. 确保文件是WAV格式的音频文件

如果不设置默认文件，API调用时必须提供 `speaker_audio` 参数。

### 示例文件结构
```
project/
├── uploads/
│   └── lyq_01.wav          # 默认说话人音频文件
├── examples/
│   ├── voice_01.wav        # 示例音频文件
│   └── emo_happy.wav       # 示例情感音频文件
└── api_server.py
```

## 异步请求机制

API支持高并发的异步TTS请求处理：

- ✅ **完全异步**: 每个TTS请求独立处理，不阻塞其他请求
- ✅ **即时响应**: 请求完成即刻可播放，无需等待队列
- ✅ **高并发**: 支持同时处理多个用户的欢迎语音生成
- ✅ **智能队列**: 自动排队播放，避免音频重叠

## 使用示例

### Python客户端

```python
import requests

# TTS推理（使用自定义音频）
def tts_request(text, speaker_audio_path=None, emotion_audio_path=None):
    url = "http://localhost:8000/tts"

    files = {}
    if speaker_audio_path:
        files['speaker_audio'] = open(speaker_audio_path, 'rb')

    data = {
        'text': text,
        'emo_control_mode': 1 if emotion_audio_path else 0,  # 使用情感参考音频或默认模式
        'emo_alpha': 0.8
    }

    if emotion_audio_path:
        files['emotion_audio'] = open(emotion_audio_path, 'rb')

    response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        if result['success']:
            # 下载音频文件
            audio_url = f"http://localhost:8000{result['audio_url']}"
            audio_response = requests.get(audio_url)
            with open('output.wav', 'wb') as f:
                f.write(audio_response.content)
            print(f"音频已保存到 output.wav")
        else:
            print(f"合成失败: {result['message']}")
    else:
        print(f"请求失败: {response.status_code}")

# 使用默认说话人音频
def tts_request_default(text, emotion_audio_path=None):
    return tts_request(text, speaker_audio_path=None, emotion_audio_path=emotion_audio_path)

# 使用示例
# 1. 使用自定义说话人音频
tts_request(
    text="你好，这是一个测试。",
    speaker_audio_path="examples/voice_01.wav",
    emotion_audio_path="examples/emo_happy.wav"
)

# 2. 使用默认说话人音频
tts_request_default(
    text="你好，使用默认说话人。",
    emotion_audio_path="examples/emo_sad.wav"
)
```

### cURL示例

```bash
# 使用默认说话人音频
curl -X POST "http://localhost:8000/tts" \
  -F "text=你好，欢迎使用IndexTTS2" \
  -F "emo_control_mode=0" \
  -o response.json

# 使用自定义说话人音频
curl -X POST "http://localhost:8000/tts" \
  -F "text=你好，欢迎使用IndexTTS2" \
  -F "speaker_audio=@examples/voice_01.wav" \
  -F "emo_control_mode=0" \
  -o response.json

# 使用情感控制
curl -X POST "http://localhost:8000/tts" \
  -F "text=哇塞！这个太棒了！" \
  -F "speaker_audio=@examples/voice_10.wav" \
  -F "emotion_audio=@examples/emo_happy.wav" \
  -F "emo_control_mode=1" \
  -F "emo_alpha=0.8" \
  -o response.json

# 使用情感向量
curl -X POST "http://localhost:8000/tts" \
  -F "text=我感到很悲伤。" \
  -F "speaker_audio=@examples/voice_07.wav" \
  -F "emo_control_mode=2" \
  -F 'emo_vector=[0,0,0.8,0,0,0,0,0.2]' \
  -o response.json

# 使用情感描述文本
curl -X POST "http://localhost:8000/tts" \
  -F "text=他突然消失了，让我很担心。" \
  -F "speaker_audio=@examples/voice_12.wav" \
  -F "emo_control_mode=3" \
  -F "emo_text=我吓死我了！你是鬼吗？" \
  -F "emo_alpha=0.6" \
  -o response.json

# 下载生成的音频
curl -O "http://localhost:8000/audio/$(cat response.json | jq -r .task_id).wav"
```

### JavaScript/Node.js示例

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function ttsSynthesis(text, speakerAudioPath = null) {
    const form = new FormData();
    form.append('text', text);
    form.append('emo_control_mode', '0');

    // 如果提供了说话人音频文件，则添加它
    if (speakerAudioPath) {
        form.append('speaker_audio', fs.createReadStream(speakerAudioPath));
    }
    // 否则使用默认的说话人音频文件

    try {
        const response = await axios.post('http://localhost:8000/tts', form, {
            headers: form.getHeaders(),
        });

        if (response.data.success) {
            // 下载音频文件
            const audioResponse = await axios.get(
                `http://localhost:8000${response.data.audio_url}`,
                { responseType: 'stream' }
            );

            audioResponse.data.pipe(fs.createWriteStream('output.wav'));
            console.log('音频已保存到 output.wav');
        }
    } catch (error) {
        console.error('TTS请求失败:', error.response?.data || error.message);
    }
}

// 使用示例
// 1. 使用默认说话人音频
ttsSynthesis('你好，这是一个测试。');

// 2. 使用自定义说话人音频
ttsSynthesis('你好，这是一个测试。', 'examples/voice_01.wav');
```

## 错误处理

API返回标准的HTTP状态码：

- `200`: 成功
- `400`: 请求参数错误
- `404`: 音频文件不存在
- `500`: 服务器内部错误
- `503`: 服务不可用（模型未加载）

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

## 性能考虑

1. **内存管理**: 服务器会自动清理临时上传的文件
2. **并发处理**: 建议根据硬件配置调整并发请求数
3. **GPU优化**: 服务器默认启用FP16推理以节省显存
4. **文件清理**: 生成的音频文件会保留在服务器上，建议定期清理

## 部署建议

### Docker部署

创建 `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装uv
RUN pip install uv

# 安装依赖
RUN uv sync --extra api

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["uv", "run", "api_server.py", "--host", "0.0.0.0"]
```

### 生产部署

```bash
# 使用uvicorn的多个worker
uv run uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4

# 或者使用nginx反向代理
# 配置nginx.conf
server {
    listen 80;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 故障排除

### 常见问题

1. **模型未加载**: 检查checkpoints目录和配置文件
2. **CUDA错误**: 确保CUDA版本兼容 (推荐12.8)
3. **内存不足**: 使用FP16推理或减少并发请求
4. **文件上传失败**: 检查文件格式和大小限制

### 日志查看

服务器会在控制台输出详细的推理日志，包括：
- 模型加载状态
- 推理进度
- 错误信息
- 性能指标
