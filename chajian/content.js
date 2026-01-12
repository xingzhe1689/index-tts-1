// 抖音直播新人TTS欢迎插件

(function() {
  'use strict';

  // 存储已处理的用户ID，避免重复提示
  const processedUsers = new Set();

  // TTS API配置
  const TTS_CONFIG = {
    // 可以修改这些地址以匹配你的TTS服务器
    baseUrl: 'http://localhost:8000',
    apiUrl: 'http://localhost:8000/tts',
    healthUrl: 'http://localhost:8000/health',
    enabled: true,  // 是否启用TTS功能
    welcomePrefix: '热烈欢迎',
    welcomeSuffix: '进入直播间',
    autoPlay: true,  // 是否自动播放生成的音频
    playVolume: 0.8  // 播放音量 (0.0-1.0)
  };

  // 音频播放队列
  const audioQueue = {
    queue: [],        // 待播放的音频URL队列
    isPlaying: false, // 当前是否正在播放
    currentAudio: null, // 当前播放的音频对象

    // 添加音频到队列
    add: function(audioUrl, userName) {
      this.queue.push({ url: audioUrl, userName: userName });
      console.log(`🎵 已添加到播放队列: ${userName} (${this.queue.length}个待播放)`);
      console.log(`📋 当前队列顺序: ${this.queue.map(item => item.userName).join(' → ')}`);

      // 显示实时队列状态
      setTimeout(() => showRealtimeQueueStatus(), 100);

      // 如果当前没有在播放，立即开始播放
      if (!this.isPlaying) {
        this.playNext();
      }
    },

    // 播放下一个音频
    playNext: function() {
      if (this.isPlaying || this.queue.length === 0) {
        return;
      }

      const nextItem = this.queue.shift();
      this.playAudio(nextItem.url, nextItem.userName);
    },

    // 播放音频
    playAudio: function(audioUrl, userName) {
      if (!TTS_CONFIG.autoPlay) {
        console.log(`🔇 自动播放已关闭，跳过: ${userName}`);
        return;
      }

      this.isPlaying = true;
      console.log(`🔊 开始播放欢迎语音: ${userName}`);
      console.log(`🔗 音频URL: ${audioUrl}`);

      try {
        this.currentAudio = new Audio(audioUrl);
        this.currentAudio.volume = TTS_CONFIG.playVolume;

        // 等待音频加载完成
        this.currentAudio.addEventListener('canplay', () => {
          console.log(`📀 音频加载完成，开始播放: ${userName}`);
          // 确保没有其他音频在播放
          if (this.isPlaying && this.currentAudio) {
            const playPromise = this.currentAudio.play();
            if (playPromise !== undefined) {
              playPromise.catch(error => {
                console.error(`❌ 音频播放失败 (canplay): ${userName}`, error);
                this.isPlaying = false;
                this.currentAudio = null;
                // 尝试播放下一个
                if (this.queue.length > 0) {
                  this.playNext();
                }
              });
            }
          }
        });

        // 添加加载超时处理（10秒超时）
        const loadTimeout = setTimeout(() => {
          if (this.currentAudio && !this.currentAudio.duration) {
            console.error(`⏰ 音频加载超时: ${userName} (10秒)`);
            this.isPlaying = false;
            this.currentAudio = null;
            // 尝试播放下一个
            if (this.queue.length > 0) {
              this.playNext();
            }
          }
        }, 10000);

        // 播放成功开始
        this.currentAudio.addEventListener('play', () => {
          console.log(`▶️ 正在播放: ${userName}`);
          clearTimeout(loadTimeout); // 清除加载超时
          setTimeout(() => showRealtimeQueueStatus(), 100);
        });

        // 播放结束
        this.currentAudio.addEventListener('ended', () => {
          console.log(`⏹️ 播放完成: ${userName}`);
          this.isPlaying = false;
          this.currentAudio = null;

          // 立即播放队列中的下一个，无延迟
          if (this.queue.length > 0) {
            console.log(`⏭️ 准备播放下一个用户: ${this.queue[0].userName}`);
            this.playNext();
            setTimeout(() => showRealtimeQueueStatus(), 100);
          } else {
            console.log(`📭 播放队列已清空`);
            setTimeout(() => showRealtimeQueueStatus(), 100);
          }
        });

        // 播放错误处理
        this.currentAudio.addEventListener('error', (error) => {
          console.error(`❌ 音频播放失败: ${userName}`, error);
          console.error(`❌ 错误详情:`, this.currentAudio ? this.currentAudio.error : '未知错误');
          console.error(`❌ 音频URL: ${audioUrl}`);
          clearTimeout(loadTimeout); // 清除加载超时
          this.isPlaying = false;
          this.currentAudio = null;

          // 立即尝试播放下一个，不要让错误阻塞队列
          if (this.queue.length > 0) {
            console.log(`⏭️ 跳过失败的音频，继续播放下一个: ${this.queue[0].userName}`);
            this.playNext();
          } else {
            console.log(`📭 播放队列已清空（因播放错误）`);
          }
        });

        // 加载错误处理
        this.currentAudio.addEventListener('abort', () => {
          console.warn(`⚠️ 音频加载被中止: ${userName}`);
        });

        // 注意：播放将在 'canplay' 事件中启动，而不是在这里立即启动
        // 这是为了确保音频完全加载后再开始播放

      } catch (error) {
        console.error(`❌ 创建音频对象失败: ${userName}`, error);
        this.isPlaying = false;
        this.currentAudio = null;
        setTimeout(() => this.playNext(), 1000);
      }
    },

    // 停止当前播放并清空队列
    stop: function() {
      if (this.currentAudio) {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio = null;
      }
      this.isPlaying = false;
      const clearedCount = this.queue.length;
      this.queue = [];
      console.log(`🛑 已停止播放并清空队列（${clearedCount}个待播放项目已清除）`);
    },

    // 获取队列状态
    getStatus: function() {
      const status = {
        queueLength: this.queue.length,
        isPlaying: this.isPlaying,
        currentUser: this.isPlaying ? '正在播放中' : null,
        nextUser: this.queue.length > 0 ? this.queue[0].userName : null,
        queueList: this.queue.map(item => item.userName)
      };

      console.log('🎵 播放队列详细状态:');
      console.log(`   📊 队列长度: ${status.queueLength}`);
      console.log(`   ▶️ 正在播放: ${status.isPlaying ? '是' : '否'}`);
      console.log(`   👤 当前播放: ${status.currentUser || '无'}`);
      console.log(`   ⏭️ 下一位播放: ${status.nextUser || '无'}`);
      if (status.queueList.length > 0) {
        console.log(`   📋 完整队列: ${status.queueList.join(' → ')}`);
      }

      return status;
    }
  };

  // 测试环境兼容性
  function testEnvironmentCompatibility() {
    console.log('🔧 检查环境兼容性...');

    // 检查FormData支持
    try {
      const testFormData = new FormData();
      testFormData.append('test', 'value');
      console.log('✅ FormData 支持正常');
    } catch (error) {
      console.error('❌ FormData 不支持:', error);
      return false;
    }

    // 检查fetch支持
    if (typeof fetch === 'undefined') {
      console.error('❌ fetch API 不支持');
      return false;
    } else {
      console.log('✅ fetch API 支持正常');
    }

    // 检查Audio支持
    try {
      const testAudio = new Audio();
      console.log('✅ Audio API 支持正常');
    } catch (error) {
      console.error('❌ Audio API 不支持:', error);
      return false;
    }

    console.log('🎉 环境兼容性检查通过');
    return true;
  }

  // 测试TTS API连接
  async function testTTSConnection() {
    try {
      console.log('🔍 测试TTS API连接...');
      const response = await fetch(TTS_CONFIG.healthUrl);

      if (response.ok) {
        const result = await response.json();
        console.log('✅ TTS API连接正常:', result);
        return true;
      } else {
        console.error('❌ TTS API响应异常:', response.status, response.statusText);
        return false;
      }
    } catch (error) {
      console.error('❌ TTS API连接失败:', error.message);
      console.error('💡 请确保IndexTTS2 API服务器正在运行 (uv run api_server.py)');
      return false;
    }
  }

  // 等待聊天列表容器加载
  function waitForChatroom() {
    const chatroom = document.querySelector('.webcast-chatroom___list');

    if (chatroom) {
      console.log('✅ 抖音直播新人TTS欢迎插件已启动');
      console.log(`🔊 TTS API: ${TTS_CONFIG.apiUrl}`);
      console.log(`📝 欢迎文案格式: "${TTS_CONFIG.welcomePrefix}[用户名]${TTS_CONFIG.welcomeSuffix}"`);
      console.log(`🔊 自动播放: ${TTS_CONFIG.autoPlay ? '开启' : '关闭'}`);
      console.log(`🔊 播放音量: ${Math.round(TTS_CONFIG.playVolume * 100)}%`);

      // 检查环境兼容性
      if (!testEnvironmentCompatibility()) {
        console.error('❌ 环境兼容性检查失败，插件可能无法正常工作');
        return;
      }

      // 测试TTS API连接
      testTTSConnection();

      startObserving(chatroom);
      // 处理已有的新用户消息
      processExistingMessages(chatroom);
    } else {
      // 如果聊天室还没加载，等待后重试
      setTimeout(waitForChatroom, 1000);
    }
  }

  // 处理已存在的新用户消息
  function processExistingMessages(chatroom) {
    const newItems = chatroom.querySelectorAll('.webcast-chatroom___item_new');
    newItems.forEach(item => {
      processNewUserMessage(item);
    });
  }

  // 开始监听DOM变化
  function startObserving(chatroom) {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          // 检查新增的节点是否是新用户消息
          if (node.nodeType === Node.ELEMENT_NODE) {
            // 如果节点本身是新用户消息
            if (node.classList && node.classList.contains('webcast-chatroom___item_new')) {
              processNewUserMessage(node);
            }
            // 或者包含新用户消息的子节点
            const newItem = node.querySelector && node.querySelector('.webcast-chatroom___item_new');
            if (newItem) {
              processNewUserMessage(newItem);
            }
          }
        });
      });
    });

    // 开始观察聊天列表的子节点变化
    observer.observe(chatroom, {
      childList: true,
      subtree: true
    });

    console.log('👀 开始监听新人进入直播间...');
  }

  // 发送TTS请求（异步版本，立即返回，不等待结果）
  function sendTTSRequestAsync(userName) {
    if (!TTS_CONFIG.enabled) {
      return;
    }

    const text = `${TTS_CONFIG.welcomePrefix}${userName}${TTS_CONFIG.welcomeSuffix}`;

    console.log(`🎤 开始生成欢迎语音: "${text}"`);
    console.log(`🔗 发送TTS请求到: ${TTS_CONFIG.apiUrl} (用户: ${userName})`);

    // 完全异步处理，不阻塞后续操作
    const formData = new FormData();
    formData.append('text', text);
    console.log(`📝 表单数据已准备: text="${text}"`);

    fetch(TTS_CONFIG.apiUrl, {
      method: 'POST',
      body: formData
      // 浏览器会自动设置正确的Content-Type: multipart/form-data
    })
    .then(response => {
      console.log(`📡 TTS响应状态 (${userName}): ${response.status} ${response.statusText}`);

      if (response.ok) {
        return response.json();
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    })
    .then(result => {
      console.log(`📄 TTS响应内容 (${userName}):`, result);

      if (result.success) {
        console.log(`✅ 欢迎语音生成成功 (${userName}): ${result.task_id}`);

        // 将音频添加到播放队列
        if (result.audio_url) {
          const audioUrl = `${TTS_CONFIG.baseUrl}${result.audio_url}`;
          console.log(`🎵 构造音频URL (${userName}): ${audioUrl}`);
          console.log(`🎶 立即添加到播放队列 (${userName})`);

          // 直接添加到播放队列，不等待HEAD请求验证
          audioQueue.add(audioUrl, userName);
        } else {
          console.warn(`⚠️ TTS响应中没有audio_url字段 (${userName})`);
        }
      } else {
        console.error(`❌ TTS请求失败 (${userName}):`, result.message);
      }
    })
    .catch(error => {
      console.error(`❌ TTS请求错误 (${userName}):`, error.message);
      console.error(`❌ 错误详情 (${userName}):`, error);
      console.error(`❌ 错误堆栈 (${userName}):`, error.stack);
    });
  }

  // 处理新用户消息
  function processNewUserMessage(item) {
    try {
      // 获取消息ID（用于去重）
      const dataId = item.getAttribute('data-id');

      if (!dataId || processedUsers.has(dataId)) {
        return;
      }

      // 提取用户名
      const userNameElement = item.querySelector('.v8LY0gZF');
      const actionElement = item.querySelector('.cL385mHb');

      if (userNameElement) {
        const userName = userNameElement.textContent.trim();
        const action = actionElement ? actionElement.textContent.trim() : '进入直播间';

        // 标记为已处理
        processedUsers.add(dataId);

        // 打印到控制台（带颜色和图标）
        console.log(
          `%c🎉 新用户进入`,
          'color: #ff0050; font-size: 14px; font-weight: bold;'
        );
        console.log(
          `%c用户名: ${userName}`,
          'color: #00cc66; font-size: 12px;'
        );
        console.log(
          `%c操作: ${action}`,
          'color: #999; font-size: 12px;'
        );
        console.log(
          `%c时间: ${new Date().toLocaleTimeString()}`,
          'color: #666; font-size: 11px;'
        );
        console.log('-------------------');

        // 发送TTS欢迎请求（异步，不阻塞）
        sendTTSRequestAsync(userName);
      }
    } catch (error) {
      console.error('处理新用户消息时出错:', error);
    }
  }

  // 页面加载完成后启动
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForChatroom);
  } else {
    waitForChatroom();
  }

  // 显示实时队列状态
  function showRealtimeQueueStatus() {
    const status = audioQueue.getStatus();
    console.log('━━━━━━━━━━━━━━━━━━━━ 实时队列状态 ━━━━━━━━━━━━━━━━━━━━');
    console.log(`🎵 队列长度: ${status.queueLength}`);
    console.log(`▶️ 正在播放: ${status.isPlaying ? '是' : '否'}`);
    console.log(`👤 当前播放: ${status.currentUser || '无'}`);
    console.log(`⏭️ 下一位播放: ${status.nextUser || '无'}`);
    if (status.queueList.length > 0) {
      console.log(`📋 完整队列: ${status.queueList.join(' → ')}`);
    } else {
      console.log(`📋 队列状态: 空`);
    }
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    // 每5秒自动更新一次状态（如果队列不为空）
    if (status.queueLength > 0 || status.isPlaying) {
      setTimeout(showRealtimeQueueStatus, 5000);
    }
  }

  // 暴露全局控制函数到控制台
  window.ttsPlugin = {
    // 配置相关
    setApiUrl: function(baseUrl) {
      TTS_CONFIG.baseUrl = baseUrl;
      TTS_CONFIG.apiUrl = `${baseUrl}/tts`;
      TTS_CONFIG.healthUrl = `${baseUrl}/health`;
      console.log(`🔧 API服务器地址已更新为: ${baseUrl}`);
      console.log(`   TTS端点: ${TTS_CONFIG.apiUrl}`);
      console.log(`   健康检查: ${TTS_CONFIG.healthUrl}`);
    },

    getConfig: function() {
      console.log('🔧 当前TTS配置:');
      Object.keys(TTS_CONFIG).forEach(key => {
        console.log(`   ${key}: ${TTS_CONFIG[key]}`);
      });
      return { ...TTS_CONFIG };
    },

    // 获取播放队列状态
    getStatus: function() {
      const status = audioQueue.getStatus();
      console.log('🎵 播放队列状态:');
      console.log(`   队列长度: ${status.queueLength}`);
      console.log(`   正在播放: ${status.isPlaying}`);
      console.log(`   下一位: ${status.currentUser || '无'}`);
      return status;
    },

    // 停止播放并清空队列
    stop: function() {
      audioQueue.stop();
    },

    // 切换自动播放
    toggleAutoPlay: function() {
      TTS_CONFIG.autoPlay = !TTS_CONFIG.autoPlay;
      console.log(`🔊 自动播放已${TTS_CONFIG.autoPlay ? '开启' : '关闭'}`);
      return TTS_CONFIG.autoPlay;
    },

    // 设置播放音量
    setVolume: function(volume) {
      if (volume >= 0 && volume <= 1) {
        TTS_CONFIG.playVolume = volume;
        if (audioQueue.currentAudio) {
          audioQueue.currentAudio.volume = volume;
        }
        console.log(`🔊 播放音量已设置为: ${Math.round(volume * 100)}%`);
        return true;
      } else {
        console.error('❌ 音量必须在0.0-1.0之间');
        return false;
      }
    },

    // 手动播放下一个
    playNext: function() {
      if (audioQueue.queue.length > 0) {
        audioQueue.playNext();
        console.log('▶️ 手动播放下一个');
      } else {
        console.log('📭 播放队列为空');
      }
    },

    // 显示帮助信息
    help: function() {
      console.log('🎵 TTS插件控制台命令:');
      console.log('配置相关:');
      console.log('   ttsPlugin.setApiUrl("http://localhost:8000") - 设置API服务器地址');
      console.log('   ttsPlugin.getConfig()     - 查看当前配置');
      console.log('播放控制:');
      console.log('   ttsPlugin.getStatus()     - 查看播放队列状态');
      console.log('   ttsPlugin.stop()          - 停止播放并清空队列');
      console.log('   ttsPlugin.toggleAutoPlay() - 切换自动播放');
      console.log('   ttsPlugin.setVolume(0.8)  - 设置播放音量(0.0-1.0)');
      console.log('   ttsPlugin.playNext()      - 手动播放下一个');
      console.log('   ttsPlugin.help()          - 显示此帮助信息');
      console.log('');
      console.log('💡 播放队列逻辑说明:');
      console.log('   • 每个TTS请求完成时立即可播放');
      console.log('   • 按请求完成顺序排队播放');
      console.log('   • 同时只播放一个音频，避免重叠');
      console.log('   • 插件会自动显示实时队列状态');
      console.log('');
      console.log('🚨 故障排除:');
      console.log('   1. API服务器是否启动: uv run api_server.py');
      console.log('   2. API地址是否正确: ttsPlugin.setApiUrl("http://你的地址:端口")');
      console.log('   3. 音频文件是否存在: 检查outputs文件夹');
      console.log('   4. 浏览器是否允许自动播放音频');
    }
  };

  // 启动时显示帮助提示
  setTimeout(() => {
    console.log('💡 输入 ttsPlugin.help() 查看可用命令');
  }, 2000);

})();
