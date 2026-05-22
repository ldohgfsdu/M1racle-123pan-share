// static/js/cookieUtils.js

/**
 * 设置 Cookie。
 * @param {string} name Cookie 名称。
 * @param {string} value Cookie 值。
 * @param {number} days Cookie 的有效天数。
 */
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        let date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/; SameSite=Lax";
}

/**
 * 获取 Cookie 值。
 * @param {string} name Cookie 名称。
 * @returns {string|null} Cookie 的值，如果不存在则返回 null。
 */
function getCookie(name) {
    let nameEQ = name + "=";
    let ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}