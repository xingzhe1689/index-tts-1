# IndexTTS2 API 接口文档

## 接口信息

**接口地址：** `/tts/audio`

**请求方法：** `POST`

**Content-Type：** `multipart/form-data`

**功能描述：** 将文本转换为语音，直接返回音频文件（WAV格式）

---

## 请求参数

### 必填参数

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| text | string | 要合成的文本内容 | "你好，欢迎使用语音合成服务" |

### 可选参数

| 参数名 | 类型 | 默认值 | 说明 | 示例值 |
|--------|------|--------|------|--------|
| emo_control_mode | int | 0 | 情感控制模式：0=同音色参考, 1=情感参考音频, 2=情感向量, 3=情感描述文本 | 0 |
| emo_alpha | float | 1.0 | 情感权重（0.0-1.0）| 0.8 |
| emo_vector | string | null | 8维情感向量JSON字符串：[高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静] | "[0.9,0.0,0.0,0.0,0.0,0.0,0.1,0.0]" |
| emo_text | string | null | 情感描述文本 | "高兴" |
| use_random | boolean | false | 是否启用随机情感采样 | false |
| max_text_tokens_per_segment | int | 120 | 每段最大文本token数（50-500）| 120 |
| verbose | boolean | false | 是否启用详细输出 | false |
| speaker_audio | File | null | 说话人参考音频文件（不提供则使用默认音频）| - |
| emotion_audio | File | null | 情感参考音频文件 | - |

---

## 返回信息

### 成功响应

**Content-Type：** `audio/wav`

**响应格式：** 二进制音频流（WAV格式文件）

### 错误响应

**Content-Type：** `text/plain` 或 `application/json`

| HTTP状态码 | 说明 |
|-----------|------|
| 400 | 请求参数错误 |
| 503 | TTS模型未初始化 |
| 500 | 服务器内部错误 |

---

## 调用示例

### cURL 示例

```bash
# 最简单的调用
curl -X POST http://localhost:8000/tts/audio \
  -F "text=你好，这是测试语音"

# 带情感控制
curl -X POST http://localhost:8000/tts/audio \
  -F "text=今天天气真好！" \
  -F "emo_control_mode=3" \
  -F "emo_text=高兴" \
  -F "emo_alpha=0.8"

# 带情感向量
curl -X POST http://localhost:8000/tts/audio \
  -F "text=我非常开心！" \
  -F "emo_control_mode=2" \
  -F "emo_vector=[0.9,0.0,0.0,0.0,0.0,0.0,0.1,0.0]"

# 上传说话人音频
curl -X POST http://localhost:8000/tts/audio \
  -F "text=这是自定义音色的语音" \
  -F "speaker_audio=@/path/to/audio.wav"
```

### Python 示例

```python
import requests

url = "http://localhost:8000/tts/audio"

# 准备数据
data = {
    "text": "你好，这是测试语音",
    "emo_alpha": 1.0,
    "emo_control_mode": 0
}

# 发送请求
response = requests.post(url, data=data)

# 保存音频文件
if response.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(response.content)
    print("语音生成成功！")
else:
    print(f"错误: {response.text}")
```

### JavaScript 示例

```javascript
async function textToSpeech(text) {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('emo_alpha', 1.0);

    const response = await fetch('http://localhost:8000/tts/audio', {
        method: 'POST',
        body: formData
    });

    if (response.ok) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play();
        return audioUrl;
    } else {
        throw new Error('请求失败');
    }
}

// 使用
textToSpeech('你好，这是测试语音');
```

### Node.js 示例

```javascript
const axios = require('axios');
const fs = require('fs');

async function textToSpeech(text) {
    const FormData = require('form-data');
    const form = new FormData();
    form.append('text', text);

    const response = await axios.post(
        'http://localhost:8000/tts/audio',
        form,
        {
            headers: form.getHeaders(),
            responseType: 'arraybuffer'
        }
    );

    fs.writeFileSync('output.wav', response.data);
    console.log('语音生成成功！');
}

textToSpeech('你好，这是测试语音');
```

---

## 注意事项

1. 文本长度限制：最大 1000 个字符
2. 情感向量必须是 8 维数组，每个元素值范围 0.0-1.0
3. 上传的音频文件支持常见格式：wav, mp3, m4a 等
4. 默认使用系统预设的说话人音频，可通过 speaker_audio 参数自定义
5. 返回的音频文件格式为 WAV，采样率由模型决定
6. 建议在生产环境中添加错误处理和重试机制