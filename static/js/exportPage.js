// static/js/exportPage.js

document.addEventListener('DOMContentLoaded', async function () {
    // 客户端侧检查IP是否为中国大陆地区
    await checkRegionAndRedirect(); 

    const exportForm = document.getElementById('exportForm');
    const resultArea = document.getElementById('resultArea');
    const statusMessageEl = document.getElementById('statusMessage');
    const logOutputEl = document.getElementById('logOutput');
    
    const longShareCodeAreaEl = document.getElementById('longShareCodeArea');
    const shareCodeOutputEl = document.getElementById('shareCodeOutput'); 
    const shortShareCodeAreaEl = document.getElementById('shortShareCodeArea');
    const shortShareCodeOutputEl = document.getElementById('shortShareCodeOutput');
    
    const actionButtonsAreaEl = document.getElementById('actionButtonsArea');
    const downloadShareCodeBtn = document.getElementById('downloadShareCodeBtn');
    const copyShareCodeBtn = document.getElementById('copyShareCodeBtn'); 
    const copyShortShareCodeBtn = document.getElementById('copyShortShareCodeBtn');

    const userSpecifiedBaseNameInput = document.getElementById('userSpecifiedBaseName');
    const generateShortCodeCheckbox = document.getElementById('generateShortCode');
    const shareProjectCheckbox = document.getElementById('shareProject');

    const startExportBtn = document.getElementById('startExportBtn'); // 获取开始导出按钮

    // 从全局配置或 data-* 属性获取 API URL
    const API_EXPORT_URL = window.APP_CONFIG.apiExportUrl || '/api/export'; 

    let currentLongShareData = null;
    let currentFilename = "exported_data.123share";
    
    // 存储按钮的原始 HTML 内容，用于恢复
    const originalStartExportBtnHtml = startExportBtn.innerHTML;
    let originalCopyShortBtnHtml = ''; 
    let originalCopyLongBtnHtml = '';
    let originalDownloadBtnHtml = '';

    // UI元素集合，方便传递给通用函数
    const uiElements = {
        statusMessageElement: statusMessageEl,
        logOutputElement: logOutputEl,
        longShareCodeAreaElement: longShareCodeAreaEl,
        shareCodeOutputElement: shareCodeOutputEl,
        shortShareCodeAreaElement: shortShareCodeAreaEl,
        shortShareCodeOutputElement: shortShareCodeOutputEl,
        actionButtonsAreaElement: actionButtonsAreaEl,
        copyShareCodeBtnElement: copyShareCodeBtn,
        downloadShareCodeBtnElement: downloadShareCodeBtn,
        copyShortShareCodeBtnElement: copyShortShareCodeBtn
    };

    // 从 Cookie 加载凭据
    const savedUsername = getCookie('username');
    const savedPassword = getCookie('password');
    if (savedUsername) document.getElementById('username').value = savedUsername;
    if (savedPassword) document.getElementById('password').value = savedPassword;
            
    shareProjectCheckbox.addEventListener('change', function() {
        if (this.checked) {
            generateShortCodeCheckbox.checked = true;
            generateShortCodeCheckbox.disabled = true;
            userSpecifiedBaseNameInput.required = true;
        } else {
            generateShortCodeCheckbox.disabled = false;
            userSpecifiedBaseNameInput.required = false; 
        }
    });
            
    exportForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        resultArea.style.display = 'block';
        resetResultDisplay(uiElements);
        currentLongShareData = null;

        // 更新开始导出按钮状态：立即禁用并改变文字/图标
        startExportBtn.disabled = true;
        startExportBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>处理中...';

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const userSpecifiedBaseNameValue = userSpecifiedBaseNameInput.value.trim();
        const homeFilePath = document.getElementById('homeFilePath').value;
        const generateShortCode = generateShortCodeCheckbox.checked; 
        const shareProject = shareProjectCheckbox.checked;

        if (shareProject && !userSpecifiedBaseNameValue) {
            updateStatusMessage(statusMessageEl, '错误: 加入资源共享计划时，必须填写根目录名 (分享名)。', 'danger'); 
            userSpecifiedBaseNameInput.focus();
            // 恢复按钮状态因为校验失败提前返回
            startExportBtn.innerHTML = originalStartExportBtnHtml; 
            startExportBtn.disabled = false;
            return;
        }

        setCookie('username', username, 30); 
        setCookie('password', password, 30); 

        const payload = {
            username: username,
            password: password,
            userSpecifiedBaseName: userSpecifiedBaseNameValue,
            homeFilePath: homeFilePath,
            generateShortCode: generateShortCode,
            shareProject: shareProject
        };
                
        const timestamp = Math.floor(Date.now() / 1000);
        if (userSpecifiedBaseNameValue) {
            currentFilename = `${userSpecifiedBaseNameValue}.123share`;
        } else {
            currentFilename = `export_${timestamp}.123share`;
        }
        currentFilename = currentFilename.replace(/[\\/:*?"<>|]+/g, '_').replace(/\s+/g, '_');

        handleApiStreamRequest({
            endpoint: API_EXPORT_URL,
            payload: payload,
            statusElement: statusMessageEl,
            logElement: logOutputEl,
            callbacks: {
                onSuccess: function(data) { 
                    currentLongShareData = displayShareCodesAndActions(data, uiElements, generateShortCode);
                    if (copyShortShareCodeBtn.style.display !== 'none') {
                        originalCopyShortBtnHtml = copyShortShareCodeBtn.innerHTML;
                    }
                    if (copyShareCodeBtn.style.display !== 'none') {
                        originalCopyLongBtnHtml = copyShareCodeBtn.innerHTML;
                    }
                    if (downloadShareCodeBtn.style.display !== 'none') {
                        originalDownloadBtnHtml = downloadShareCodeBtn.innerHTML;
                    }
                },
                onFailure: function(message) {
                    // 状态已由 streamApiHandler 更新
                },
                onRequestError: function(error) {
                     // 状态已由 streamApiHandler 更新
                },
                onStreamEnd: function() { // 流结束后，无论成功失败都确保按钮恢复
                    startExportBtn.innerHTML = originalStartExportBtnHtml;
                    startExportBtn.disabled = false;
                }
            }
        });
    });

    downloadShareCodeBtn.addEventListener('click', function() {
        downloadFile(currentLongShareData, currentFilename, downloadShareCodeBtn, originalDownloadBtnHtml);
    });

    copyShareCodeBtn.addEventListener('click', function() {
        copyToClipboard(shareCodeOutputEl, copyShareCodeBtn, `<i class="bi bi-clipboard-check"></i>复制成功`, originalCopyLongBtnHtml);
    });
            
    copyShortShareCodeBtn.addEventListener('click', function() {
        copyToClipboard(shortShareCodeOutputEl, copyShortShareCodeBtn, `<i class="bi bi-clipboard-check"></i>复制成功`, originalCopyShortBtnHtml);
    });
});