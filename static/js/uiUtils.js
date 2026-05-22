// static/js/uiUtils.js

/**
 * 对HTML特殊字符进行转义。
 * @param {string} unsafe 未转义的字符串。
 * @returns {string} 转义后的字符串。
 */
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') {
        return '';
    }
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

/**
 * 更新状态消息。
 * @param {HTMLElement} element 显示状态消息的HTML元素。
 * @param {string} message 要显示的消息。
 * @param {'info'|'success'|'danger'|'warning'|'secondary'} type 消息类型，用于设置alert样式。
 */
function updateStatusMessage(element, message, type = 'info') {
    if (element) {
        element.textContent = message;
        element.className = `alert alert-${type}`;
        element.style.display = 'block';
    }
}

/**
 * 向日志区域添加消息。
 * @param {HTMLElement} logElement 显示日志的HTML元素 (通常是 <pre>).
 * @param {string} message 要添加的日志消息。
 */
function addLogMessage(logElement, message) {
    if (logElement) {
        logElement.textContent += `${message}\n`;
        logElement.scrollTop = logElement.scrollHeight;
    }
}

/**
 * 重置结果显示区域。
 * @param {object} elements 包含各个UI元素引用的对象。
 * @param {HTMLElement} elements.statusMessageElement 状态消息元素。
 * @param {HTMLElement} elements.logOutputElement 日志输出元素。
 * @param {HTMLElement} [elements.longShareCodeAreaElement] 长分享码区域元素。
 * @param {HTMLElement} [elements.shortShareCodeAreaElement] 短分享码区域元素。
 * @param {HTMLElement} [elements.actionButtonsAreaElement] 操作按钮区域元素。
 */
function resetResultDisplay(elements) {
    if (elements.logOutputElement) elements.logOutputElement.textContent = '';
    if (elements.longShareCodeAreaElement) elements.longShareCodeAreaElement.style.display = 'none';
    if (elements.shortShareCodeAreaElement) elements.shortShareCodeAreaElement.style.display = 'none';
    if (elements.actionButtonsAreaElement) elements.actionButtonsAreaElement.style.display = 'none';
    
    if (elements.statusMessageElement) {
        updateStatusMessage(elements.statusMessageElement, '准备开始...', 'info');
    }
}

/**
 * 将文本复制到剪贴板，并提供用户反馈。
 * @param {HTMLTextAreaElement|HTMLInputElement} textElement 包含要复制文本的元素。
 * @param {HTMLButtonElement} buttonElement 点击的复制按钮元素。
 * @param {string} successHtml 复制成功后按钮上显示的HTML内容 (例如 "<i class='bi bi-clipboard-check'></i> 复制成功")。
 * @param {string} originalButtonHtml 按钮的原始HTML内容。
 */
async function copyToClipboard(textElement, buttonElement, successHtml, originalButtonHtml) {
    if (!textElement || !textElement.value) {
        alert('没有可复制的内容。');
        return;
    }
    
    const originalClasses = Array.from(buttonElement.classList);

    try {
        await navigator.clipboard.writeText(textElement.value);
        if (buttonElement) {
            buttonElement.innerHTML = successHtml; // 使用传入的成功HTML
            setTimeout(() => {
                buttonElement.innerHTML = originalButtonHtml;
            }, 1000); // 成功提示显示1秒
        }
    } catch (err) {
        console.error('复制到剪贴板失败:', err);
        if (buttonElement) {
            buttonElement.innerHTML = `<i class="bi bi-x-circle"></i> 复制失败`; // 固定的失败提示
            const tempOriginalClasses = Array.from(buttonElement.classList); // 复制一份类数组
            buttonElement.classList.remove('btn-secondary', 'btn-primary', 'btn-info'); // 移除原有颜色类
            buttonElement.classList.add('btn-danger'); 
            setTimeout(() => {
                buttonElement.innerHTML = originalButtonHtml;
                buttonElement.className = tempOriginalClasses.join(' '); // 确保恢复原始类
            }, 2000); // 失败提示显示时间稍长
        }
    }
}

/**
 * 下载文件。
 * @param {string} content 文件内容。
 * @param {string} filename 下载时的文件名。
 * @param {HTMLButtonElement} [buttonElement] 可选，触发下载的按钮元素，用于UI反馈。
 * @param {string} [originalButtonHtml] 可选，按钮的原始HTML内容。
 * @param {string} [mimeType='application/octet-stream'] 文件的MIME类型。
 */
function downloadFile(content, filename, buttonElement, originalButtonHtml, mimeType = 'application/octet-stream') {
    if (!content) {
        if (buttonElement && originalButtonHtml) {
            const originalClasses = Array.from(buttonElement.classList);
            buttonElement.innerHTML = `<i class="bi bi-x-circle"></i> 下载失败`;
            buttonElement.classList.remove('btn-primary', 'btn-secondary', 'btn-info');
            buttonElement.classList.add('btn-danger');
             setTimeout(() => {
                buttonElement.innerHTML = originalButtonHtml;
                buttonElement.className = originalClasses.join(' ');
            }, 2000); // 失败提示显示2秒
        }
        return;
    }
    
    let originalClasses;
    if (buttonElement) {
        originalClasses = Array.from(buttonElement.classList);
    }

    try {
        const blob = new Blob([content], { type: mimeType });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
        
        if (buttonElement && originalButtonHtml) {
            buttonElement.innerHTML = `<i class="bi bi-file-earmark-arrow-down-fill"></i> 下载成功`;
            setTimeout(() => {
                buttonElement.innerHTML = originalButtonHtml;
            }, 1000); // 成功提示显示1秒
        }

    } catch (e) {
        console.error("创建下载时出错:", e);
        if (buttonElement && originalButtonHtml) {
            buttonElement.innerHTML = `<i class="bi bi-x-circle"></i> 下载失败`;
            buttonElement.classList.remove('btn-primary', 'btn-secondary', 'btn-info');
            buttonElement.classList.add('btn-danger');
             setTimeout(() => {
                buttonElement.innerHTML = originalButtonHtml;
                if(originalClasses) buttonElement.className = originalClasses.join(' ');
            }, 2000); // 失败提示显示2秒
        }
    }
}

/**
 * 显示操作按钮和相关的分享码区域。
 * @param {object} data API成功响应中解析出的数据。
 * @param {object} elements 包含UI元素引用的对象。
 * @param {HTMLElement} elements.actionButtonsAreaElement 操作按钮区域。
 * @param {HTMLElement} [elements.longShareCodeAreaElement] 长分享码区域。
 * @param {HTMLTextAreaElement} [elements.shareCodeOutputElement] 长分享码输出框。
 * @param {HTMLElement} [elements.copyShareCodeBtnElement] 复制长分享码按钮。
 * @param {HTMLElement} [elements.downloadShareCodeBtnElement] 下载分享码按钮。
 * @param {HTMLElement} [elements.shortShareCodeAreaElement] 短分享码区域。
 * @param {HTMLTextAreaElement} [elements.shortShareCodeOutputElement] 短分享码输出框。
 * @param {HTMLElement} [elements.copyShortShareCodeBtnElement] 复制短分享码按钮。
 * @param {boolean} generateShortCodeChecked 指示用户是否勾选了“生成短分享码”。
 * @returns {string|null} 返回长分享码数据，如果没有则为null。
 */
function displayShareCodesAndActions(data, elements, generateShortCodeChecked) {
    let longShareData = null;
    elements.actionButtonsAreaElement.style.display = 'flex'; // 改为 flex 以应用 action-button-row 样式

    // 总是尝试显示长码按钮和下载按钮，如果 data 中没有 longShareCode，它们在 downloadFile 时会处理
    if (elements.copyShareCodeBtnElement) elements.copyShareCodeBtnElement.style.display = 'flex'; // flex item
    if (elements.downloadShareCodeBtnElement) elements.downloadShareCodeBtnElement.style.display = 'flex'; // flex item

    if (data.longShareCode) {
        longShareData = data.longShareCode;
        if (elements.shareCodeOutputElement) elements.shareCodeOutputElement.value = longShareData;
        if (elements.longShareCodeAreaElement) elements.longShareCodeAreaElement.style.display = 'block';
    } else {
        // 如果没有长分享码，则隐藏文本区域，但按钮可能仍可见（由上面逻辑决定，或在 downloadFile 中处理）
        if (elements.longShareCodeAreaElement) elements.longShareCodeAreaElement.style.display = 'none';
        // 也可能需要禁用按钮或改变其文本
        // if (elements.copyShareCodeBtnElement) elements.copyShareCodeBtnElement.disabled = true;
        // if (elements.downloadShareCodeBtnElement) elements.downloadShareCodeBtnElement.disabled = true;
    }

    if (generateShortCodeChecked && data.shortShareCode) {
        if (elements.shortShareCodeOutputElement) elements.shortShareCodeOutputElement.value = data.shortShareCode;
        if (elements.shortShareCodeAreaElement) elements.shortShareCodeAreaElement.style.display = 'block';
        if (elements.copyShortShareCodeBtnElement) elements.copyShortShareCodeBtnElement.style.display = 'flex'; // flex item
    } else {
        if (elements.shortShareCodeAreaElement) elements.shortShareCodeAreaElement.style.display = 'none';
        if (elements.copyShortShareCodeBtnElement) elements.copyShortShareCodeBtnElement.style.display = 'none';
    }

    // 特殊处理：如果只有下载和长码复制，短码按钮隐藏，确保它们仍然能平分宽度
    // （这部分可以通过CSS的flex-grow来处理，只要按钮是flex项）
    // 如果只有长码按钮和下载按钮可见
    const shortBtnVisible = elements.copyShortShareCodeBtnElement && elements.copyShortShareCodeBtnElement.style.display !== 'none';
    if (!shortBtnVisible) {
        // 如果短码按钮不可见，长码和下载按钮应该平分空间。
        // flex-grow: 1 应该已经处理了这一点。
    }

    return longShareData;
}

// --- 新增IP区域检查功能 (JSONP 版本) ---
let geoCheckPromise = null; // 用于存储Promise的状态，避免重复请求

/**
 * 检查IP是否为中国大陆地区（客户端，使用JSONP）。
 * @returns {Promise<boolean>} True: 支持 (境外IP或港澳台或API请求失败), False: 不支持 (中国大陆IP)。
 */
function isAvailableRegionJS() {
    // 如果已经有正在进行的检查，则返回该Promise
    if (geoCheckPromise) {
        return geoCheckPromise;
    }

    geoCheckPromise = new Promise((resolve) => {
        // 定义一个全局回调函数，JSONP脚本加载后会调用它
        window.jsonpGeoCallback = function(ip, location, asn, org) {
            // console.log("JSONP地理位置信息:", ip, location, asn, org); // 中文注释
            // 清理全局回调函数，避免内存泄漏和冲突
            delete window.jsonpGeoCallback;
            // 从DOM中移除JSONP的script标签
            const scriptTag = document.getElementById('jsonpGeoScript');
            if (scriptTag) {
                scriptTag.remove();
            }

            if (typeof location !== 'string') {
                console.warn("JSONP回调: location参数不是字符串, 默认为允许访问。"); // 中文注释
                resolve(true);
                return;
            }
            
            // 检查 location 字符串是否包含"中国"并且不包含"香港", "澳门", "台湾"
            if (location.includes("中国") && 
                !["香港", "澳门", "台湾"].some(keyword => location.includes(keyword))) {
                // console.log(`当前IP地址检测为中国大陆 (基于JSONP: ${location}), 根据策略将限制访问。`); // 中文注释
                resolve(false); // 中国大陆IP
            } else {
                // console.log(`当前IP地址检测为非中国大陆或港澳台 (基于JSONP: ${location}), 允许访问。`); // 中文注释
                resolve(true); // 非中国大陆IP或港澳台
            }
        };

        // 创建并添加script标签来触发JSONP请求
        const script = document.createElement('script');
        script.id = 'jsonpGeoScript'; // 给script标签一个ID，方便之后移除
        script.src = 'https://ping0.cc/geo/jsonp/jsonpGeoCallback'; // 注意回调函数名已包含在URL中
        
        // 处理脚本加载失败的情况 (例如网络错误，或ping0.cc服务不可用)
        script.onerror = function() {
            console.error("加载JSONP地理位置脚本失败。默认为允许访问。"); // 中文注释
            delete window.jsonpGeoCallback; // 清理
            const scriptTag = document.getElementById('jsonpGeoScript');
            if (scriptTag) {
                scriptTag.remove();
            }
            resolve(true); // 加载失败时，默认为允许访问
        };
        
        document.body.appendChild(script);

        // 设置一个超时，以防JSONP请求一直没有响应
        setTimeout(() => {
            if (window.jsonpGeoCallback) { // 如果回调还没有被调用
                console.warn("JSONP地理位置请求超时。默认为允许访问。"); // 中文注释
                delete window.jsonpGeoCallback;
                const scriptTag = document.getElementById('jsonpGeoScript');
                if (scriptTag) {
                    scriptTag.remove();
                }
                resolve(true); // 超时，默认为允许访问
            }
        }, 5000); // 5秒超时
    });

    // 在Promise解决后，重置geoCheckPromise，以便下次可以重新开始检查
    // 这样做是为了处理页面刷新等情况，或者如果希望每次页面导航都重新检查
    geoCheckPromise.finally(() => {
        geoCheckPromise = null;
    });
    
    return geoCheckPromise;
}

/**
 * 检查用户区域并根据结果重定向。
 * 如果区域不受支持，则重定向到 /banip 页面。
 */
async function checkRegionAndRedirect() {
    // 检查 BAN_IP 设置是否为 false，如果是，则不执行IP检测
    // 确保 window.APP_CONFIG 和 banIpEnabled 确实存在且被正确设置为布尔值
    if (window.APP_CONFIG && typeof window.APP_CONFIG.banIpEnabled === 'boolean' && !window.APP_CONFIG.banIpEnabled) {
        // console.log("IP区域检测已由 BAN_IP=False 配置禁用。"); // 中文注释
        return; // 如果设置为False，则跳过IP检测
    }

    // 仅当当前页面不是 /banip 时才执行检查和重定向，防止无限循环
    // 同时，管理员页面不进行区域检查
    if (window.location.pathname === '/banip' || window.location.pathname.startsWith('/admin_')) {
        return;
    }

    // 在执行检查前，可以先给用户一个提示，例如显示一个加载遮罩
    // document.body.classList.add('checking-region'); // 假设有一个CSS类来显示加载状态

    const isAllowed = await isAvailableRegionJS();

    // document.body.classList.remove('checking-region'); // 移除加载状态

    if (!isAllowed) {
        // 构造完整的 banip 页面的 URL
        const banipUrl = window.location.origin + '/banip';
        window.location.href = banipUrl; 
    }
}
// --- IP区域检查功能结束 ---