// static/js/streamApiHandler.js

/**
 * 处理API流式（NDJSON）请求。
 * @param {object} options 配置对象。
 * @param {string} options.endpoint API的URL。
 * @param {object} options.payload 发送到API的JSON负载。
 * @param {HTMLElement} options.statusElement 用于显示状态消息的元素。
 * @param {HTMLElement} options.logElement 用于显示日志消息的元素。
 * @param {object} options.callbacks 回调函数对象。
 * @param {function(string)} options.callbacks.onProgress 当接收到中间流消息时调用 (isFinish: null)。
 * @param {function(object)} options.callbacks.onSuccess 当API成功完成时调用 (isFinish: true)，参数为解析后的结果。
 * @param {function(string)} options.callbacks.onFailure 当API操作失败时调用 (isFinish: false)。
 * @param {function(Error)} options.callbacks.onRequestError 当发生网络或请求错误时调用。
 * @param {function} [options.callbacks.onStreamStart] 当流开始处理时调用。
 * @param {function} [options.callbacks.onStreamEnd] 当流处理完毕（无论成功失败）时调用。
 */
async function handleApiStreamRequest(options) {
    const { endpoint, payload, statusElement, logElement, callbacks } = options;

    if (callbacks.onStreamStart) {
        callbacks.onStreamStart();
    }

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            let errorMessage = `服务器错误: ${response.status} ${response.statusText}`;
            try { // 尝试解析JSON错误体
                const errorData = await response.json();
                errorMessage = `错误: ${errorData.message || response.statusText}`;
            } catch (e) {
                // 如果响应体不是JSON，保持原始错误信息
            }
            updateStatusMessage(statusElement, errorMessage, 'danger');
            addLogMessage(logElement, `请求失败: ${errorMessage}`);
            if (callbacks.onRequestError) callbacks.onRequestError(new Error(errorMessage));
            if (callbacks.onStreamEnd) callbacks.onStreamEnd();
            return;
        }
        
        updateStatusMessage(statusElement, "处理中，请稍候...", 'info');

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let streamEndedSuccessfully = false; // 用于标记isFinish:true是否已收到

        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                // 处理缓冲区中剩余的最后一行（如果有）
                if (buffer.trim()) {
                    processJsonLine(buffer.trim());
                }
                break;
            }
            
            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split('\n');
            
            // 如果缓冲区末尾不是换行符，则最后一部分可能是不完整的行，保留它
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.trim()) {
                   processJsonLine(line.trim());
                }
            }
             // 如果已经收到了isFinish:true或isFinish:false，可以提前停止处理（尽管通常流也会很快结束）
            if (streamEndedSuccessfully) break; 
        }

        if (!streamEndedSuccessfully && logElement.textContent.includes("处理中") && !logElement.textContent.includes("最终错误") && !logElement.textContent.includes("执行完毕") && !logElement.textContent.includes("导入成功")) {
             // 如果流正常结束，但没有收到 isFinish: true/false 的明确消息，可能是一个意外情况
             // (通常服务器应该总是发送一个最终状态)
             updateStatusMessage(statusElement, "流处理完成，但未收到明确的成功/失败标志。", 'warning');
        }

    } catch (error) {
        console.error('Fetch请求或流处理错误:', error);
        const netErrorMsg = `请求发送或处理失败: ${error.message}`;
        updateStatusMessage(statusElement, netErrorMsg, 'danger');
        addLogMessage(logElement, netErrorMsg);
        if (callbacks.onRequestError) callbacks.onRequestError(error);
    } finally {
        if (callbacks.onStreamEnd) {
            callbacks.onStreamEnd();
        }
    }

    function processJsonLine(line) {
        try {
            const jsonData = JSON.parse(line);
            if (jsonData.isFinish === null) {
                updateStatusMessage(statusElement, jsonData.message, 'info');
                addLogMessage(logElement, jsonData.message);
                if (callbacks.onProgress) callbacks.onProgress(jsonData.message);
            } else if (jsonData.isFinish === true) {
                streamEndedSuccessfully = true; // 标记成功
                // jsonData.message 此时可能是包含分享码的JSON字符串，需要再次解析
                try {
                    const resultPayload = JSON.parse(jsonData.message);
                    updateStatusMessage(statusElement, '执行完毕！', 'success');
                     // 显式添加一个日志表示操作完成
                    addLogMessage(logElement, '操作执行完毕。');

                    if (callbacks.onSuccess) callbacks.onSuccess(resultPayload);
                } catch (parseError) {
                    // 如果jsonData.message不是预期的JSON字符串 (例如导入操作的成功消息是普通字符串)
                    updateStatusMessage(statusElement, `操作成功: ${jsonData.message}`, 'success');
                    addLogMessage(logElement, `操作成功: ${jsonData.message}`);
                    if (callbacks.onSuccess) callbacks.onSuccess({ rawMessage: jsonData.message }); //传递原始消息
                }
            } else if (jsonData.isFinish === false) {
                streamEndedSuccessfully = true; // 也算流结束的一种方式
                updateStatusMessage(statusElement, `操作失败: ${jsonData.message}`, 'danger');
                addLogMessage(logElement, `最终错误: ${jsonData.message}`);
                if (callbacks.onFailure) callbacks.onFailure(jsonData.message);
            }
        } catch (e) {
            console.error('解析JSON行时出错:', line, e);
            addLogMessage(logElement, `错误: 无法解析流数据: ${line}`);
        }
    }
}