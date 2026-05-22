// static/js/adminLoginPage.js

document.addEventListener('DOMContentLoaded', function () {
    const usernameInput = document.getElementById('username');

    // 从 Cookie 加载用户名
    const savedAdminUsername = getCookie('admin_username');
    if (savedAdminUsername && usernameInput) {
        usernameInput.value = savedAdminUsername;
    }

    // 登录表单提交时，用户名通常由后端设置到cookie，如果需要前端也保存，可以在表单提交事件中处理
    // const adminLoginForm = document.getElementById('adminLoginForm');
    // if(adminLoginForm) {
    //     adminLoginForm.addEventListener('submit', function() {
    //         if (usernameInput && usernameInput.value) {
    //             setCookie('admin_username', usernameInput.value, 30);
    //         }
    //     });
    // }
});