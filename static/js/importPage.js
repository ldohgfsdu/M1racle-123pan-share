document.addEventListener('DOMContentLoaded', async function () {
    // 客户端侧检查IP是否为中国大陆地区, 如果是则重定向
    await checkRegionAndRedirect();

    // 获取表单和结果显示区域的DOM元素
    const importForm = document.getElementById('importForm');
    const resultArea = document.getElementById('resultArea');
    const statusMessageEl = document.getElementById('statusMessage');
    const logOutputEl = document.getElementById('logOutput');

    // 公共资源库相关的DOM元素
    const selectedPublicCodeHashInput = document.getElementById('selectedPublicCodeHash');
    const selectedPublicRootNameInput = document.getElementById('selectedPublicRootName');
    const publicSharesListDiv = document.getElementById('publicSharesListActual');
    const publicShareSearchInput = document.getElementById('publicShareSearch');
    const publicSharesListContainer = document.getElementById('publicSharesListContainer');

    // 短分享码、长分享码、文件导入相关的DOM元素
    const shortCodeInput = document.getElementById('shortCodeInput');
    const longBase64DataInput = document.getElementById('longBase64DataInput');
    const longRootFolderNameInput = document.getElementById('longRootFolderNameInput');
    const importShareProjectCheckbox = document.getElementById('importShareProject');

    const shareFileInput = document.getElementById('shareFileInput');
    const selectShareFileButton = document.getElementById('selectShareFileButton');

    // 内容目录树模态框相关的DOM元素
    const contentTreeModalEl = document.getElementById('contentTreeModal');
    const contentTreeSearchInput = document.getElementById('contentTreeSearchInput');
    const contentTreeDisplayArea = document.getElementById('contentTreeDisplayArea');
    const bsContentTreeModal = new bootstrap.Modal(contentTreeModalEl);

    // 目录树模态框内的按钮
    const selectFilesToggleBtn = document.getElementById('selectFilesToggleBtn');
    const filterButtonsContainer = document.getElementById('filterButtonsContainer');
    const selectAllImagesBtn = document.getElementById('selectAllImagesBtn');
    const selectAllVideosBtn = document.getElementById('selectAllVideosBtn');
    const selectAllAudiosBtn = document.getElementById('selectAllAudiosBtn');
    const selectAllArchivesBtn = document.getElementById('selectAllArchivesBtn');
    const confirmSelectionBtn = document.getElementById('confirmSelectionBtn');

    const startImportBtn = document.getElementById('startImportBtn');

    // API端点URL 
    const API_IMPORT_URL = window.APP_CONFIG.apiImportUrl || '/api/import';
    const API_LIST_PUBLIC_SHARES_URL = window.APP_CONFIG.apiListPublicSharesUrl || '/api/list_public_shares';
    const API_GET_CONTENT_TREE_URL = window.APP_CONFIG.apiGetContentTreeUrl || '/api/get_content_tree';
    const API_SEARCH_DATABASE_URL = window.APP_CONFIG.apiSearchDatabaseUrl || '/api/search_database';

    // 状态变量
    let allPublicSharesData = [];
    let currentPublicListPage = 1;
    let isLoadingPublicList = false;
    let isEndOfPublicList = false;
    let currentSearchPage = 1;
    let isLoadingSearchResults = false;
    let isEndOfSearchResults = false;
    let currentSearchTerm = '';
    let currentActiveTabId = 'publicRepoContent';
    const originalStartImportBtnHtml = startImportBtn.innerHTML;

    let currentTreeData = []; // 用于存储从API获取的原始目录树数据 [[lineText, fileId], ...]
    let currentFilterIds = []; // 用户勾选的用于导入的文件ID列表
    let currentSelectedPublicShareItemElement = null; // 当前在公共列表中选中的DOM元素

    // 从Cookie加载用户凭据 
    const savedUsername = getCookie('username');
    const savedPassword = getCookie('password');
    if (savedUsername) document.getElementById('username').value = savedUsername;
    if (savedPassword) document.getElementById('password').value = savedPassword;

    // 辅助函数：设置模态框中选择相关按钮的初始状态
    function setInitialModalState() {
        if (selectFilesToggleBtn) {
            selectFilesToggleBtn.innerHTML = '<i class="bi bi-check-all"></i>选择部分文件导入';
            selectFilesToggleBtn.dataset.selecting = 'false';
        }
        if (filterButtonsContainer) filterButtonsContainer.style.display = 'none';
        if (confirmSelectionBtn) confirmSelectionBtn.style.display = 'none';
    
        // 重新渲染不带勾选框的树 (如果树数据已加载)
        if (currentTreeData && currentTreeData.length > 0) {
             renderTreeLines(currentTreeData, false);
        } else {
            contentTreeDisplayArea.innerHTML = ''; // 清空旧树
        }
    }

    // 切换部分文件选择模式
    if (selectFilesToggleBtn) {
        selectFilesToggleBtn.addEventListener('click', function() {
            const isSelecting = this.dataset.selecting === 'true';
            if (isSelecting) { // 当前是“取消选择”状态，要切换回普通查看
                this.innerHTML = '<i class="bi bi-check-all"></i>选择部分文件导入';
                this.dataset.selecting = 'false';
                filterButtonsContainer.style.display = 'none';
                confirmSelectionBtn.style.display = 'none';
                renderTreeLines(currentTreeData, false); // 重新渲染不带勾选框的树
                currentFilterIds = []; // 从“选择模式”退出时，清空已选ID
            } else { // 当前是普通查看状态，要切换到“选择文件”
                this.innerHTML = '<i class="bi bi-x-lg"></i>取消选择部分文件导入';
                this.dataset.selecting = 'true';
                filterButtonsContainer.style.display = 'flex'; // 使用 flex 以应用 action-button-row 的等宽效果
                confirmSelectionBtn.style.display = 'inline-block';
                renderTreeLines(currentTreeData, true); // 重新渲染带勾选框的树
            }
        });
    }

    // 绑定类型筛选按钮事件
    if (selectAllImagesBtn) selectAllImagesBtn.addEventListener('click', () => toggleSelectionByIcon("🖼️"));
    if (selectAllVideosBtn) selectAllVideosBtn.addEventListener('click', () => toggleSelectionByIcon("🎥"));
    if (selectAllAudiosBtn) selectAllAudiosBtn.addEventListener('click', () => toggleSelectionByIcon("🎵"));
    if (selectAllArchivesBtn) selectAllArchivesBtn.addEventListener('click', () => toggleSelectionByIcon("📦"));

    function toggleSelectionByIcon(iconSymbol) {
        const checkboxes = contentTreeDisplayArea.querySelectorAll('.tree-item-checkbox');
        checkboxes.forEach(checkbox => {
            const lineIndex = parseInt(checkbox.dataset.lineindex, 10);
            const [lineText, fileId] = currentTreeData[lineIndex];
            const isDir = checkbox.dataset.isdir === 'true';
            const lineIcon = lineText.trim().split(" ")[0];

            if (lineText.includes(iconSymbol) && !isDir) { // 只对文件生效
                checkbox.checked = true; // 勾选
                // 触发父级联动
                handleSingleCheckboxChange(checkbox, true); // 传入 true 表示强制向上勾选父级
            }
        });
    }

    // 渲染目录树行的函数
    function renderTreeLines(treeData, showCheckboxes) {
        contentTreeDisplayArea.innerHTML = treeData.map((item, index) => {
            const [lineText, fileId] = item;
            const escapedLineText = escapeHtml(lineText);
            const isDirectory = lineText.includes("📂");
            const icon = lineText.trim().split(" ")[0]; 

            let checkboxHtml = '';
            if (showCheckboxes) {
                checkboxHtml = `<input type="checkbox" class="form-check-input tree-item-checkbox" data-fileid="${fileId}" data-lineindex="${index}" data-isdir="${isDirectory}" data-icon="${escapeHtml(icon)}">`;
            }
            return `<div class="tree-line-item" data-fileid="${fileId}" data-lineindex="${index}" data-isdir="${isDirectory}" data-icon="${escapeHtml(icon)}">${checkboxHtml}<span>${escapedLineText}</span></div>`;
        }).join('');

        if (showCheckboxes) {
            bindCheckboxEvents();
            // 恢复之前的勾选状态 (如果有的话)
            reapplyCheckboxStates();
        }
    }
    
    function reapplyCheckboxStates() {
        if (currentFilterIds.length > 0) {
            const allCheckboxes = contentTreeDisplayArea.querySelectorAll('.tree-item-checkbox');
            allCheckboxes.forEach(cb => {
                const fileId = parseInt(cb.dataset.fileid, 10);
                const isDir = cb.dataset.isdir === 'true';
                if (!isDir && currentFilterIds.includes(fileId)) {
                    cb.checked = true;
                    // 触发父级联动，确保父文件夹也被勾选
                    handleSingleCheckboxChange(cb, true);
                }
            });
            // 由于 handleSingleCheckboxChange 中文件夹的勾选是基于子项，
            // 可能需要再次遍历确保所有包含已选文件的文件夹都被勾选
            propagateFolderChecks();
        }
    }
    
    function propagateFolderChecks() {
        const folderCheckboxes = Array.from(contentTreeDisplayArea.querySelectorAll('.tree-item-checkbox[data-isdir="true"]'));
        // 从最深层文件夹开始检查
        folderCheckboxes.sort((a, b) => getDepthFromLineIndex(b.dataset.lineindex) - getDepthFromLineIndex(a.dataset.lineindex));
        
        folderCheckboxes.forEach(folderCb => {
            if (hasCheckedChildFile(folderCb)) {
                folderCb.checked = true;
            }
        });
    }

    function hasCheckedChildFile(folderCheckbox) {
        const lineIndex = parseInt(folderCheckbox.dataset.lineindex, 10);
        const currentDepth = getDepthFromLineIndex(lineIndex);

        for (let i = lineIndex + 1; i < currentTreeData.length; i++) {
            const childDepth = getDepthFromLineIndex(i);
            if (childDepth > currentDepth) {
                const childCb = contentTreeDisplayArea.querySelector(`.tree-item-checkbox[data-lineindex="${i}"]`);
                if (childCb) {
                    if (childCb.dataset.isdir === 'false' && childCb.checked) return true; // 找到一个已勾选的子文件
                    if (childCb.dataset.isdir === 'true' && hasCheckedChildFile(childCb)) return true; // 递归检查子文件夹
                }
            } else {
                break; 
            }
        }
        return false;
    }

    // 绑定和处理勾选框变化的逻辑
    function bindCheckboxEvents() {
        const checkboxes = contentTreeDisplayArea.querySelectorAll('.tree-item-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.removeEventListener('change', handleCheckboxChangeEvent); 
            checkbox.addEventListener('change', handleCheckboxChangeEvent);
        });
    }

    function handleCheckboxChangeEvent(event) {
        handleSingleCheckboxChange(event.target, false); // 默认不是强制向上勾选
    }
    
    function handleSingleCheckboxChange(checkbox, forceCheckParent = false) {
        const isChecked = checkbox.checked;
        const lineIndex = parseInt(checkbox.dataset.lineindex, 10);
        const isDir = checkbox.dataset.isdir === 'true';

        if (isDir) { // 操作的是文件夹
            // 向下影响子项
            const currentDepth = getDepthFromLineIndex(lineIndex);
            for (let i = lineIndex + 1; i < currentTreeData.length; i++) {
                const childDepth = getDepthFromLineIndex(i);
                if (childDepth > currentDepth) {
                    const childCheckbox = contentTreeDisplayArea.querySelector(`.tree-item-checkbox[data-lineindex="${i}"]`);
                    if (childCheckbox) childCheckbox.checked = isChecked;
                } else {
                    break; 
                }
            }
        }
        
        // 向上影响父项
        if (isChecked || forceCheckParent) { // 如果是勾选文件，或强制勾选父级
            let currentIndex = lineIndex;
            let currentItemDepth = getDepthFromLineIndex(currentIndex);
            while (true) {
                let parentIndex = -1;
                let parentDepth = -1;
                // 从当前项向上查找第一个层级比它浅的文件夹
                for (let p = currentIndex - 1; p >= 0; p--) {
                    const pDepth = getDepthFromLineIndex(p);
                    const pIsDir = currentTreeData[p][0].includes("📂"); 
                    if (pIsDir && pDepth < currentItemDepth) {
                        parentIndex = p;
                        parentDepth = pDepth;
                        break;
                    }
                }

                if (parentIndex !== -1) {
                    const parentCheckbox = contentTreeDisplayArea.querySelector(`.tree-item-checkbox[data-lineindex="${parentIndex}"]`);
                    if (parentCheckbox) {
                         // 只有当子项被勾选时，才强制勾选父项
                         if (isChecked || forceCheckParent) {
                            parentCheckbox.checked = true;
                        }
                    }
                    currentIndex = parentIndex;
                    currentItemDepth = parentDepth;
                } else {
                    break; // 到达顶级或未找到父文件夹
                }
            }
        } else { // 如果是取消勾选文件，则检查是否需要取消父文件夹
           if (!isDir) { // 只对文件取消勾选时触发父级检查
                checkAndUncheckParents(lineIndex);
           }
        }
    }
    
    function checkAndUncheckParents(startIndex) {
        let currentIndex = startIndex;
        let currentItemDepth = getDepthFromLineIndex(currentIndex);

        while (true) {
            let parentIndex = -1;
            let parentDepth = -1;
            for (let p = currentIndex - 1; p >= 0; p--) {
                const pDepth = getDepthFromLineIndex(p);
                const pIsDir = currentTreeData[p][0].includes("📂");
                if (pIsDir && pDepth < currentItemDepth) {
                    parentIndex = p;
                    parentDepth = pDepth;
                    break;
                }
            }

            if (parentIndex !== -1) {
                const parentCheckbox = contentTreeDisplayArea.querySelector(`.tree-item-checkbox[data-lineindex="${parentIndex}"]`);
                if (parentCheckbox && parentCheckbox.checked) { // 只有父文件夹是勾选状态才检查
                    if (!hasCheckedChildFileOrFolder(parentCheckbox)) {
                        parentCheckbox.checked = false;
                    }
                }
                currentIndex = parentIndex;
                currentItemDepth = parentDepth;
            } else {
                break;
            }
        }
    }

    function hasCheckedChildFileOrFolder(folderCheckbox) {
        const lineIndex = parseInt(folderCheckbox.dataset.lineindex, 10);
        const currentDepth = getDepthFromLineIndex(lineIndex);

        for (let i = lineIndex + 1; i < currentTreeData.length; i++) {
            const childDepth = getDepthFromLineIndex(i);
            if (childDepth > currentDepth) {
                const childCb = contentTreeDisplayArea.querySelector(`.tree-item-checkbox[data-lineindex="${i}"]`);
                if (childCb && childCb.checked) return true; // 找到一个已勾选的子项 (文件或文件夹)
            } else {
                break; 
            }
        }
        return false;
    }

    // 辅助函数：从行文本获取层级深度 (基于行在 currentTreeData 中的索引)
    function getDepthFromLineIndex(lineIndex) {
        if (lineIndex < 0 || lineIndex >= currentTreeData.length) return -1;
        const lineText = currentTreeData[lineIndex][0];
        // 匹配所有可能的前缀字符，并计算长度. '    ' (4个空格), '│   ' (4个字符), '└── ' (4个字符), '├── ' (4个字符).
        // 所以深度就是前缀长度除以4.
        const prefix = lineText.match(/^(\s*(?:│\s\s\s|└──\s|├──\s| ))*/)[0];
        return Math.floor(prefix.length / 4);
    }

    // 确认勾选按钮事件
    if (confirmSelectionBtn) {
        confirmSelectionBtn.addEventListener('click', function() {
            currentFilterIds = [];
            const checkboxes = contentTreeDisplayArea.querySelectorAll('.tree-item-checkbox:checked');
            checkboxes.forEach(cb => {
                currentFilterIds.push(parseInt(cb.dataset.fileid, 10));
            });

            currentFilterIds = [...new Set(currentFilterIds)]; // 去重

            if (currentFilterIds.length === 0) {
                alert("您没有勾选任何文件。如果想导入全部内容，请点击“取消选择部分文件导入”按钮，然后关闭此窗口并直接导入。");
                return;
            }
            
            let targetElementName = "当前操作";
            if (currentActiveTabId === 'publicRepoContent' && selectedPublicRootNameInput.value) {
                targetElementName = `资源“${escapeHtml(selectedPublicRootNameInput.value)}”`;
            } else if (currentActiveTabId === 'shortCodeContent' && shortCodeInput.value) {
                targetElementName = `短码“${escapeHtml(shortCodeInput.value.substring(0,8))}...”`;
            } else if (currentActiveTabId === 'longCodeContent' && longRootFolderNameInput.value) {
                 targetElementName = `分享“${escapeHtml(longRootFolderNameInput.value)}”`;
            }
            updateStatusMessage(statusMessageEl, `已为${targetElementName}选择了 ${currentFilterIds.length} 个文件进行导入。`, 'success');

            // 如果是从公共资源库选择的，更新列表项显示
            if (currentSelectedPublicShareItemElement) {
                let filterIdsDisplay = currentSelectedPublicShareItemElement.querySelector('.selected-filter-ids-display');
                if (!filterIdsDisplay) {
                    filterIdsDisplay = document.createElement('small');
                    filterIdsDisplay.classList.add('selected-filter-ids-display');
                    const textContainer = currentSelectedPublicShareItemElement.querySelector('.col');
                    if (textContainer) {
                         textContainer.appendChild(filterIdsDisplay);
                    } else {
                        currentSelectedPublicShareItemElement.appendChild(filterIdsDisplay);
                    }
                }
                const displayIds = currentFilterIds.length > 5 ? currentFilterIds.slice(0, 5).join(', ') + `... (共${currentFilterIds.length}项)` : currentFilterIds.join(', ');
                filterIdsDisplay.textContent = `已选文件ID: ${displayIds}`;
            }
            bsContentTreeModal.hide(); 
        });
    }
    
    // 监听导入模式标签页的切换事件
    document.querySelectorAll('#importTabs button[data-bs-toggle="tab"]').forEach(tabEl => {
        tabEl.addEventListener('shown.bs.tab', function (event) {
            currentActiveTabId = event.target.getAttribute('aria-controls'); 
            selectedPublicCodeHashInput.value = ''; 
            selectedPublicRootNameInput.value = ''; // 清空
            shortCodeInput.value = '';
            longBase64DataInput.value = '';
            longRootFolderNameInput.value = '';
            importShareProjectCheckbox.checked = false;
            if (shareFileInput) shareFileInput.value = ''; 
            
            document.querySelectorAll('.public-share-item.active').forEach(activeItem => {
                activeItem.classList.remove('active');
                const oldFilterDisplay = activeItem.querySelector('.selected-filter-ids-display');
                if(oldFilterDisplay) oldFilterDisplay.remove();
            });
            currentSelectedPublicShareItemElement = null; // 清除
            currentFilterIds = []; // 切换标签页时清空已选ID

            if (statusMessageEl.textContent.startsWith('已选择公共资源:') || 
                statusMessageEl.textContent.startsWith('已成功加载文件:') ||
                statusMessageEl.textContent.includes('选择了')) {
                updateStatusMessage(statusMessageEl, '请输入必填信息。', 'info');
            }
        });
    });

    // 处理公共资源列表项点击事件
    publicSharesListDiv.addEventListener('click', function(event) {
        const item = event.target.closest('.public-share-item');
        if (item && item.contains(event.target) && !event.target.closest('.view-content-tree-btn')) { // 确保不是点击查看目录按钮
            // 清除所有项的 active 和 filterIds 显示
            document.querySelectorAll('.public-share-item.active').forEach(activeItem => {
                activeItem.classList.remove('active');
                const existingFilterDisplay = activeItem.querySelector('.selected-filter-ids-display');
                if (existingFilterDisplay) existingFilterDisplay.textContent = ''; // 只清空内容，保留元素
            });

            item.classList.add('active'); 
            currentSelectedPublicShareItemElement = item; 
            const nameSpan = item.querySelector('.share-name');
            if (nameSpan) {
                 selectedPublicRootNameInput.value = nameSpan.textContent;
            }
            selectedPublicCodeHashInput.value = item.querySelector('.view-content-tree-btn').dataset.codehash;

            updateStatusMessage(statusMessageEl, `已选择公共资源: ${escapeHtml(selectedPublicRootNameInput.value)}`, 'secondary');
            logOutputEl.textContent = ''; 
            currentFilterIds = []; // 重置 filterIds 数组
            const currentFilterDisplay = item.querySelector('.selected-filter-ids-display');
            if (currentFilterDisplay) currentFilterDisplay.textContent = '';
        }
    });

    async function fetchAndDisplayContentTree(params) {
        const payload = {};
        if (params.codeHash) payload.codeHash = params.codeHash;
        if (params.shareCode) payload.shareCode = params.shareCode; 

        if (!payload.codeHash && !payload.shareCode) {
            contentTreeDisplayArea.innerHTML = '<p class="text-center text-danger">错误: 查看目录树缺少必要的参数。</p>';
            setInitialModalState(); 
            bsContentTreeModal.show();
            return;
        }

        contentTreeDisplayArea.innerHTML = '<div class="text-center p-3"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">加载中...</span></div> <span class="ms-2 text-muted">正在加载目录结构...</span></div>';
        contentTreeSearchInput.value = ''; 
        
        setInitialModalState(); 
        
        bsContentTreeModal.show(); 

        try {
            const response = await fetch(API_GET_CONTENT_TREE_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (result.isFinish === true) {
                if (Array.isArray(result.message) && result.message.length > 0) {
                    currentTreeData = result.message; 
                    const showCheckboxesInitially = selectFilesToggleBtn && selectFilesToggleBtn.dataset.selecting === 'true';
                    renderTreeLines(currentTreeData, showCheckboxesInitially); 
                } else if (Array.isArray(result.message) && result.message.length === 0) {
                     contentTreeDisplayArea.innerHTML = '<p class="text-center text-muted p-3">此分享内容为空。</p>';
                     currentTreeData = [];
                } else { 
                    contentTreeDisplayArea.innerHTML = '<p class="text-center text-muted p-3">目录为空或无法解析。</p>';
                    currentTreeData = [];
                }
            } else { 
                contentTreeDisplayArea.innerHTML = `<p class="text-center text-danger p-3">错误: ${escapeHtml(result.message)}</p>`;
                currentTreeData = [];
            }
        } catch (error) {
            console.error('获取目录树失败:', error);
            currentTreeData = [];
            contentTreeDisplayArea.innerHTML = `<p class="text-center text-danger p-3">请求目录树失败: ${escapeHtml(error.message)}</p>`;
        }
    }

    function renderPublicSharesList(sharesToRender, append = false) {
        if (!append) {
            publicSharesListDiv.innerHTML = ''; 
            currentSelectedPublicShareItemElement = null; 
            currentFilterIds = []; 
            selectedPublicRootNameInput.value = '';
            selectedPublicCodeHashInput.value = '';
        }
        
        sharesToRender.forEach(share => {
            const item = document.createElement('div');
            item.classList.add('public-share-item', 'row', 'gx-2', 'align-items-center');
            
            const textContainer = document.createElement('div'); 
            textContainer.classList.add('col');
            textContainer.style.cursor = 'pointer'; 
            textContainer.style.minWidth = '0'; 

            const nameSpan = document.createElement('span'); 
            nameSpan.classList.add('share-name');
            nameSpan.textContent = share.name;
            textContainer.appendChild(nameSpan);

            const tsSpan = document.createElement('span'); 
            tsSpan.classList.add('share-timestamp', 'd-block');
            const date = new Date(share.timestamp);
            tsSpan.textContent = `更新时间: ${date.toLocaleString('zh-CN')}`; 
            textContainer.appendChild(tsSpan);
            
            const filterIdsDisplay = document.createElement('small');
            filterIdsDisplay.classList.add('selected-filter-ids-display');
            textContainer.appendChild(filterIdsDisplay);

            item.appendChild(textContainer); 

            const buttonContainer = document.createElement('div');
            buttonContainer.classList.add('col-auto');

            const viewTreeBtn = document.createElement('button'); 
            viewTreeBtn.type = 'button';
            viewTreeBtn.classList.add('btn', 'btn-sm', 'btn-outline-secondary', 'view-content-tree-btn');
            viewTreeBtn.innerHTML = '<i class="bi bi-search"></i>'; 
            viewTreeBtn.dataset.codehash = share.codeHash; 
            viewTreeBtn.title = "查看目录结构";
            buttonContainer.appendChild(viewTreeBtn);
            item.appendChild(buttonContainer); 
            
            textContainer.addEventListener('click', function() {
                document.querySelectorAll('.public-share-item.active').forEach(activeItem => {
                    activeItem.classList.remove('active');
                    const oldFilterDisplay = activeItem.querySelector('.selected-filter-ids-display');
                    if(oldFilterDisplay) oldFilterDisplay.textContent = '';
                });

                item.classList.add('active'); 
                currentSelectedPublicShareItemElement = item; 
                selectedPublicRootNameInput.value = share.name;
                selectedPublicCodeHashInput.value = share.codeHash;

                updateStatusMessage(statusMessageEl, `已选择公共资源: ${escapeHtml(share.name)}`, 'secondary');
                logOutputEl.textContent = ''; 
                currentFilterIds = [];
                const currentFilterDisplay = item.querySelector('.selected-filter-ids-display');
                if (currentFilterDisplay) currentFilterDisplay.textContent = '';
            });
            publicSharesListDiv.appendChild(item); 
        });
    }

    importForm.addEventListener('submit', async function (event) {
        event.preventDefault(); 
        resultArea.style.display = 'block'; 
        logOutputEl.textContent = '';       
        updateStatusMessage(statusMessageEl, '准备开始...', 'info'); 

        startImportBtn.disabled = true;
        startImportBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>处理中...';

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        setCookie('username', username, 30);
        setCookie('password', password, 30);

        let payload = { username: username, password: password }; 
        let formValid = true; 

        if (currentActiveTabId === 'publicRepoContent') {
            if (!selectedPublicCodeHashInput.value) {
                updateStatusMessage(statusMessageEl, '错误: 请先从公共资源库选择一项资源。', 'danger');
                formValid = false;
            }
            payload.codeHash = selectedPublicCodeHashInput.value;
        } else if (currentActiveTabId === 'shortCodeContent') {
            if (!shortCodeInput.value.trim()) {
                updateStatusMessage(statusMessageEl, '错误: 请输入短分享码。', 'danger');
                shortCodeInput.focus();
                formValid = false;
            }
             payload.codeHash = shortCodeInput.value.trim();
        } else if (currentActiveTabId === 'longCodeContent') {
            if (!longBase64DataInput.value.trim()) {
                updateStatusMessage(statusMessageEl, '错误: 请输入或选择文件以填充长分享码。', 'danger');
                longBase64DataInput.focus();
                formValid = false;
            }
            if (!longRootFolderNameInput.value.trim()) {
                updateStatusMessage(statusMessageEl, '错误: 请输入或选择文件以填充根目录名。', 'danger');
                longRootFolderNameInput.focus();
                formValid = false;
            }
            if (formValid) { 
                payload.base64Data = longBase64DataInput.value.trim();
                payload.rootFolderName = longRootFolderNameInput.value.trim();
                payload.shareProject = importShareProjectCheckbox.checked;

                if (payload.shareProject && !payload.rootFolderName) {
                     updateStatusMessage(statusMessageEl, '错误: 加入资源共享计划时，必须填写有效的根目录名。', 'danger');
                     longRootFolderNameInput.focus();
                     formValid = false;
                }
            }
        } else {
             updateStatusMessage(statusMessageEl, '错误: 未知的导入模式。', 'danger');
             formValid = false;
        }

        if (formValid && currentFilterIds.length > 0) {
            if (payload.codeHash || payload.base64Data) {
                payload.filterIds = currentFilterIds;
            } else {
                console.warn("有 filterIds 但没有主要的导入目标 (codeHash 或 base64Data)，将不传递 filterIds。");
            }
        }

        if (!formValid) {
            startImportBtn.innerHTML = originalStartImportBtnHtml; 
            startImportBtn.disabled = false;
            return; 
        }

        handleApiStreamRequest({
            endpoint: API_IMPORT_URL,
            payload: payload,
            statusElement: statusMessageEl,
            logElement: logOutputEl,
            callbacks: { 
                onSuccess: function(data) {
                    if (currentSelectedPublicShareItemElement) {
                        const filterIdsDisplay = currentSelectedPublicShareItemElement.querySelector('.selected-filter-ids-display');
                        if (filterIdsDisplay) filterIdsDisplay.textContent = '';
                    }
                    currentFilterIds = [];
                },
                onFailure: function(message) {},
                onRequestError: function(error) {},
                onStreamEnd: function() {
                    startImportBtn.innerHTML = originalStartImportBtnHtml;
                    startImportBtn.disabled = false;
                }
            }
        });
    });

    contentTreeModalEl.addEventListener('hidden.bs.modal', function () {
        contentTreeSearchInput.value = ''; 
        setInitialModalState(); 
    });
    
    async function loadSharesPage(page, searchTerm = '') {
        const isSearchMode = searchTerm !== ''; 
        let isLoadingFlag, isEndFlag, currentPageToUpdate, sharesArrayToUpdate, listDiv, apiUrl, fetchOptions;

        if (isSearchMode) {
            if (isLoadingSearchResults && page > 1) return; 
            isLoadingSearchResults = true;
            isLoadingFlag = isLoadingSearchResults;
            isEndFlag = isEndOfSearchResults;
            sharesArrayToUpdate = allPublicSharesData; 
            listDiv = publicSharesListDiv;
            apiUrl = API_SEARCH_DATABASE_URL;
            fetchOptions = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rootFolderName: searchTerm, page: page })
            };
        } else {
            if (isLoadingPublicList && page > 1) return;
            isLoadingPublicList = true;
            isLoadingFlag = isLoadingPublicList;
            isEndFlag = isEndOfPublicList;
            sharesArrayToUpdate = allPublicSharesData;
            listDiv = publicSharesListDiv;
            apiUrl = `${API_LIST_PUBLIC_SHARES_URL}?page=${page}`; 
            fetchOptions = { method: 'GET' };
        }

        if (page === 1) {
            listDiv.innerHTML = '<p class="text-muted text-center">正在加载...</p>';
            allPublicSharesData = []; 
            if (isSearchMode) isEndOfSearchResults = false; else isEndOfPublicList = false; 
        } else {
            const loadingIndicator = listDiv.querySelector('.loading-indicator');
            if (!loadingIndicator) { 
                 listDiv.insertAdjacentHTML('beforeend', '<p class="text-muted text-center loading-indicator">正在加载更多...</p>');
            }
        }

        try {
            const response = await fetch(apiUrl, fetchOptions);
            const existingLoadingIndicator = listDiv.querySelector('.loading-indicator'); 
            if (existingLoadingIndicator) existingLoadingIndicator.remove(); 

            if (!response.ok) {
                if(page === 1) listDiv.innerHTML = `<p class="text-danger text-center">加载失败 (HTTP ${response.status})。</p>`;
                else listDiv.insertAdjacentHTML('beforeend', `<p class="text-danger text-center">加载更多失败。</p>`);
                if (isSearchMode) isEndOfSearchResults = true; else isEndOfPublicList = true;
                return;
            }
            const data = await response.json();

            if (data.success) {
                if (page === 1) listDiv.innerHTML = ''; 
                
                if (data.files && data.files.length > 0) {
                    allPublicSharesData = (page === 1) ? data.files : allPublicSharesData.concat(data.files);
                    renderPublicSharesList(data.files, true); 
                    if (isSearchMode) currentPageSearch = page; else currentPublicListPage = page;
                } else if (page === 1) { 
                    listDiv.innerHTML = `<p class="text-muted text-center">${isSearchMode ? '没有匹配的搜索结果。' : '暂无公共资源。请前往后台管理面板点击“更新数据库”按钮'}</p>`;
                }
                if (isSearchMode) { isEndOfSearchResults = data.end; currentPageToUpdate = currentSearchPage = page; }
                else { isEndOfPublicList = data.end; currentPageToUpdate = currentPublicListPage = page; }
            } else {
                if(page === 1) listDiv.innerHTML = `<p class="text-danger text-center">加载失败: ${escapeHtml(data.message || '未知错误')}</p>`;
                else listDiv.insertAdjacentHTML('beforeend', `<p class="text-danger text-center">加载更多失败。</p>`);
                if (isSearchMode) isEndOfSearchResults = true; else isEndOfPublicList = true;
            }
        } catch (error) {
            console.error(`获取${isSearchMode ? '搜索结果' : '公共资源'}时出错 (页 ${page}):`, error);
            if(page === 1) listDiv.innerHTML = `<p class="text-danger text-center">加载时发生网络错误。</p>`;
            else listDiv.insertAdjacentHTML('beforeend', `<p class="text-danger text-center">加载更多时发生网络错误。</p>`);
            if (isSearchMode) isEndOfSearchResults = true; else isEndOfPublicList = true;
        } finally {
            if (isSearchMode) isLoadingSearchResults = false; else isLoadingPublicList = false;
        }
    }

    publicShareSearchInput.addEventListener('input', function(e) {
        currentSearchTerm = e.target.value.trim().toLowerCase(); 
        currentSearchPage = 1;           
        isEndOfSearchResults = false;    
        allPublicSharesData = [];        
        publicSharesListDiv.innerHTML = ''; 

        if (currentSearchTerm) {
            loadSharesPage(1, currentSearchTerm); 
        } else {
            currentPublicListPage = 1;
            isEndOfPublicList = false;
            loadSharesPage(1);
        }
    });

    if (selectShareFileButton && shareFileInput) {
        selectShareFileButton.addEventListener('click', function() {
            shareFileInput.click(); 
        });

        shareFileInput.addEventListener('change', function(event) {
            const file = event.target.files[0]; 
            if (file) {
                if (!file.name.toLowerCase().endsWith('.123share')) {
                    updateStatusMessage(statusMessageEl, '错误: 请选择一个有效的 .123share 文件。', 'danger');
                    shareFileInput.value = ''; 
                    return;
                }

                let rootFolderName = file.name;
                if (rootFolderName.toLowerCase().endsWith('.123share')) {
                    rootFolderName = rootFolderName.substring(0, rootFolderName.length - 9);
                }
                longRootFolderNameInput.value = rootFolderName; 

                const reader = new FileReader(); 
                reader.onload = function(e) {
                    longBase64DataInput.value = e.target.result; 
                    updateStatusMessage(statusMessageEl, `已成功加载文件: ${escapeHtml(file.name)}`, 'success');
                    
                    const longCodeTabButton = document.getElementById('long-code-tab');
                    if (longCodeTabButton && currentActiveTabId !== 'longCodeContent') {
                        const tabInstance = bootstrap.Tab.getInstance(longCodeTabButton) || new bootstrap.Tab(longCodeTabButton);
                        tabInstance.show();
                    }
                };
                reader.onerror = function(e) {
                    console.error("读取文件时出错:", e);
                    updateStatusMessage(statusMessageEl, `错误: 读取文件 ${escapeHtml(file.name)} 失败。请检查文件或浏览器权限。`, 'danger');
                    longBase64DataInput.value = ''; 
                    longRootFolderNameInput.value = ''; 
                };
                reader.readAsText(file, 'UTF-8'); 
                shareFileInput.value = ''; 
            }
        });
    }

    document.getElementById('importTabsContent').addEventListener('click', function(event) {
        const target = event.target.closest('.view-content-tree-btn'); 
        if (!target) return; 

        let codeHash = null;
        let shareCode = null;

        if (target.id === 'viewTreeForShortCodeBtn') {
            codeHash = shortCodeInput.value.trim();
            if (!codeHash) { 
                alert('请输入短分享码。'); 
                updateStatusMessage(statusMessageEl, '请输入短分享码以查看目录结构。', 'warning');
                return; 
            }
        } else if (target.id === 'viewTreeForLongCodeBtn') {
            shareCode = longBase64DataInput.value.trim();
            if (!shareCode) { 
                alert('请输入长分享码（或从文件加载）。');
                updateStatusMessage(statusMessageEl, '请输入长分享码以查看目录结构。', 'warning');
                return; 
            }
        } else if (target.dataset.codehash) { 
            codeHash = target.dataset.codehash;
        } else {
            console.warn('未知的查看目录按钮被点击:', target);
            return;
        }

        if (codeHash || shareCode) {
            fetchAndDisplayContentTree({ codeHash, shareCode });
        }
    });

    contentTreeSearchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const lines = contentTreeDisplayArea.querySelectorAll('.tree-line-item'); 
        lines.forEach(lineEl => {
            const text = lineEl.textContent.toLowerCase();
            lineEl.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    });

    if (publicSharesListContainer) {
        publicSharesListContainer.addEventListener('scroll', function() {
            const { scrollTop, scrollHeight, clientHeight } = publicSharesListContainer;
            const threshold = 50; 

            if (scrollTop + clientHeight >= scrollHeight - threshold) {
                if (currentSearchTerm) { 
                    if (!isLoadingSearchResults && !isEndOfSearchResults) {
                        loadSharesPage(currentSearchPage + 1, currentSearchTerm);
                    }
                } else { 
                    if (!isLoadingPublicList && !isEndOfPublicList) {
                        loadSharesPage(currentPublicListPage + 1);
                    }
                }
            }
        });
    }

    loadSharesPage(1); 
});