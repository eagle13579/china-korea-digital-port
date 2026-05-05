/**
 * Toast 消息组件 - 全局、无依赖、中韩双语
 * 使用方式: showToast(message, type, duration)
 *   message: 字符串消息（会自动支持中韩双语）
 *   type: 'success' | 'error' | 'info'
 *   duration: 显示时长（ms），默认3500
 */
(function() {
    window.showToast = function(message, type, duration) {
        type = type || 'success';
        duration = duration || 3500;

        // 确保容器存在
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText =
                'position:fixed;top:20px;right:20px;z-index:9999;' +
                'display:flex;flex-direction:column;gap:12px;' +
                'pointer-events:none;';
            document.body.appendChild(container);
        }

        // 创建 Toast 元素
        const toast = document.createElement('div');

        const isSuccess = type === 'success';
        const bgColor = isSuccess ? '#16a34a' : '#dc2626';
        const borderColor = isSuccess ? 'rgba(22,163,74,0.3)' : 'rgba(220,38,38,0.3)';
        const textColor = '#ffffff';
        const icon = isSuccess ? 'bi-check-circle-fill' : 'bi-x-circle-fill';

        toast.style.cssText =
            'display:flex;align-items:flex-start;gap:12px;' +
            'padding:16px 20px;border-radius:12px;' +
            'background:' + bgColor + ';' +
            'color:' + textColor + ';' +
            'font-size:14px;line-height:1.5;' +
            'max-width:420px;min-width:280px;' +
            'box-shadow:0 8px 24px rgba(0,0,0,0.2);' +
            'border:1px solid ' + borderColor + ';' +
            'pointer-events:auto;' +
            'transition:all 0.3s ease;' +
            'transform:translateX(120%);opacity:0;';

        // 图标
        const iconEl = document.createElement('i');
        iconEl.className = 'bi ' + icon;
        iconEl.style.cssText = 'font-size:18px;flex-shrink:0;margin-top:1px;';
        toast.appendChild(iconEl);

        // 消息文本
        const msgEl = document.createElement('span');
        msgEl.style.cssText = 'flex:1;word-break:break-word;';
        msgEl.textContent = message;  // XSS-safe: textContent not innerHTML
        toast.appendChild(msgEl);

        // 关闭按钮
        const closeEl = document.createElement('i');
        closeEl.className = 'bi bi-x';
        closeEl.style.cssText =
            'font-size:18px;cursor:pointer;flex-shrink:0;' +
            'opacity:0.7;transition:opacity 0.2s;';
        closeEl.addEventListener('click', function() {
            dismissToast(toast);
        });
        closeEl.addEventListener('mouseenter', function() {
            this.style.opacity = '1';
        });
        closeEl.addEventListener('mouseleave', function() {
            this.style.opacity = '0.7';
        });
        toast.appendChild(closeEl);

        // 添加前先让浏览器渲染一下，好让 transition 生效
        requestAnimationFrame(function() {
            container.appendChild(toast);
            requestAnimationFrame(function() {
                toast.style.transform = 'translateX(0)';
                toast.style.opacity = '1';
            });
        });

        // 自动关闭
        const autoDismiss = setTimeout(function() {
            dismissToast(toast);
        }, duration);

        // 保存 timeout 引用，以便手动关闭时取消
        toast._autoDismiss = autoDismiss;

        return toast;
    };

    function dismissToast(toast) {
        if (toast._dismissed) return;
        toast._dismissed = true;
        clearTimeout(toast._autoDismiss);
        toast.style.transform = 'translateX(120%)';
        toast.style.opacity = '0';
        setTimeout(function() {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    /**
     * 获取当前语言的 Toast 文案
     * @param {string} key - 'success_contact' | 'error_network' 等
     */
    window.getToastMessage = function(key) {
        var lang = localStorage.getItem('lang') || 'zh-CN';
        var messages = {
            'zh-CN': {
                success_contact: '感谢您的咨询！我们将在24小时内与您联系。',
                success_demo: '演示预约已提交！我们的团队将尽快与您确认具体时间。',
                success_pricing: '您的咨询已收到！销售团队将主动联系您。',
                success_service_inquiry: '邀请已提交！销售团队将主动联系您。',
                error_network: '提交失败：网络连接异常，请稍后重试。',
                error_default: '提交失败，请稍后重试。',
                validation_required: '请填写必填字段',
                validation_email: '请输入有效的邮箱地址',
            },
            'ko-KR': {
                success_contact: '문의가 접수되었습니다! 24시간 내에 연락드리겠습니다.',
                success_demo: '데모 예약이 접수되었습니다! 빠른 시일 내에 일정을 확인해 드리겠습니다.',
                success_pricing: '문의가 접수되었습니다! 영업팀이 연락드릴 것입니다.',
                success_service_inquiry: '초대가 접수되었습니다! 영업팀이 연락드릴 것입니다.',
                error_network: '제출 실패: 네트워크 연결 오류, 나중에 다시 시도해 주세요.',
                error_default: '제출 실패, 나중에 다시 시도해 주세요.',
                validation_required: '필수 항목을 입력하세요',
                validation_email: '유효한 이메일 주소를 입력하세요',
            }
        };
        return (messages[lang] && messages[lang][key]) || messages['zh-CN'][key] || key;
    };

    /**
     * 通用表单提交函数 - 自动收集name属性数据，调用API，显示Toast
     * @param {HTMLFormElement} form - 表单元素
     * @param {string} endpoint - API端点 (如 '/api/v1/contact')
     * @param {function} extraData - 可选的额外数据处理函数 (formData) => formData
     * @param {string} successKey - Toast消息key
     */
    window.submitForm = async function(form, endpoint, extraData, successKey) {
        var submitBtn = form.querySelector('button[type="submit"]');
        if (!submitBtn) return;

        // 收集表单数据（通过 name 属性自动收集）
        var formData = {};
        form.querySelectorAll('input, textarea, select').forEach(function(el) {
            if (el.name) {
                formData[el.name] = el.value;
            }
        });

        // 额外数据处理
        if (typeof extraData === 'function') {
            formData = extraData(formData);
        }

        // 客户端校验
        var lang = localStorage.getItem('lang') || 'zh-CN';
        var requiredFields = form.querySelectorAll('[required]');
        var valid = true;
        requiredFields.forEach(function(el) {
            if (!el.value.trim()) {
                valid = false;
                el.style.borderColor = '#dc2626';
            } else {
                el.style.borderColor = '';
            }
        });

        if (!valid) {
            showToast(window.getToastMessage('validation_required'), 'error');
            return;
        }

        // 邮箱格式校验（如果有 email 字段）
        if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            showToast(window.getToastMessage('validation_email'), 'error');
            return;
        }

        // 禁用按钮，显示提交中
        submitBtn.disabled = true;
        var originalText = submitBtn.textContent;
        submitBtn.textContent = lang === 'ko-KR' ? '제출 중...' : '提交中...';

        try {
            var response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            var result = await response.json();

            if (response.ok && result.success === true) {
                showToast(successKey ? window.getToastMessage(successKey) : (result.message || '提交成功'), 'success');
                form.reset();
            } else {
                var errMsg = result.detail || result.message || window.getToastMessage('error_default');
                showToast(errMsg, 'error');
            }
        } catch (err) {
            showToast(window.getToastMessage('error_network'), 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    };
})();
