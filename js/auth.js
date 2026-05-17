/** 中韩出海数智港 - 前端认证通用模块 */
const AUTH = {
    getToken() {
        try { return localStorage.getItem('access_token'); } catch(e) { return null; }
    },
    setToken(token, user) {
        try {
            localStorage.setItem('access_token', token);
            if (user) localStorage.setItem('user', JSON.stringify(user));
        } catch(e) { console.warn(e); }
    },
    clearToken() {
        try { localStorage.removeItem('access_token'); localStorage.removeItem('user'); } catch(e) {}
    },
    isLoggedIn() {
        const token = this.getToken();
        if (!token) return false;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.exp && payload.exp < Math.floor(Date.now()/1000)) {
                this.clearToken(); return false;
            }
            return true;
        } catch(e) { return token.length > 0; }
    },
    getUser() {
        try {
            const str = localStorage.getItem('user');
            if (str) return JSON.parse(str);
            const token = this.getToken();
            if (token) {
                const p = JSON.parse(atob(token.split('.')[1]));
                return { id: p.user_id, username: p.username, email: p.email };
            }
            return null;
        } catch(e) { return null; }
    },
    authHeader() {
        const t = this.getToken();
        return t ? { Authorization: `Bearer ${t}` } : {};
    },
    logout(redirect) {
        this.clearToken();
        window.location.href = redirect || '/login.html';
    },
    async fetchQuota() {
        const r = await fetch('/api/v1/auth/quota', { headers: { ...this.authHeader(), 'Content-Type': 'application/json' } });
        const d = await r.json();
        if (d.success) return d.data;
        throw new Error(d.message || '获取额度失败');
    },
    async fetchOrders() {
        const r = await fetch('/api/v1/auth/orders', { headers: { ...this.authHeader(), 'Content-Type': 'application/json' } });
        const d = await r.json();
        if (d.success) return d.data;
        throw new Error(d.message || '获取订单失败');
    },
};
window.AUTH = AUTH;
