from __future__ import annotations

FORM_STYLE = """
<style>
/* 表单样式 - 与高保真设计保持一致 */
.form-row { display:flex; gap:8px; align-items:center; margin:10px 0; }
.form-row label { min-width: 88px; font-size: 14px; color: #1f2937; }
.form-input { height: 38px; padding: 9px 10px; border:1px solid #E5E7EB; border-radius:8px; flex:1; background:#fff; }
.form-button { height: 38px; padding: 0 12px; border:1px solid #E5E7EB; border-radius:8px; background:#fff; cursor:pointer; transition: all 0.2s; font-size: 14px; }
.form-button:hover { background:#f3f4f6; }
.form-button:active { background:#e5e7eb; transform: scale(0.98); }
.primary-button { border-color:#2563EB; background:#E6F0FF; color:#2563EB; }
.form-feedback { margin-left: 88px; font-size:13px; color:#2563EB; display:none; }
.form-feedback.is-visible { display:block; }
.debug-info { font-size:11px; color:#666; margin-top:4px; }
.debug-info:not(.debug-mode) { display:none; }

/* 全局重置，确保全屏覆盖 */
html, body, #root, .stApp, .main { 
  margin: 0 !important; 
  padding: 0 !important; 
  box-sizing: border-box !important; 
}

/* 遮罩与弹框样式 - 现代化设计 */
.overlay-backdrop { 
  position: fixed !important; 
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100% !important;
  height: 100% !important;
  background: rgba(0,0,0,0.15) !important; 
  backdrop-filter: blur(8px) !important;
  z-index: 999999 !important; 
  display: flex !important; 
  align-items: center !important; 
  justify-content: center !important; 
  margin: 0 !important;
  padding: 0 !important;
  animation: fadeIn 0.2s ease-out !important;
}

/* 强制锁定滚动 */
.lock-scroll { 
  height: 100% !important; 
  overflow: hidden !important; 
}

/* 覆盖所有可能的父容器样式 */
html.lock-scroll, 
html.lock-scroll body,
html.lock-scroll .stApp,
html.lock-scroll .main,
body.lock-scroll,
body.lock-scroll .stApp,
body.lock-scroll .main,
.stApp.lock-scroll,
.stApp.lock-scroll .main,
.main.lock-scroll {
  height: 100% !important; 
  overflow: hidden !important; 
  position: relative !important;
}

/* 模态框容器 - 确保在所有元素之上 */
.modal-container {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100% !important;
  height: 100% !important;
  background: rgba(0,0,0,0.35) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 1000000 !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* 模态框样式 - 现代化设计 */
.modal { 
  background: rgba(255, 255, 255, 0.95) !important; 
  border: 1px solid rgba(229, 231, 235, 0.8) !important; 
  border-radius: 16px !important; 
  box-shadow: 0 20px 60px rgba(31, 41, 55, 0.15), 0 4px 12px rgba(31, 41, 55, 0.05) !important; 
  padding: 24px !important; 
  width: 380px !important; 
  max-width: calc(100% - 48px) !important; 
  position: relative !important;
  z-index: 1000001 !important;
  margin: 0 !important;
  backdrop-filter: blur(10px) !important;
  animation: modalSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.modal-panel { 
  background: rgba(255, 255, 255, 0.95) !important; 
  border: 1px solid rgba(229, 231, 235, 0.8) !important; 
  border-radius: 16px !important; 
  box-shadow: 0 20px 60px rgba(31, 41, 55, 0.15), 0 4px 12px rgba(31, 41, 55, 0.05) !important; 
  padding: 24px !important; 
  width: 380px !important; 
  max-width: calc(100% - 48px) !important; 
  position: relative !important;
  z-index: 1000001 !important;
  backdrop-filter: blur(10px) !important;
}

.modal-title { 
  font-weight: 600 !important; 
  margin: 0 0 8px !important; 
  font-size: 18px !important; 
  color: #1f2937 !important;
}

.modal-content { 
  margin: 8px 0 12px !important; 
  color: #6b7280 !important; 
  font-size: 14px !important; 
  line-height: 1.4 !important;
}

.modal-actions { 
  display: flex !important; 
  justify-content: flex-end !important; 
  gap: 8px !important; 
  margin-top: 12px !important; 
}

/* 动画效果 */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes modalSlideIn {
  from { 
    opacity: 0; 
    transform: translateY(-20px) scale(0.95); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0) scale(1); 
  }
}

/* 增强按钮样式 */
.return-button {
  border: 1px solid #2563EB !important;
  background: linear-gradient(135deg, #E6F0FF, #D6E8FF) !important;
  color: #2563EB !important;
  border-radius: 10px !important;
  padding: 10px 20px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15) !important;
}

.return-button:hover {
  background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
  color: white !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.25) !important;
}

.return-button:active {
  transform: translateY(0) scale(0.98) !important;
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
}
</style>
"""


def _comprehensive_diagnostic_script() -> str:
    return """
<script>
// 调试模式控制
const DEBUG_MODE = window.location.search.includes('debug=true');
const debugLog = DEBUG_MODE ? console.log : () => {};

debugLog('[XJJ Debug] 脚本开始执行');

(function(){
  // 防止重复绑定
  if (window.__xjjSelectDirectoryBound) { 
    debugLog('[XJJ Debug] 脚本已绑定，跳过');
    return; 
  }
  window.__xjjSelectDirectoryBound = true;
  
  debugLog('[XJJ Debug] 开始查找按钮元素');
  
  // 延迟查找元素，确保DOM完全加载
  function bindEventHandlers() {
    const selectDirButton = document.getElementById('select-directory-button');
    const startMaintainButton = document.getElementById('start-maintain-button');
    const feedback = document.getElementById('select-directory-feedback');
    const input = document.getElementById('scan-directory-input');
    
    debugLog('[XJJ Debug] 元素查找结果:', {
      selectDirButton: selectDirButton,
      startMaintainButton: startMaintainButton,
      feedback: feedback,
      input: input,
      selectDirExists: !!selectDirButton,
      startMaintainExists: !!startMaintainButton,
      feedbackExists: !!feedback,
      inputExists: !!input
    });
    
    if (!selectDirButton || !startMaintainButton) {
      debugLog('[XJJ Debug] 关键按钮元素未找到，DOM可能未完全加载');
      // 重试机制
      setTimeout(bindEventHandlers, 100);
      return;
    }
    
    if (!feedback) {
      debugLog('[XJJ Debug] 反馈元素未找到');
      return;
    }
    
    // 调试信息（仅debug模式显示）
    if (DEBUG_MODE) {
      const debugDiv = document.createElement('div');
      debugDiv.className = 'debug-info debug-mode';
      debugDiv.innerHTML = `
        调试信息: 按钮已找到并绑定事件监听器<br>
        浏览器支持目录选择: ${!!window.showDirectoryPicker}<br>
        用户代理: ${navigator.userAgent.split(' ').pop()}
      `;
      feedback.parentNode.insertBefore(debugDiv, feedback.nextSibling);
    }
    
    debugLog('[XJJ Debug] 开始绑定事件监听器');
    
    // === 目录选择功能 ===
    // 尝试获取目录完整路径的辅助函数
    async function getDirectoryPath(dirHandle) {
      try {
        // 尝试通过 resolve 方法获取路径（实验性功能）
        if (dirHandle.resolve) {
          const path = await dirHandle.resolve();
          return path ? path.join('/') : dirHandle.name;
        }
        
        // 尝试访问 webkitRelativePath（如果可用）
        if (dirHandle.webkitRelativePath) {
          return dirHandle.webkitRelativePath;
        }
        
        // 构造可能的路径信息
        let pathParts = [];
        let current = dirHandle;
        
        // 尝试向上遍历获取路径层级（有限支持）
        while (current && current.name) {
          pathParts.unshift(current.name);
          if (current.parent) {
            current = current.parent;
          } else {
            break;
          }
        }
        
        return pathParts.length > 1 ? pathParts.join('/') : dirHandle.name;
      } catch (e) {
        debugLog('[XJJ Debug] 路径解析失败:', e);
        return dirHandle.name || '未知目录';
      }
    }
    
    // 目录选择按钮事件处理
    const handleDirectorySelect = async function(event) {
      debugLog('[XJJ Debug] 按钮点击事件触发', event);
      
      // 防止事件冒泡和默认行为
      event.preventDefault();
      event.stopPropagation();
      
      const setMessage = (text, isError = false) => {
        debugLog('[XJJ Debug] 设置消息:', text);
        feedback.textContent = text;
        feedback.classList.add('is-visible');
        if (isError) {
          feedback.style.color = '#dc2626';
        } else {
          feedback.style.color = '#2563EB';
        }
      };
      
      // 立即反馈点击
      setMessage('正在处理目录选择...');
      
      if (!window.showDirectoryPicker) {
        debugLog('[XJJ Debug] 浏览器不支持 showDirectoryPicker API');
        setMessage('当前浏览器不支持目录选择API，请手动输入路径。建议使用Chrome 86+或Edge 86+');
        return;
      }
      
      try {
        debugLog('[XJJ Debug] 调用 showDirectoryPicker');
        const dirHandle = await window.showDirectoryPicker({
          mode: 'read'
        });
        
        debugLog('[XJJ Debug] 目录选择结果:', dirHandle);
        
        // 获取目录路径
        const fullPath = await getDirectoryPath(dirHandle);
        debugLog('[XJJ Debug] 解析的完整路径:', fullPath);
        
        if (input) { 
          input.value = fullPath; 
          debugLog('[XJJ Debug] 输入框值已更新:', fullPath);
        }
        setMessage(`✓ 已选择目录: ${dirHandle.name}`);
        
      } catch (error) {
        debugLog('[XJJ Debug] 目录选择出错:', error);
        
        if (error && error.name === 'AbortError') {
          setMessage('用户取消了目录选择');
        } else if (error && error.name === 'NotAllowedError') {
          setMessage('浏览器阻止了目录选择，请检查权限设置', true);
        } else {
          setMessage(`目录选择失败: ${error && error.message ? error.message : '未知错误'}`, true);
        }
      }
    };
    
    // 绑定目录选择事件（防重复绑定）
    if (!selectDirButton._eventBound) {
      selectDirButton.addEventListener('click', handleDirectorySelect, false);
      selectDirButton.addEventListener('touchstart', handleDirectorySelect, false);
      selectDirButton._eventBound = true;
      debugLog('[XJJ Debug] 目录选择按钮事件已绑定');
    }
    
    // === 开始维护功能 ===
    const handleStartMaintain = function(event) {
      debugLog('[XJJ Debug] 开始维护按钮点击事件触发', event);
      
      event.preventDefault();
      event.stopPropagation();
      
      const scanPath = input ? input.value.trim() : '';
      if (!scanPath) {
        alert('请先选择扫描目录路径');
        return;
      }
      
      debugLog('[XJJ Debug] 开始维护流程, 扫描路径:', scanPath);
      
      // 获取其他表单字段
      const tagsInput = document.getElementById('tags-input');
      const logicalPathInput = document.getElementById('logical-path-input');
      const tags = tagsInput ? tagsInput.value.trim() : '';
      const logicalPath = logicalPathInput ? logicalPathInput.value.trim() : '';
      
      // 使用Streamlit的setComponentValue通知后端
      if (window.parent && window.parent.postMessage) {
        window.parent.postMessage({
          type: 'streamlit:setComponentValue',
          value: {
            action: 'start_maintain',
            scan_path: scanPath,
            tags: tags,
            logical_path: logicalPath
          }
        }, '*');
      }
      
      // 显示处理中遮罩
      showProcessingOverlay();
      
      // 模拟处理过程（实际处理由后端完成）
      setTimeout(() => {
        hideProcessingOverlay();
        showCompleteModal();
      }, 3000);
    };
    
    // 绑定开始维护事件（防重复绑定）
    if (!startMaintainButton._eventBound) {
      startMaintainButton.addEventListener('click', handleStartMaintain, false);
      startMaintainButton.addEventListener('touchstart', handleStartMaintain, false);
      startMaintainButton._eventBound = true;
      debugLog('[XJJ Debug] 开始维护按钮事件已绑定');
    }
    
    // === 弹框管理功能 ===
    function showProcessingOverlay() {
      debugLog('[XJJ Debug] 显示处理中遮罩');
      
      // 先清理可能存在的旧模态框
      hideProcessingOverlay();
      
      const overlay = document.createElement('div');
      overlay.id = 'processing-overlay';
      overlay.className = 'overlay-backdrop';
      overlay.innerHTML = `
        <div class="modal" role="dialog" aria-modal="true" aria-label="处理中">
          <div class="modal-title">处理中</div>
          <div class="modal-content">正在维护数据，请稍候…期间无法操作。</div>
        </div>
      `;
      
      // 确保body有正确的样式
      document.body.style.position = 'relative';
      document.body.style.margin = '0';
      document.body.style.padding = '0';
      
      document.body.appendChild(overlay);
      
      // 添加滚动锁定类到所有可能的容器
      document.documentElement.classList.add('lock-scroll');
      document.body.classList.add('lock-scroll');
      
      // 尝试找到并锁定Streamlit容器
      const stApp = document.querySelector('.stApp');
      if (stApp) {
        stApp.classList.add('lock-scroll');
      }
      
      const main = document.querySelector('.main');
      if (main) {
        main.classList.add('lock-scroll');
      }
    }
    
    function hideProcessingOverlay() {
      debugLog('[XJJ Debug] 隐藏处理中遮罩');
      
      const overlay = document.getElementById('processing-overlay');
      if (overlay) {
        overlay.remove();
      }
      
      // 移除滚动锁定类
      document.documentElement.classList.remove('lock-scroll');
      document.body.classList.remove('lock-scroll');
      
      const stApp = document.querySelector('.stApp');
      if (stApp) {
        stApp.classList.remove('lock-scroll');
      }
      
      const main = document.querySelector('.main');
      if (main) {
        main.classList.remove('lock-scroll');
      }
    }
    
    function showCompleteModal() {
      debugLog('[XJJ Debug] 显示维护完成弹框');
      
      // 先清理可能存在的旧模态框
      const existingModal = document.getElementById('complete-modal');
      if (existingModal) {
        existingModal.remove();
      }
      
      const modal = document.createElement('div');
      modal.id = 'complete-modal';
      modal.className = 'overlay-backdrop';
      modal.innerHTML = `
        <div class="modal" role="dialog" aria-modal="true" aria-label="维护完成">
          <div class="modal-title">维护完成</div>
          <div class="modal-content">已完成扫描并自动合并到数据库。</div>
          <div class="modal-actions">
            <button class="return-button" id="return-to-query">返回查询</button>
          </div>
        </div>
      `;
      
      // 确保body有正确的样式
      document.body.style.position = 'relative';
      document.body.style.margin = '0';
      document.body.style.padding = '0';
      
      document.body.appendChild(modal);
      
      // 添加滚动锁定类到所有可能的容器
      document.documentElement.classList.add('lock-scroll');
      document.body.classList.add('lock-scroll');
      
      // 尝试找到并锁定Streamlit容器
      const stApp = document.querySelector('.stApp');
      if (stApp) {
        stApp.classList.add('lock-scroll');
      }
      
      const main = document.querySelector('.main');
      if (main) {
        main.classList.add('lock-scroll');
      }
      
      // 绑定返回查询按钮事件（多层级确保触发）
      function bindReturnButton() {
        const returnBtn = document.getElementById('return-to-query');
        debugLog('[XJJ Debug] 查找返回查询按钮:', returnBtn);
        
        if (returnBtn) {
          // 先移除可能存在的旧事件监听器
          returnBtn.replaceWith(returnBtn.cloneNode(true));
          const newReturnBtn = document.getElementById('return-to-query');
          
          const handleReturn = function(event) {
            debugLog('[XJJ Debug] 返回查询按钮点击事件触发');
            event.preventDefault();
            event.stopPropagation();
            
            // 清理模态框和事件监听器
            const modalElement = document.getElementById('complete-modal');
            if (modalElement) {
              modalElement.remove();
            }
            
            // 移除滚动锁定
            document.documentElement.classList.remove('lock-scroll');
            document.body.classList.remove('lock-scroll');
            
            const stApp = document.querySelector('.stApp');
            if (stApp) {
              stApp.classList.remove('lock-scroll');
            }
            
            const main = document.querySelector('.main');
            if (main) {
              main.classList.remove('lock-scroll');
            }
            
            // 移除ESC事件监听器
            if (modal._escapeHandler) {
              document.removeEventListener('keydown', modal._escapeHandler);
            }
            
            // 路由跳转到查询页面
            debugLog('[XJJ Debug] 执行返回查询操作');
            
            // 尝试使用Streamlit的页面跳转
            if (window.parent && window.parent.postMessage) {
              window.parent.postMessage({
                type: 'streamlit:setQueryParams',
                queryParams: { route: 'query' }
              }, '*');
            }
            
            // 备选方案：直接URL跳转
            setTimeout(() => {
              const url = new URL(window.location);
              url.searchParams.set('route', 'query');
              window.location.href = url.toString();
            }, 100);
          };
          
          // 绑定点击事件
          newReturnBtn.addEventListener('click', handleReturn, { capture: true });
          newReturnBtn.addEventListener('touchstart', handleReturn, { capture: true });
          
          // 添加CSS样式确保按钮可点击
          newReturnBtn.style.cursor = 'pointer';
          newReturnBtn.style.pointerEvents = 'auto';
          
          debugLog('[XJJ Debug] 返回查询按钮事件已绑定');
        } else {
          debugLog('[XJJ Debug] 返回查询按钮未找到，重试...');
          setTimeout(bindReturnButton, 50);
        }
      }
      
      // 立即尝试绑定，并设置重试机制
      bindReturnButton();
      
      // ESC键关闭功能
      const handleEscape = function(event) {
        if (event.key === 'Escape') {
          debugLog('[XJJ Debug] ESC键触发返回查询');
          event.preventDefault();
          event.stopPropagation();
          
          // 清理模态框
          const modalElement = document.getElementById('complete-modal');
          if (modalElement) {
            modalElement.remove();
          }
          
          // 移除滚动锁定
          document.documentElement.classList.remove('lock-scroll');
          document.body.classList.remove('lock-scroll');
          
          const stApp = document.querySelector('.stApp');
          if (stApp) {
            stApp.classList.remove('lock-scroll');
          }
          
          const main = document.querySelector('.main');
          if (main) {
            main.classList.remove('lock-scroll');
          }
          
          // 路由跳转
          const url = new URL(window.location);
          url.searchParams.set('route', 'query');
          window.location.href = url.toString();
        }
      };
      
      document.addEventListener('keydown', handleEscape, { capture: true });
      
      // 保存事件处理器引用以便清理
      modal._escapeHandler = handleEscape;
    }
    
    // 添加视觉反馈测试（仅调试模式）
    if (DEBUG_MODE) {
      [selectDirButton, startMaintainButton].forEach(btn => {
        btn.addEventListener('mouseenter', function() {
          debugLog('[XJJ Debug] 鼠标悬停事件触发:', btn.id);
        });
        
        btn.addEventListener('mousedown', function() {
          debugLog('[XJJ Debug] 鼠标按下事件触发:', btn.id);
        });
      });
    }
    
    debugLog('[XJJ Debug] 所有事件监听器绑定完成');
    
    // 测试按钮是否可点击（仅调试模式）
    if (DEBUG_MODE) {
      [selectDirButton, startMaintainButton].forEach(btn => {
        const computedStyle = window.getComputedStyle(btn);
        debugLog(`[XJJ Debug] 按钮样式检查 (${btn.id}):`, {
          display: computedStyle.display,
          visibility: computedStyle.visibility,
          pointerEvents: computedStyle.pointerEvents,
          zIndex: computedStyle.zIndex,
          position: computedStyle.position
        });
      });
    }
  }
  
  // 立即尝试绑定，同时设置延迟重试
  bindEventHandlers();
  
  // DOM完全加载后再次尝试
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindEventHandlers);
  }
  
  // 额外的延迟确保Streamlit完全渲染
  setTimeout(bindEventHandlers, 500);
  
})();

debugLog('[XJJ Debug] 脚本执行完成');
</script>
"""


def _mobile_style() -> str:
    return """
<style>
@media (max-width: 480px) {
  .form-row { gap:4px; margin:8px 0; }
  .form-input { height:34px; }
  .form-button { height:34px; padding:0 10px; }
  .form-feedback { margin-left: 0; }
}
</style>
"""


def render_mobile_density_styles() -> str:
    return _mobile_style()


def render_maintain_form() -> str:
    return (
        FORM_STYLE
        + _comprehensive_diagnostic_script()
        + """
<div class="form-row">
  <label for="scan-directory-input">扫描目录路径</label>
  <input id="scan-directory-input" class="form-input" placeholder="扫描目录路径，例如：/Volumes/Media/videos" />
  <button class="form-button" type="button" id="select-directory-button">选择目录</button>
</div>
<div id="select-directory-feedback" class="form-feedback" role="status" aria-live="polite"></div>
<div class="form-row">
  <label for="tags-input">标签（可选）</label>
  <input id="tags-input" class="form-input" placeholder="标签（可选），例如：电影, 高清" />
</div>
<div class="form-row" style="display:none;">
  <label for="logical-path-input">逻辑路径（可选）</label>
  <input id="logical-path-input" class="form-input" placeholder="逻辑路径（可选），例如：媒体库/电影/2024" />
</div>
<div class="form-row">
  <button class="form-button primary-button" type="button" id="start-maintain-button">开始维护</button>
</div>
"""
    )


def render_processing_overlay() -> str:
    return (
        FORM_STYLE
        + """
<div class="lock-scroll"></div>
<div class="overlay-backdrop" aria-busy="true" role="presentation">
  <div class="modal" role="dialog" aria-modal="true" aria-label="处理中">
    <div class="modal-title">处理中</div>
    <div class="modal-content">正在维护数据，请稍候…期间无法操作。</div>
  </div>
</div>
"""
    )


def render_complete_modal(title: str = "维护完成", message: str | None = None) -> str:
    msg = message or "已完成维护，按 Esc 关闭并返回查询"
    return (
        FORM_STYLE
        + f"""
<div class="modal" role="dialog" aria-modal="true" tabindex="-1" id="complete-modal">
  <div class="modal-panel" aria-labelledby="complete-title">
    <div id="complete-title" class="modal-title">{title}</div>
    <div class="modal-content">{msg}</div>
    <div class="modal-actions">
      <button class="form-button" id="close-modal">返回查询</button>
    </div>
  </div>
</div>
"""
    )