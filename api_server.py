"""
IndexTTS2 API Server
基于FastAPI的自定义TTS API服务器
"""

import os
import tempfile
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

# IndexTTS2 imports
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from indextts.infer_v2 import IndexTTS2

# 全局TTS实例
tts_instance = None

# 创建FastAPI应用
app = FastAPI(
    title="IndexTTS2 API",
    description="IndexTTS2 文本到语音合成API服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class TTSRequest(BaseModel):
    """TTS推理请求模型"""
    text: str = Field(..., description="要合成的文本", min_length=1, max_length=1000)
    emo_control_mode: int = Field(0, description="情感控制模式: 0=同音色参考, 1=情感参考音频, 2=情感向量, 3=情感描述文本", ge=0, le=3)
    emo_alpha: float = Field(1.0, description="情感权重", ge=0.0, le=1.0)
    emo_vector: Optional[List[float]] = Field(None, description="8维情感向量 [高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静]")
    emo_text: Optional[str] = Field(None, description="情感描述文本")
    use_random: bool = Field(False, description="是否启用随机情感采样")
    max_text_tokens_per_segment: int = Field(120, description="每段最大文本token数", ge=50, le=500)
    verbose: bool = Field(False, description="是否启用详细输出")

class TTSResponse(BaseModel):
    """TTS推理响应模型"""
    success: bool = Field(..., description="是否成功")
    audio_url: Optional[str] = Field(None, description="生成的音频文件URL")
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    duration: Optional[float] = Field(None, description="音频时长(秒)")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    model_loaded: bool = Field(..., description="模型是否已加载")
    version: str = Field(..., description="API版本")

# 全局变量
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
STATIC_DIR = Path("static")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

def initialize_tts():
    """初始化TTS模型"""
    global tts_instance
    try:
        model_dir = "checkpoints"
        config_path = os.path.join(model_dir, "config.yaml")

        # 检查必要文件
        required_files = [
            "config.yaml", "gpt.pth", "s2mel.pth", "bpe.model", "wav2vec2bert_stats.pt"
        ]

        for file in required_files:
            if not os.path.exists(os.path.join(model_dir, file)):
                raise FileNotFoundError(f"Required file {file} not found in {model_dir}")

        tts_instance = IndexTTS2(
            cfg_path=config_path,
            model_dir=model_dir,
            use_fp16=True,  # 使用FP16以节省显存
            use_cuda_kernel=False,
            use_deepspeed=False
        )
        return True
    except Exception as e:
        print(f"Failed to initialize TTS: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """启动时初始化模型"""
    if not initialize_tts():
        print("Warning: Failed to initialize TTS model on startup")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        model_loaded=tts_instance is not None,
        version="2.0.0"
    )

@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="要合成的文本"),
    emo_control_mode: int = Form(0, description="情感控制模式"),
    emo_alpha: float = Form(1.0, description="情感权重"),
    emo_vector: Optional[str] = Form(None, description="8维情感向量，JSON格式"),
    emo_text: Optional[str] = Form(None, description="情感描述文本"),
    use_random: bool = Form(False, description="是否启用随机情感采样"),
    max_text_tokens_per_segment: int = Form(120, description="每段最大文本token数"),
    verbose: bool = Form(False, description="是否启用详细输出"),
    speaker_audio: Optional[UploadFile] = File(None, description="说话人参考音频文件，不提供则使用默认文件 uploads/lyq_01.wav"),
    emotion_audio: Optional[UploadFile] = File(None, description="情感参考音频文件")
):
    """文本到语音合成接口"""

    if tts_instance is None:
        raise HTTPException(status_code=503, detail="TTS model not initialized")

    # 生成任务ID
    task_id = str(uuid.uuid4())

    try:
        # 保存上传的音频文件
        speaker_audio_path = None
        emotion_audio_path = None

        # 处理说话人音频
        if speaker_audio:
            # 保存上传的音频文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=UPLOAD_DIR) as temp_file:
                shutil.copyfileobj(speaker_audio.file, temp_file)
                speaker_audio_path = temp_file.name
        else:
            # 使用默认音频文件
            default_audio_path = UPLOAD_DIR / "lyq_01.wav"
            if not default_audio_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"默认说话人音频文件不存在: {default_audio_path}。请上传音频文件或将默认音频文件放置在该路径。"
                )
            speaker_audio_path = str(default_audio_path)

        # 保存情感音频（如果提供）
        if emotion_audio:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=UPLOAD_DIR) as temp_file:
                shutil.copyfileobj(emotion_audio.file, temp_file)
                emotion_audio_path = temp_file.name

        # 解析情感向量
        emo_vector_parsed = None
        if emo_vector:
            try:
                import json
                emo_vector_parsed = json.loads(emo_vector)
                if len(emo_vector_parsed) != 8:
                    raise ValueError("Emotion vector must have 8 elements")
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid emotion vector: {e}")

        # 准备推理参数
        infer_kwargs = {
            "spk_audio_prompt": speaker_audio_path,
            "text": text,
            "emo_alpha": emo_alpha,
            "use_random": use_random,
            "max_text_tokens_per_segment": max_text_tokens_per_segment,
            "verbose": verbose
        }

        # 根据情感控制模式设置参数
        if emo_control_mode == 1 and emotion_audio_path:  # 情感参考音频
            infer_kwargs["emo_audio_prompt"] = emotion_audio_path
        elif emo_control_mode == 2 and emo_vector_parsed:  # 情感向量
            infer_kwargs["emo_vector"] = emo_vector_parsed
        elif emo_control_mode == 3 and emo_text:  # 情感描述文本
            infer_kwargs["use_emo_text"] = True
            infer_kwargs["emo_text"] = emo_text

        # 生成输出路径
        output_path = OUTPUT_DIR / f"{task_id}.wav"

        # 执行推理
        tts_instance.infer(output_path=str(output_path), **infer_kwargs)

        # 添加清理任务（只清理临时文件，不清理默认文件）
        temp_files_to_cleanup = []
        if speaker_audio_path and speaker_audio_path.startswith(str(UPLOAD_DIR)) and "lyq_01.wav" not in speaker_audio_path:
            temp_files_to_cleanup.append(speaker_audio_path)
        if emotion_audio_path:
            temp_files_to_cleanup.append(emotion_audio_path)
        if temp_files_to_cleanup:
            background_tasks.add_task(cleanup_files, *temp_files_to_cleanup)

        return TTSResponse(
            success=True,
            audio_url=f"/audio/{task_id}",
            task_id=task_id,
            message="TTS synthesis completed successfully"
        )

    except Exception as e:
        # 清理临时文件（不清理默认文件）
        if speaker_audio_path and os.path.exists(speaker_audio_path) and "lyq_01.wav" not in speaker_audio_path:
            try:
                os.unlink(speaker_audio_path)
            except Exception as cleanup_error:
                print(f"Failed to cleanup speaker audio: {cleanup_error}")
        if emotion_audio_path and os.path.exists(emotion_audio_path):
            try:
                os.unlink(emotion_audio_path)
            except Exception as cleanup_error:
                print(f"Failed to cleanup emotion audio: {cleanup_error}")

        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")

@app.api_route("/audio/{task_id}", methods=["GET", "HEAD"])
async def get_audio(task_id: str, request: Request):
    """获取生成的音频文件"""
    audio_path = OUTPUT_DIR / f"{task_id}.wav"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    # 获取文件大小
    file_size = audio_path.stat().st_size

    # 对于HEAD请求，只返回头部信息
    if request.method == "HEAD":
        return Response(
            status_code=200,
            headers={
                "content-type": "audio/wav",
                "content-length": str(file_size),
                "accept-ranges": "bytes"
            }
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=f"{task_id}.wav"
    )

def cleanup_files(*file_paths):
    """清理临时文件"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except Exception as e:
                print(f"Failed to cleanup {path}: {e}")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "IndexTTS2 API Server",
        "docs": "/docs",
        "health": "/health",
        "test_page": "/test"
    }

@app.post("/tts/audio")
async def text_to_speech_audio(
    text: str = Form(..., description="要合成的文本"),
    emo_control_mode: int = Form(0, description="情感控制模式"),
    emo_alpha: float = Form(1.0, description="情感权重"),
    emo_vector: Optional[str] = Form(None, description="8维情感向量，JSON格式"),
    emo_text: Optional[str] = Form(None, description="情感描述文本"),
    use_random: bool = Form(False, description="是否启用随机情感采样"),
    max_text_tokens_per_segment: int = Form(120, description="每段最大文本token数"),
    verbose: bool = Form(False, description="是否启用详细输出"),
    speaker_audio: Optional[UploadFile] = File(None, description="说话人参考音频文件"),
    emotion_audio: Optional[UploadFile] = File(None, description="情感参考音频文件")
):
    """
    文本到语音合成接口 - 直接返回音频文件

    这个接口与 /tts 接口类似，但直接返回音频文件而不是JSON响应。
    适用于需要直接获取音频文件的场景。

    参数说明：
    - text: 要合成的文本内容（必填）
    - emo_control_mode: 情感控制模式，0=同音色参考, 1=情感参考音频, 2=情感向量, 3=情感描述文本
    - emo_alpha: 情感权重 (0.0-1.0)
    - emo_vector: 8维情感向量的JSON字符串 [高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静]
    - emo_text: 情感描述文本（如"高兴"、"悲伤"等）
    - use_random: 是否启用随机情感采样
    - speaker_audio: 说话人参考音频文件（可选，不提供则使用默认音频）
    - emotion_audio: 情感参考音频文件（可选）

    返回：音频文件 (audio/wav)
    """

    if tts_instance is None:
        raise HTTPException(status_code=503, detail="TTS model not initialized")

    # 生成任务ID
    task_id = str(uuid.uuid4())

    try:
        # 保存上传的音频文件
        speaker_audio_path = None
        emotion_audio_path = None

        # 处理说话人音频
        if speaker_audio:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=UPLOAD_DIR) as temp_file:
                shutil.copyfileobj(speaker_audio.file, temp_file)
                speaker_audio_path = temp_file.name
        else:
            # 使用默认音频文件
            default_audio_path = UPLOAD_DIR / "lyq_01.wav"
            if not default_audio_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"默认说话人音频文件不存在。请上传音频文件。"
                )
            speaker_audio_path = str(default_audio_path)

        # 保存情感音频（如果提供）
        if emotion_audio:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=UPLOAD_DIR) as temp_file:
                shutil.copyfileobj(emotion_audio.file, temp_file)
                emotion_audio_path = temp_file.name

        # 解析情感向量
        emo_vector_parsed = None
        if emo_vector:
            try:
                import json
                emo_vector_parsed = json.loads(emo_vector)
                if len(emo_vector_parsed) != 8:
                    raise ValueError("Emotion vector must have 8 elements")
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid emotion vector: {e}")

        # 准备推理参数
        infer_kwargs = {
            "spk_audio_prompt": speaker_audio_path,
            "text": text,
            "emo_alpha": emo_alpha,
            "use_random": use_random,
            "max_text_tokens_per_segment": max_text_tokens_per_segment,
            "verbose": verbose
        }

        # 根据情感控制模式设置参数
        if emo_control_mode == 1 and emotion_audio_path:  # 情感参考音频
            infer_kwargs["emo_audio_prompt"] = emotion_audio_path
        elif emo_control_mode == 2 and emo_vector_parsed:  # 情感向量
            infer_kwargs["emo_vector"] = emo_vector_parsed
        elif emo_control_mode == 3 and emo_text:  # 情感描述文本
            infer_kwargs["use_emo_text"] = True
            infer_kwargs["emo_text"] = emo_text

        # 生成输出路径
        output_path = OUTPUT_DIR / f"{task_id}.wav"

        # 执行推理
        tts_instance.infer(output_path=str(output_path), **infer_kwargs)

        # 清理临时文件
        if speaker_audio_path and "lyq_01.wav" not in speaker_audio_path:
            try:
                os.unlink(speaker_audio_path)
            except Exception:
                pass
        if emotion_audio_path:
            try:
                os.unlink(emotion_audio_path)
            except Exception:
                pass

        # 直接返回音频文件
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename=f"{task_id}.wav"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")

@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """测试页面"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IndexTTS2 API 测试页面</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
            font-size: 14px;
        }
        input[type="text"],
        input[type="number"],
        textarea,
        select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="number"]:focus,
        textarea:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
            font-family: inherit;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        button {
            flex: 1;
            padding: 14px 24px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-primary:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .btn-secondary {
            background: #f5f5f5;
            color: #333;
        }
        .btn-secondary:hover {
            background: #e0e0e0;
        }
        .result-section {
            margin-top: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
            display: none;
        }
        .result-section.show {
            display: block;
        }
        .result-section h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 18px;
        }
        audio {
            width: 100%;
            margin-top: 10px;
        }
        .status {
            padding: 12px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 14px;
        }
        .status.loading {
            background: #e3f2fd;
            color: #1976d2;
        }
        .status.success {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .status.error {
            background: #ffebee;
            color: #c62828;
        }
        .advanced-options {
            margin-top: 20px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        .advanced-options h4 {
            margin-bottom: 15px;
            color: #555;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .advanced-content {
            display: none;
        }
        .advanced-content.show {
            display: block;
        }
        .file-input-wrapper {
            position: relative;
            margin-bottom: 10px;
        }
        .file-input-label {
            display: block;
            padding: 10px;
            background: #f5f5f5;
            border: 2px dashed #ccc;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .file-input-label:hover {
            border-color: #667eea;
            background: #f0f0ff;
        }
        .file-input-wrapper input[type="file"] {
            position: absolute;
            left: -9999px;
        }
        .file-name {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>IndexTTS2 API 测试页面</h1>
        <p class="subtitle">文本转语音合成 API 测试工具</p>

        <form id="ttsForm">
            <div class="form-group">
                <label for="text">要合成的文本 *</label>
                <textarea id="text" name="text" required placeholder="请输入要转换为语音的文本内容...">你好，这是一个测试语音。</textarea>
            </div>

            <div class="form-group">
                <label for="emo_control_mode">情感控制模式</label>
                <select id="emo_control_mode" name="emo_control_mode">
                    <option value="0">0 - 同音色参考</option>
                    <option value="1">1 - 情感参考音频</option>
                    <option value="2">2 - 情感向量</option>
                    <option value="3">3 - 情感描述文本</option>
                </select>
            </div>

            <div class="form-group">
                <label for="emo_alpha">情感权重 (0.0 - 1.0)</label>
                <input type="number" id="emo_alpha" name="emo_alpha" value="1.0" min="0" max="1" step="0.1">
            </div>

            <div class="advanced-options">
                <h4 onclick="toggleAdvanced()">
                    <span>高级选项</span>
                    <span id="advancedArrow">▼</span>
                </h4>
                <div class="advanced-content" id="advancedContent">
                    <div class="form-group">
                        <label for="emo_text">情感描述文本</label>
                        <input type="text" id="emo_text" name="emo_text" placeholder="例如：高兴、悲伤、愤怒等">
                    </div>

                    <div class="form-group">
                        <label for="emo_vector">8维情感向量 (JSON格式)</label>
                        <input type="text" id="emo_vector" name="emo_vector" placeholder='[高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静]'>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="use_random" name="use_random">
                            启用随机情感采样
                        </label>
                    </div>

                    <div class="form-group">
                        <label for="max_text_tokens_per_segment">每段最大文本token数</label>
                        <input type="number" id="max_text_tokens_per_segment" name="max_text_tokens_per_segment" value="120" min="50" max="500">
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="verbose" name="verbose">
                            启用详细输出
                        </label>
                    </div>

                    <div class="form-group">
                        <label>说话人参考音频文件 (可选)</label>
                        <div class="file-input-wrapper">
                            <label class="file-input-label" for="speaker_audio">
                                点击选择文件
                                <input type="file" id="speaker_audio" name="speaker_audio" accept="audio/*">
                            </label>
                            <div class="file-name" id="speaker_audio_name"></div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>情感参考音频文件 (可选)</label>
                        <div class="file-input-wrapper">
                            <label class="file-input-label" for="emotion_audio">
                                点击选择文件
                                <input type="file" id="emotion_audio" name="emotion_audio" accept="audio/*">
                            </label>
                            <div class="file-name" id="emotion_audio_name"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="button-group">
                <button type="submit" class="btn-primary" id="submitBtn">生成语音</button>
                <button type="button" class="btn-secondary" onclick="clearForm()">清空</button>
            </div>
        </form>

        <div id="status" class="status" style="display: none;"></div>

        <div id="resultSection" class="result-section">
            <h3>生成的音频</h3>
            <audio id="audioPlayer" controls></audio>
        </div>
    </div>

    <script>
        // 显示文件名
        document.getElementById('speaker_audio').addEventListener('change', function(e) {
            document.getElementById('speaker_audio_name').textContent = e.target.files[0] ? e.target.files[0].name : '';
        });

        document.getElementById('emotion_audio').addEventListener('change', function(e) {
            document.getElementById('emotion_audio_name').textContent = e.target.files[0] ? e.target.files[0].name : '';
        });

        // 切换高级选项
        function toggleAdvanced() {
            const content = document.getElementById('advancedContent');
            const arrow = document.getElementById('advancedArrow');
            content.classList.toggle('show');
            arrow.textContent = content.classList.contains('show') ? '▲' : '▼';
        }

        // 显示状态
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
            statusDiv.style.display = 'block';
        }

        // 清空表单
        function clearForm() {
            document.getElementById('ttsForm').reset();
            document.getElementById('resultSection').classList.remove('show');
            document.getElementById('status').style.display = 'none';
            document.getElementById('speaker_audio_name').textContent = '';
            document.getElementById('emotion_audio_name').textContent = '';
        }

        // 提交表单
        document.getElementById('ttsForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const submitBtn = document.getElementById('submitBtn');
            const resultSection = document.getElementById('resultSection');
            const audioPlayer = document.getElementById('audioPlayer');

            // 禁用按钮
            submitBtn.disabled = true;
            submitBtn.textContent = '生成中...';
            resultSection.classList.remove('show');

            try {
                // 准备表单数据
                const formData = new FormData();
                formData.append('text', document.getElementById('text').value);
                formData.append('emo_control_mode', document.getElementById('emo_control_mode').value);
                formData.append('emo_alpha', document.getElementById('emo_alpha').value);
                formData.append('use_random', document.getElementById('use_random').checked);
                formData.append('max_text_tokens_per_segment', document.getElementById('max_text_tokens_per_segment').value);
                formData.append('verbose', document.getElementById('verbose').checked);

                // 添加可选字段
                const emoText = document.getElementById('emo_text').value;
                if (emoText) formData.append('emo_text', emoText);

                const emoVector = document.getElementById('emo_vector').value;
                if (emoVector) formData.append('emo_vector', emoVector);

                // 添加文件
                const speakerAudio = document.getElementById('speaker_audio').files[0];
                if (speakerAudio) formData.append('speaker_audio', speakerAudio);

                const emotionAudio = document.getElementById('emotion_audio').files[0];
                if (emotionAudio) formData.append('emotion_audio', emotionAudio);

                showStatus('正在生成语音，请稍候...', 'loading');

                // 发送请求
                const response = await fetch('/tts/audio', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText || '请求失败');
                }

                // 获取音频blob
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);

                // 显示音频播放器
                audioPlayer.src = audioUrl;
                resultSection.classList.add('show');
                showStatus('语音生成成功！', 'success');

                // 自动播放
                audioPlayer.play();

            } catch (error) {
                console.error('Error:', error);
                showStatus('错误: ' + error.message, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '生成语音';
            }
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IndexTTS2 API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto reload")

    args = parser.parse_args()

    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
