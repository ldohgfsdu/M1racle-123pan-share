// static/js/transformPage.js

document.addEventListener('DOMContentLoaded', async function () {
    // 客户端侧检查IP是否为中国大陆地区
    await checkRegionAndRedirect();

    // Tab 1: 123share 转 123FastLink
    const toFastLinkForm = document.getElementById('toFastLinkForm');
    const toFL_shareFileInput = document.getElementById('toFL_shareFileInput');
    const toFL_selectShareFileButton = document.getElementById('toFL_selectShareFileButton');
    const toFL_rootFolderNameInput = document.getElementById('toFL_rootFolderName');
    const toFL_shareCodeTextarea = document.getElementById('toFL_shareCode');
    const toFastLinkResultArea = document.getElementById('toFastLinkResultArea');
    const toFastLinkStatusMessage = document.getElementById('toFastLinkStatusMessage');
    const toFastLinkJsonOutputTextarea = document.getElementById('toFastLinkJsonOutput');
    const toFastLinkActionButtons = document.getElementById('toFastLinkActionButtons');
    const toFL_copyJsonBtn = document.getElementById('toFL_copyJsonBtn');
    const toFL_downloadJsonBtn = document.getElementById('toFL_downloadJsonBtn');
    const startToFastLinkTransformBtn = document.getElementById('startToFastLinkTransformBtn');
    
    // 存储按钮的原始 HTML 内容，用于恢复
    const originalStartToFLBtnHtml = startToFastLinkTransformBtn.innerHTML;
    const originalToFLCopyBtnHtml = toFL_copyJsonBtn.innerHTML; 
    const originalToFLDownloadBtnHtml = toFL_downloadJsonBtn.innerHTML; 

    // Tab 2: 123FastLink 转 123share
    const fromFastLinkForm = document.getElementById('fromFastLinkForm');
    const fromFL_jsonFileInput = document.getElementById('fromFL_jsonFileInput');
    const fromFL_selectJsonFileButton = document.getElementById('fromFL_selectJsonFileButton');
    const fromFL_rootFolderNameInput = document.getElementById('fromFL_rootFolderName');
    const fromFL_jsonDataTextarea = document.getElementById('fromFL_jsonData');
    const fromFL_generateShortCodeCheckbox = document.getElementById('fromFL_generateShortCode');
    const fromFL_shareProjectCheckbox = document.getElementById('fromFL_shareProject');
    const fromFastLinkResultArea = document.getElementById('fromFastLinkResultArea');
    const fromFastLinkStatusMessage = document.getElementById('fromFastLinkStatusMessage');
    const fromFastLinkOutputContainer = document.getElementById('fromFastLinkOutputContainer');
    const startFromFastLinkTransformBtn = document.getElementById('startFromFastLinkTransformBtn');

    const originalStartFromFLBtnHtml = startFromFastLinkTransformBtn.innerHTML;

    const API_TO_FASTLINK_URL = window.APP_CONFIG.apiToFastLinkUrl;
    const API_FROM_FASTLINK_URL = window.APP_CONFIG.apiFromFastLinkUrl;

    // === Tab 1: 123share 转 123FastLink ===
    if (toFL_selectShareFileButton && toFL_shareFileInput) {
        toFL_selectShareFileButton.addEventListener('click', function () {
            toFL_shareFileInput.click();
        });

        toFL_shareFileInput.addEventListener('change', function (event) {
            const file = event.target.files[0];
            if (file) {
                if (!file.name.toLowerCase().endsWith('.123share')) {
                    updateStatusMessage(toFastLinkStatusMessage, '错误: 请选择一个有效的 .123share 文件。', 'danger');
                    toFastLinkStatusMessage.style.display = 'block'; 
                    toFL_shareFileInput.value = '';
                    return;
                }
                let rootFolderName = file.name.substring(0, file.name.length - 9);
                toFL_rootFolderNameInput.value = rootFolderName;

                const reader = new FileReader();
                reader.onload = function (e) {
                    toFL_shareCodeTextarea.value = e.target.result;
                    updateStatusMessage(toFastLinkStatusMessage, `已成功加载文件: ${escapeHtml(file.name)}`, 'success');
                    toFastLinkStatusMessage.style.display = 'block'; 
                };
                reader.onerror = function (e) {
                    console.error("读取.123share文件时出错:", e);
                    updateStatusMessage(toFastLinkStatusMessage, `错误: 读取文件 ${escapeHtml(file.name)} 失败。`, 'danger');
                    toFastLinkStatusMessage.style.display = 'block'; 
                };
                reader.readAsText(file, 'UTF-8');
                toFL_shareFileInput.value = ''; 
            }
        });
    }

    toFastLinkForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        toFastLinkResultArea.style.display = 'block';
        toFastLinkActionButtons.style.display = 'none';
        toFastLinkJsonOutputTextarea.value = '';
        updateStatusMessage(toFastLinkStatusMessage, '转换中，请稍候...', 'info');
        toFastLinkStatusMessage.style.display = 'block'; 

        // 更新开始转换按钮状态
        startToFastLinkTransformBtn.disabled = true;
        startToFastLinkTransformBtn.innerHTML = `<i class="bi bi-hourglass-split"></i>处理中...`;

        const payload = {
            shareCode: toFL_shareCodeTextarea.value,
            rootFolderName: toFL_rootFolderNameInput.value.trim()
        };

        try {
            const response = await fetch(API_TO_FASTLINK_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (result.isFinish) {
                toFastLinkJsonOutputTextarea.value = JSON.stringify(result.message, null, 4);
                updateStatusMessage(toFastLinkStatusMessage, '转换成功！', 'success');
                toFastLinkActionButtons.style.display = 'flex';
            } else {
                toFastLinkJsonOutputTextarea.value = `错误: ${result.message}`;
                updateStatusMessage(toFastLinkStatusMessage, '转换失败。', 'danger');
            }
        } catch (error) {
            console.error('转换到123FastLink API请求错误:', error);
            toFastLinkJsonOutputTextarea.value = `请求错误: ${error.message}`;
            updateStatusMessage(toFastLinkStatusMessage, '转换请求失败。', 'danger');
        } finally {
            // 恢复按钮状态
            startToFastLinkTransformBtn.innerHTML = originalStartToFLBtnHtml;
            startToFastLinkTransformBtn.disabled = false;
        }
    });

    toFL_copyJsonBtn.addEventListener('click', function() { 
        copyToClipboard(toFastLinkJsonOutputTextarea, toFL_copyJsonBtn, `<i class="bi bi-clipboard-check"></i>复制成功`, originalToFLCopyBtnHtml);
    });

    toFL_downloadJsonBtn.addEventListener('click', function() {
        const filenameBase = toFL_rootFolderNameInput.value.trim() || "transformed_data";
        const filename = `${filenameBase}.json`.replace(/[\\/:*?"<>|]+/g, '_').replace(/\s+/g, '_');
        downloadFile(toFastLinkJsonOutputTextarea.value, filename, toFL_downloadJsonBtn, originalToFLDownloadBtnHtml, 'application/json');
    });

    // === Tab 2: 123FastLink 转 123share ===
    if (fromFL_selectJsonFileButton && fromFL_jsonFileInput) {
        fromFL_selectJsonFileButton.addEventListener('click', function () {
            fromFL_jsonFileInput.click();
        });

        fromFL_jsonFileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                if (!file.name.toLowerCase().endsWith('.json')) {
                    updateStatusMessage(fromFastLinkStatusMessage, '错误: 请选择一个有效的 .json 文件。', 'danger');
                    fromFastLinkStatusMessage.style.display = 'block'; 
                    fromFL_jsonFileInput.value = '';
                    return;
                }
                const reader = new FileReader();
                reader.onload = function(e) {
                    const fileContent = e.target.result;
                    fromFL_jsonDataTextarea.value = fileContent;
                    try {
                        const jsonData = JSON.parse(fileContent);
                        if (jsonData.commonPath && typeof jsonData.commonPath === 'string') {
                            fromFL_rootFolderNameInput.value = jsonData.commonPath.replace(/^\/+|\/+$/g, '');
                        } else {
                            fromFL_rootFolderNameInput.value = '';
                        }
                        updateStatusMessage(fromFastLinkStatusMessage, `已成功加载并解析文件: ${escapeHtml(file.name)}。commonPath已自动填充。`, 'success');
                        fromFastLinkStatusMessage.style.display = 'block'; 
                    } catch (parseError) {
                        console.error("解析.json文件内容时出错:", parseError);
                        updateStatusMessage(fromFastLinkStatusMessage, `错误: 文件 ${escapeHtml(file.name)} 不是有效的JSON格式。`, 'danger');
                        fromFastLinkStatusMessage.style.display = 'block'; 
                        fromFL_rootFolderNameInput.value = '';
                    }
                };
                reader.onerror = function(e) {
                    console.error("读取.json文件时出错:", e);
                    updateStatusMessage(fromFastLinkStatusMessage, `错误: 读取文件 ${escapeHtml(file.name)} 失败。`, 'danger');
                    fromFastLinkStatusMessage.style.display = 'block'; 
                };
                reader.readAsText(file, 'UTF-8');
                fromFL_jsonFileInput.value = '';
            }
        });
    }
    
    fromFL_shareProjectCheckbox.addEventListener('change', function() {
        if (this.checked) {
            fromFL_generateShortCodeCheckbox.checked = true;
            fromFL_generateShortCodeCheckbox.disabled = true;
        } else {
            fromFL_generateShortCodeCheckbox.disabled = false;
        }
    });

    fromFastLinkForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        fromFastLinkResultArea.style.display = 'block';
        fromFastLinkOutputContainer.innerHTML = '';
        updateStatusMessage(fromFastLinkStatusMessage, '转换中，请稍候...', 'info');
        fromFastLinkStatusMessage.style.display = 'block';

        // 更新开始转换按钮状态
        startFromFastLinkTransformBtn.disabled = true;
        startFromFastLinkTransformBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>处理中...';

        const rootFolderNameByUser = fromFL_rootFolderNameInput.value.trim();
        let fastLinkJsonString = fromFL_jsonDataTextarea.value;

        try {
            let fastLinkJsonData = JSON.parse(fastLinkJsonString);
            if (rootFolderNameByUser) {
                fastLinkJsonData.commonPath = rootFolderNameByUser + (fastLinkJsonData.commonPath && fastLinkJsonData.commonPath.endsWith('/') ? "" : "/");
            } else {
                 if (fastLinkJsonData.commonPath && typeof fastLinkJsonData.commonPath === 'string' && fastLinkJsonData.commonPath.trim() === '') {
                    fastLinkJsonData.commonPath = "";
                 } else if (!fastLinkJsonData.commonPath) {
                    fastLinkJsonData.commonPath = "";
                 }
            }
            fastLinkJsonString = JSON.stringify(fastLinkJsonData);
        } catch (e) {
            updateStatusMessage(fromFastLinkStatusMessage, '输入的Json数据格式无效。', 'danger');
            // 恢复按钮状态因为校验失败提前返回
            startFromFastLinkTransformBtn.innerHTML = originalStartFromFLBtnHtml; 
            startFromFastLinkTransformBtn.disabled = false;
            return;
        }
        
        const payload = {
            '123FastLinkJson': fastLinkJsonString,
            'generateShortCode': fromFL_generateShortCodeCheckbox.checked,
            'shareProject': fromFL_shareProjectCheckbox.checked 
        };

        try {
            const response = await fetch(API_FROM_FASTLINK_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            
            if (result.isFinish) {
                updateStatusMessage(fromFastLinkStatusMessage, '转换成功！', 'success');
                if (result.message && Array.isArray(result.message) && result.message.length > 0) {
                    result.message.forEach((item, index) => {
                        const resultItemDiv = document.createElement('div');
                        resultItemDiv.classList.add('result-item');
                        
                        const title = document.createElement('h6');
                        title.textContent = `分享 (结果 ${index + 1}): ${escapeHtml(item.rootFolderName)}`;
                        resultItemDiv.appendChild(title);

                        const buttonRow = document.createElement('div');
                        buttonRow.classList.add('action-button-row'); 

                        const copyLongBtn = document.createElement('button');
                        copyLongBtn.type = 'button';
                        copyLongBtn.classList.add('btn', 'custom-btn', 'btn-secondary'); 
                        const originalCopyLongText = `<i class="bi bi-clipboard me-2"></i>复制长码`;
                        copyLongBtn.innerHTML = originalCopyLongText;
                        const longCodeForCopy = item.longShareCode;
                        copyLongBtn.addEventListener('click', function() {
                            const tempTextarea = document.createElement('textarea');
                            tempTextarea.value = longCodeForCopy;
                            document.body.appendChild(tempTextarea);
                            copyToClipboard(tempTextarea, this, `<i class="bi bi-clipboard-check me-2"></i>复制成功`, originalCopyLongText);
                            document.body.removeChild(tempTextarea);
                        });
                        buttonRow.appendChild(copyLongBtn);

                        if (item.shortShareCode) {
                            const copyShortBtn = document.createElement('button');
                            copyShortBtn.type = 'button';
                            copyShortBtn.classList.add('btn', 'custom-btn', 'btn-info'); 
                            const originalCopyShortText = `<i class="bi bi-clipboard me-2"></i>复制短码`;
                            copyShortBtn.innerHTML = originalCopyShortText;
                            const shortCodeForCopy = item.shortShareCode;
                            copyShortBtn.addEventListener('click', function() {
                                const tempTextarea = document.createElement('textarea');
                                tempTextarea.value = shortCodeForCopy;
                                document.body.appendChild(tempTextarea);
                                copyToClipboard(tempTextarea, this, `<i class="bi bi-clipboard-check me-2"></i>复制成功`, originalCopyShortText);
                                document.body.removeChild(tempTextarea);
                            });
                            buttonRow.appendChild(copyShortBtn);
                        }
                        
                        const downloadBtn = document.createElement('button');
                        downloadBtn.type = 'button';
                        downloadBtn.classList.add('btn', 'custom-btn', 'btn-primary'); 
                        const originalDownloadText = `<i class="bi bi-file-earmark-arrow-down me-2"></i>下载文件`;
                        downloadBtn.innerHTML = originalDownloadText;
                        const shareCodeForDownload = item.longShareCode;
                        const filenameForDownload = `${item.rootFolderName}.123share`.replace(/[\\/:*?"<>|]+/g, '_').replace(/\s+/g, '_');
                        downloadBtn.addEventListener('click', function() {
                            downloadFile(shareCodeForDownload, filenameForDownload, this, originalDownloadText);
                        });
                        buttonRow.appendChild(downloadBtn);

                        resultItemDiv.appendChild(buttonRow);
                        fromFastLinkOutputContainer.appendChild(resultItemDiv);
                    });
                } else if (result.note) {
                     fromFastLinkOutputContainer.innerHTML = `<p class="text-muted text-center p-3">${escapeHtml(result.note)}</p>`;
                } else {
                    fromFastLinkOutputContainer.innerHTML = `<p class="text-muted text-center p-3">转换成功，但未返回有效数据。</p>`;
                }
            } else {
                updateStatusMessage(fromFastLinkStatusMessage, '转换失败。', 'danger');
                fromFastLinkOutputContainer.innerHTML = `<div class="alert alert-danger">${escapeHtml(result.message)}</div>`;
            }
        } catch (error) {
            console.error('从123FastLink转换API请求错误:', error);
            updateStatusMessage(fromFastLinkStatusMessage, '转换请求失败。', 'danger');
             fromFastLinkOutputContainer.innerHTML = `<div class="alert alert-danger">请求错误: ${escapeHtml(error.message)}</div>`;
        } finally {
            // 恢复按钮状态
            startFromFastLinkTransformBtn.innerHTML = originalStartFromFLBtnHtml;
            startFromFastLinkTransformBtn.disabled = false;
        }
    });

    document.querySelectorAll('#transformTabs button[data-bs-toggle="tab"]').forEach(tabEl => {
        tabEl.addEventListener('hide.bs.tab', function (event) {
            toFastLinkStatusMessage.style.display = 'none';
            toFastLinkResultArea.style.display = 'none';
            toFastLinkJsonOutputTextarea.value = '';
            if(toFL_shareFileInput) toFL_shareFileInput.value = ''; 

            fromFastLinkStatusMessage.style.display = 'none';
            fromFastLinkResultArea.style.display = 'none';
            fromFastLinkOutputContainer.innerHTML = '';
            if(fromFL_jsonFileInput) fromFL_jsonFileInput.value = ''; 
        });
    });
});