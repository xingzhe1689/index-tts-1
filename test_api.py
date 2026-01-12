#!/usr/bin/env python3
"""
IndexTTS2 API 测试脚本
"""

import requests
import json
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed")
            print(f"   Status: {data['status']}")
            print(f"   Model loaded: {data['model_loaded']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_tts_basic():
    """测试基本TTS功能"""
    print("\nTesting basic TTS...")

    # 检查示例文件是否存在
    voice_file = Path("examples/voice_01.wav")
    if not voice_file.exists():
        print(f"❌ Voice file not found: {voice_file}")
        return False

    try:
        # 准备请求数据
        files = {
            'speaker_audio': open(voice_file, 'rb')
        }

        data = {
            'text': '你好，这是一个API测试。',
            'emo_control_mode': 0,  # 基本模式
            'verbose': True
        }

        # 发送请求
        response = requests.post(f"{API_BASE_URL}/tts", files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            print("✅ TTS request successful")
            print(f"   Task ID: {result['task_id']}")
            print(f"   Message: {result['message']}")

            if result['success']:
                # 下载音频文件
                audio_url = f"{API_BASE_URL}{result['audio_url']}"
                audio_response = requests.get(audio_url)

                if audio_response.status_code == 200:
                    with open('test_output.wav', 'wb') as f:
                        f.write(audio_response.content)
                    print("✅ Audio file downloaded: test_output.wav")
                    return True
                else:
                    print(f"❌ Failed to download audio: {audio_response.status_code}")
                    return False
            else:
                print(f"❌ TTS failed: {result['message']}")
                return False
        else:
            print(f"❌ TTS request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ TTS test error: {e}")
        return False

def test_tts_emotion():
    """测试情感控制功能"""
    print("\nTesting emotion control...")

    voice_file = Path("examples/voice_10.wav")
    emotion_file = Path("examples/emo_sad.wav")

    if not voice_file.exists():
        print(f"❌ Voice file not found: {voice_file}")
        return False

    try:
        files = {
            'speaker_audio': open(voice_file, 'rb')
        }

        data = {
            'text': '酒楼丧尽天良，开始借机竞拍房间，哎，一群蠢货。',
            'emo_control_mode': 1,  # 情感参考音频
            'emo_alpha': 0.9,
            'verbose': True
        }

        if emotion_file.exists():
            files['emotion_audio'] = open(emotion_file, 'rb')

        response = requests.post(f"{API_BASE_URL}/tts", files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            if result['success']:
                audio_url = f"{API_BASE_URL}{result['audio_url']}"
                audio_response = requests.get(audio_url)

                if audio_response.status_code == 200:
                    with open('test_emotion_output.wav', 'wb') as f:
                        f.write(audio_response.content)
                    print("✅ Emotion TTS test passed: test_emotion_output.wav")
                    return True
                else:
                    print(f"❌ Failed to download emotion audio: {audio_response.status_code}")
                    return False
            else:
                print(f"❌ Emotion TTS failed: {result['message']}")
                return False
        else:
            print(f"❌ Emotion TTS request failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Emotion test error: {e}")
        return False

def test_tts_vector():
    """测试情感向量功能"""
    print("\nTesting emotion vector...")

    voice_file = Path("examples/voice_10.wav")
    if not voice_file.exists():
        print(f"❌ Voice file not found: {voice_file}")
        return False

    try:
        files = {
            'speaker_audio': open(voice_file, 'rb')
        }

        data = {
            'text': '哇塞！这个爆率也太高了！欧皇附体了！',
            'emo_control_mode': 2,  # 情感向量
            'emo_vector': json.dumps([0, 0, 0, 0, 0, 0, 0.45, 0]),  # 惊讶和平静
            'use_random': False,
            'verbose': True
        }

        response = requests.post(f"{API_BASE_URL}/tts", files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            if result['success']:
                audio_url = f"{API_BASE_URL}{result['audio_url']}"
                audio_response = requests.get(audio_url)

                if audio_response.status_code == 200:
                    with open('test_vector_output.wav', 'wb') as f:
                        f.write(audio_response.content)
                    print("✅ Vector TTS test passed: test_vector_output.wav")
                    return True
                else:
                    print(f"❌ Failed to download vector audio: {audio_response.status_code}")
                    return False
            else:
                print(f"❌ Vector TTS failed: {result['message']}")
                return False
        else:
            print(f"❌ Vector TTS request failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Vector test error: {e}")
        return False

def main():
    """主测试函数"""
    print("IndexTTS2 API Test Suite")
    print("=" * 50)

    # 等待服务器启动
    print("Waiting for server to start...")
    time.sleep(2)

    # 运行测试
    tests = [
        ("Health Check", test_health),
        ("Basic TTS", test_tts_basic),
        ("Emotion Control", test_tts_emotion),
        ("Emotion Vector", test_tts_vector),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # 输出总结
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print("25")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
