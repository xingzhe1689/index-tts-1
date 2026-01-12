#!/usr/bin/env python3
"""
测试音频文件服务
"""

import requests
import os
from pathlib import Path

def test_audio_service():
    """测试API服务器的音频文件服务"""
    base_url = "http://localhost:8000"

    print("🎵 测试IndexTTS2音频文件服务")
    print("=" * 50)

    # 1. 测试健康检查
    print("1. 测试API服务器健康状态...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            result = response.json()
            print("✅ API服务器运行正常")
            print(f"   状态: {result.get('status', 'unknown')}")
            print(f"   模型加载: {result.get('model_loaded', False)}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到API服务器: {e}")
        print("💡 请确保运行: uv run api_server.py")
        return False

    # 2. 检查outputs目录
    print("\n2. 检查音频文件目录...")
    outputs_dir = Path("outputs")
    if outputs_dir.exists():
        audio_files = list(outputs_dir.glob("*.wav"))
        print(f"✅ outputs目录存在，包含 {len(audio_files)} 个音频文件")
        if audio_files:
            print("   最近的音频文件:")
            for audio_file in sorted(audio_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
                size_mb = audio_file.stat().st_size / (1024 * 1024)
                print(".2f")
    else:
        print("❌ outputs目录不存在")
        print("   运行TTS后会自动创建")

    # 3. 测试音频文件访问
    print("\n3. 测试音频文件访问...")
    if outputs_dir.exists():
        audio_files = list(outputs_dir.glob("*.wav"))
        if audio_files:
            # 取最新的音频文件
            latest_audio = max(audio_files, key=lambda x: x.stat().st_mtime)
            task_id = latest_audio.stem  # 去掉.wav扩展名

            try:
                # 测试不带扩展名的URL（这是API现在返回的格式）
                audio_url = f"{base_url}/audio/{task_id}"
                print(f"   测试访问: {audio_url}")

                # 首先测试HEAD请求
                head_response = requests.head(audio_url, timeout=5)
                print(f"   HEAD请求状态: {head_response.status_code}")

                if head_response.status_code == 200:
                    content_type = head_response.headers.get('content-type', '')
                    content_length = head_response.headers.get('content-length', '0')

                    print("✅ 音频文件HEAD请求成功")
                    print(f"   内容类型: {content_type}")
                    print(f"   文件大小: {int(content_length) / 1024:.1f} KB")

                    # 再测试GET请求下载
                    get_response = requests.get(audio_url, stream=True, timeout=5)
                    if get_response.status_code == 200:
                        print("✅ 音频文件GET请求成功")

                        # 读取前1KB验证文件内容
                        content = get_response.raw.read(1024)
                        if len(content) > 0:
                            # 检查是否是WAV文件（WAV文件以'RIFF'开头）
                            if content.startswith(b'RIFF'):
                                print("✅ 文件内容验证通过（WAV格式）")
                            else:
                                print("⚠️ 文件内容可能不是有效的WAV格式")
                        else:
                            print("⚠️ 无法读取文件内容")

                    else:
                        print(f"❌ GET请求失败: {get_response.status_code}")

                elif head_response.status_code == 405:
                    print("❌ HEAD请求被拒绝（405 Method Not Allowed）")
                    print("   这通常表示API服务器不支持HEAD请求")
                    print("   尝试GET请求...")

                    # 回退到GET请求
                    get_response = requests.get(audio_url, stream=True, timeout=5)
                    if get_response.status_code == 200:
                        content_length = get_response.headers.get('content-length', '0')
                        print("✅ GET请求成功")
                        print(f"   文件大小: {int(content_length) / 1024:.1f} KB")
                    else:
                        print(f"❌ GET请求也失败: {get_response.status_code}")

                else:
                    print(f"❌ 音频文件访问失败: {head_response.status_code}")
                    print(f"   响应: {head_response.text[:200]}...")

            except Exception as e:
                print(f"❌ 音频访问测试失败: {e}")
        else:
            print("   没有音频文件可以测试")
            print("   💡 请先使用TTS API生成一些音频文件")

    print("\n" + "=" * 50)
    print("🎵 音频服务测试完成")
    print("\n🔧 故障排除:")
    print("- 确保API服务器正在运行: uv run api_server.py")
    print("- 检查防火墙是否阻止了8000端口")
    print("- 确认outputs目录存在且包含.wav文件")
    print("- 在浏览器中测试: http://localhost:8000/audio/文件名")

if __name__ == "__main__":
    test_audio_service()
