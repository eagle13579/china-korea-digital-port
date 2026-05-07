/**
 * auth.js - 通用认证模块
 * 提供统一的 token 管理、登录状态判断、用户信息存取
 * 依赖: 无（纯原生 JS）
 */

window.auth = {
    /**
     * 获取存储的 access_token
     */
    getToken() {
        return localStorage.getItem('access_token');
    },

    /**
     * 存储 token 和用户信息
     * @param {string} token - JWT access_token
     * @param {object} user - 用户对象 {id, username, email, created_at}
     */
    setToken(token, user) {
        localStorage.setItem('access_token', token);
        if (user) {
            localStorage.setItem('user', JSON.stringify(user));
        }
    },

    /**
     * 清除所有认证信息（登出）
     */
    clearToken() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
    },

    /**
     * 判断用户是否已登录
     * @returns {boolean}
     */
    isLoggedIn() {
        return !!localStorage.getItem('access_token');
    },

    /**
     * 获取当前登录用户信息
     * @returns {object|null} 用户对象或 null
     */
    getUser() {
        try {
            const raw = localStorage.getItem('user');
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    },

    /**
     * 获取用于 API 请求的 Authorization header 对象
     * @returns {object} {Authorization: 'Bearer xxx'} 或 {}
     */
    authHeader() {
        const token = this.getToken();
        return token ? { Authorization: 'Bearer ' + token } : {};
    },

    /**
     * 登出并跳转到首页
     */
    logout() {
        this.clearToken();
        window.location.href = '/';
    },

    /**
     * 获取当前登录用户的用户名（用于显示）
     * @returns {string}
     */
    getDisplayName() {
        const user = this.getUser();
        return user ? user.username : '';
    }
};
