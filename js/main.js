// 导航栏滚动效果
window.addEventListener('scroll', function() {
    const header = document.querySelector('.header');
    if (window.scrollY > 50) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});

// 平滑滚动
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ===== SEO Meta 更新函数 =====
function updateSEOMeta(lang) {
    var seoData = window._seoMeta || {};
    var data = seoData[lang];
    if (!data) return;

    // 更新 lang 属性
    document.documentElement.lang = lang;

    // 更新 meta description
    var metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc && data.description) metaDesc.content = data.description;

    // 更新 OG tags
    var ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle && data.og_title) ogTitle.content = data.og_title;
    var ogDesc = document.querySelector('meta[property="og:description"]');
    if (ogDesc && data.og_description) ogDesc.content = data.og_description;

    // 更新 Twitter Card
    var twTitle = document.querySelector('meta[name="twitter:title"]');
    if (twTitle && data.og_title) twTitle.content = data.og_title;
    var twDesc = document.querySelector('meta[name="twitter:description"]');
    if (twDesc && data.og_description) twDesc.content = data.og_description;

    // 更新 JSON-LD（替换整个 script 块）
    var jsonld = document.querySelector('script[type="application/ld+json"]');
    if (jsonld && data.jsonld) {
        jsonld.textContent = JSON.stringify(data.jsonld);
    }

    // 更新网页标题
    if (data.title) {
        document.title = data.title;
    }
}

// 设置中韩双语 SEO 数据（每个页面各自扩展）
window._seoMeta = window._seoMeta || {};
window._seoMeta['zh-CN'] = window._seoMeta['zh-CN'] || {
    description: '中韩出海数智港 - AI赋能企业跨境发展，助力中国企业进韩国，韩国企业进中国。提供AI数字合规官、市场准入咨询、合规诊断等一站式服务。',
    og_title: '中韩出海数智港 - AI赋能企业跨境发展',
    og_description: 'AI驱动中韩跨境商业落地平台，6位AI数字合规官为韩企进入中国市场提供一站式解决方案。',
    title: '中韩出海数智港 - AI赋能企业跨境发展'
};
window._seoMeta['ko-KR'] = window._seoMeta['ko-KR'] || {
    description: '중한 해외진출 디지털 포트 - AI 기반 기업 해외진출 플랫폼, 중국 기업의 한국 진출, 한국 기업의 중국 진출 지원. AI 디지털 규제 전문가, 시장 진출 컨설팅, 규제 진단 등 원스톱 서비스.',
    og_title: '중한 해외진출 디지털 포트 - AI 기반 해외진출 플랫폼',
    og_description: 'AI 기반 중한跨境 비즈니스 플랫폼, 6명의 AI 디지털 규제 전문가가 한국 기업의 중국 시장 진출을 위한 원스톱 솔루션 제공.',
    title: '중한 해외진출 디지털 포트 - AI 기반 해외진출 플랫폼'
};

// ===== 表单提交逻辑（使用name属性收集数据，Toast替代alert） =====
const form = document.querySelector('.form');
if (form) {
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        window.submitForm(form, '/api/v1/contact', null, 'success_contact');
    });
}

// 滚动动画
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animated-element');
        }
    });
}, observerOptions);

// 观察所有需要动画的元素
document.querySelectorAll('.section__header, .feature__card, .service__item, .info__item, .stat__card').forEach(el => {
    observer.observe(el);
});

// 数字增长动画
function animateNumbers() {
    const numberElements = document.querySelectorAll('.stat__number');
    numberElements.forEach(element => {
        const target = element.textContent;
        const numericValue = parseInt(target.replace(/[^0-9]/g, ''));
        const suffix = target.replace(/[0-9]/g, '');

        let current = 0;
        const increment = numericValue / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= numericValue) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current) + suffix;
            }
        }, 30);
    });
}

// 当统计卡片进入视口时触发数字动画
const statsObserver = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateNumbers();
            statsObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

const statsSection = document.querySelector('.stats');
if (statsSection) {
    statsObserver.observe(statsSection);
}

// 语言切换
document.addEventListener('DOMContentLoaded', function() {
    // 获取当前语言（默认中文）
    let currentLang = localStorage.getItem('lang') || 'zh-CN';

    // 切换语言
    const langBtns = document.querySelectorAll('.lang-btn');

    function switchLang(lang) {
        currentLang = lang;
        localStorage.setItem('lang', lang);

        // 更新按钮状态
        langBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });

        // 更新所有 data-lang-key 元素
        document.querySelectorAll('[data-lang-key]').forEach(element => {
            const key = element.dataset.langKey;
            const langData = translations[currentLang];
            if (langData && langData[key]) {
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    const placeholderKey = element.dataset.placeholderZh || element.dataset.placeholderKo;
                    if (placeholderKey) {
                        element.placeholder = langData[key] || element.placeholder;
                    }
                } else {
                    element.textContent = langData[key];
                }
            }
        });

        // 同步更新 SEO meta
        updateSEOMeta(lang);
    }

    langBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            switchLang(this.dataset.lang);
        });
    });

    // 主题切换
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
            themeToggle.innerHTML = '<i class="bi bi-sun"></i>';
        }

        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('light-mode');
            const isLight = document.body.classList.contains('light-mode');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            themeToggle.innerHTML = isLight ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon"></i>';
        });
    }

    // 初始化语言
    switchLang(currentLang);
});

// 中韩双语翻译数据
const translations = {
    'zh-CN': {
        logo: '中韩出海数智港',
        about: '关于我们',
        services: '服务内容',
        features: '核心功能',
        home: '首页',
        team_nav: '数字员工团队',
        contact: '联系我们',
        consult: '预约咨询',
        hero_title: '中韩出海数智港',
        hero_subtitle: 'AI赋能企业跨境发展，助力中国企业进韩国，韩国企业进中国',
        hero_consult: '立即咨询',
        hero_learn: '了解更多',
        about_title: '关于我们',
        about_desc: '中韩出海数智港是AI驱动的中韩跨境商业落地平台，以6位AI数字合规官为核心，为韩企进入中国市场提供一站式解决方案。',
        services_title: '服务内容',
        service_china_to_korea: '中国企业进韩国',
        service_china_to_korea_desc: '为中国企业提供韩国市场准入、公司设立、税务筹划等全方位服务',
        service_korea_to_china: '韩国企业进中国',
        service_korea_to_china_desc: '为韩国企业提供中国市场准入、合规诊断、品牌落地等一站式解决方案',
        service_ai_services: 'AI赋能服务',
        service_ai_services_desc: 'AI数字员工驱动的市场分析、合规诊断、情报监控，让决策更智能',
        features_title: '核心功能',
        feature_digital_employees: '数字合规官',
        feature_digital_employees_desc: '6位AI数字员工覆盖行业准入、数据安全、知识产权、财税、用工、签证全链路',
        feature_ai_analysis: 'AI智能分析',
        feature_ai_analysis_desc: '基于大数据和AI算法的市场趋势分析、竞争对手洞察、风险评估',
        feature_compliance_diagnosis: '合规诊断',
        feature_compliance_diagnosis_desc: '自动化合规检查清单，覆盖外商投资、数据安全、劳动用工等关键领域',
        feature_market_intelligence: '市场情报',
        feature_market_intelligence_desc: '实时监控中韩市场动态、政策变化、竞品动向，第一时间获取商业情报',
        stats_clients: '服务企业',
        stats_experts: '领域专家',
        stats_success_rate: '成功率',
        stats_countries: '覆盖国家',
        form_company: '企业名称',
        form_contact: '联系人',
        form_phone: '电话',
        form_email: '邮箱',
        form_message: '咨询内容',
        form_submit: '提交咨询',
        info_phone: '电话',
        info_email: '邮箱',
        info_address: '地址',
        info_address_detail: '北京市朝阳区建国路88号',
        info_hours: '工作时间',
        info_hours_detail: '周一至周五 9:00-18:00',
        footer_tagline: 'AI赋能企业跨境发展',
        footer_services: '服务',
        footer_ai_services: 'AI赋能服务',
        footer_opc_ai: 'OPC+AI模式',
        footer_pricing: '定价/购买',
        footer_about: '关于',
        footer_company: '公司介绍',
        footer_advantages: '核心优势',
        footer_partners: '合作伙伴',
        footer_follow: '关注我们',
        footer_copyright: '© 2026 中韩出海数智港. 保留所有权利.',
        footer_privacy: '隐私政策',
        footer_terms: '服务条款',
        about_vision: '我们的愿景',
        about_vision_desc: '成为中韩跨境商业领域最值得信赖的AI驱动服务平台',
        about_mission: '我们的使命',
        about_mission_desc: '用AI技术降低中韩企业跨境经营的门槛和成本',
        about_advantage: '我们的优势',
        about_advantage_desc: 'AI数字员工24小时在线，专业合规官全程陪跑，让跨境不再复杂',
        contact_title: '联系我们',
        contact_subtitle: '预约咨询，开启中韩跨境发展之旅',
        service_china: '中国企业进韩国',
        service_china_desc: '为中国企业提供韩国市场准入、公司设立、税务筹划等全方位服务',
        service_korea: '韩国企业进中国',
        service_korea_desc: '为韩国企业提供中国市场准入、合规诊断、品牌落地等一站式解决方案',
        service_ai: 'AI赋能服务',
        service_ai_desc: 'AI数字员工驱动的市场分析、合规诊断、情报监控',
        feature_employees: '数字合规官',
        feature_employees_desc: '6位AI数字员工覆盖行业准入、数据安全、知识产权、财税、用工、签证全链路',
    },
    'ko-KR': {
        logo: '중한 해외진출 디지털 포트',
        about: '회사 소개',
        services: '서비스',
        features: '핵심 기능',
        home: '홈',
        team_nav: '디지털 직원 팀',
        contact: '문의하기',
        consult: '상담 예약',
        hero_title: '중한 해외진출 디지털 포트',
        hero_subtitle: 'AI 기반 기업 해외진출 플랫폼, 중국 기업의 한국 진출, 한국 기업의 중국 진출 지원',
        hero_consult: '지금 문의',
        hero_learn: '더 알아보기',
        about_title: '회사 소개',
        about_desc: '중한 해외진출 디지털 포트는 AI 기반의 중한跨境 비즈니스 플랫폼입니다. 6명의 AI 디지털 규제 전문가가 한국 기업의 중국 시장 진출을 위한 원스톱 솔루션을 제공합니다.',
        services_title: '서비스',
        service_china_to_korea: '중국 기업의 한국 진출',
        service_china_to_korea_desc: '중국 기업 대상 한국 시장 진출, 법인 설립, 세무 계획 등 종합 서비스',
        service_korea_to_china: '한국 기업의 중국 진출',
        service_korea_to_china_desc: '한국 기업 대상 중국 시장 진출, 규제 진단, 브랜드 론칭 등 원스톱 솔루션',
        service_ai_services: 'AI 서비스',
        service_ai_services_desc: 'AI 디지털 직원 기반 시장 분석, 규제 진단, 정보 모니터링',
        features_title: '핵심 기능',
        feature_digital_employees: '디지털 규제 전문가',
        feature_digital_employees_desc: '6명의 AI 디지털 직원이 업종 허가, 데이터 보안, 지식재산권, 재무세무, 고용, 비자 전 과정 커버',
        feature_ai_analysis: 'AI 분석',
        feature_ai_analysis_desc: '빅데이터와 AI 알고리즘 기반 시장 동향 분석, 경쟁사 인사이트, 리스크 평가',
        feature_compliance_diagnosis: '규제 진단',
        feature_compliance_diagnosis_desc: '외국인 투자, 데이터 보안, 노동 고용 등 핵심 영역의 자동화된 규제 체크리스트',
        feature_market_intelligence: '시장 정보',
        feature_market_intelligence_desc: '중한 시장 동향, 정책 변화, 경쟁사 동향 실시간 모니터링',
        stats_clients: '서비스 기업',
        stats_experts: '전문가',
        stats_success_rate: '성공률',
        stats_countries: '커버 국가',
        form_company: '기업명',
        form_contact: '연락처',
        form_phone: '전화번호',
        form_email: '이메일',
        form_message: '문의 내용',
        form_submit: '상담 제출',
        info_phone: '전화',
        info_email: '이메일',
        info_address: '주소',
        info_address_detail: '중국 베이징시 차오양구 진궈로 88호',
        info_hours: '근무 시간',
        info_hours_detail: '월-금 9:00-18:00',
        footer_tagline: 'AI 기반 기업 해외진출 플랫폼',
        footer_services: '서비스',
        footer_ai_services: 'AI 서비스',
        footer_opc_ai: 'OPC+AI 모드',
        footer_pricing: '가격/구매',
        footer_about: '회사 소개',
        footer_company: '회사 개요',
        footer_advantages: '핵심 장점',
        footer_partners: '파트너',
        footer_follow: '팔로우',
        footer_copyright: '© 2026 중한 해외진출 디지털 포트. All rights reserved.',
        footer_privacy: '개인정보처리방침',
        footer_terms: '이용약관',
        about_vision: '비전',
        about_vision_desc: '중한跨境 비즈니스 분야에서 가장 신뢰받는 AI 기반 서비스 플랫폼',
        about_mission: '미션',
        about_mission_desc: 'AI 기술로 중한 기업의 해외 진출 장벽과 비용을 낮추는 것',
        about_advantage: '강점',
        about_advantage_desc: 'AI 디지털 직원 24시간 온라인, 전문 규제 전문가 전담 지원',
        contact_title: '문의하기',
        contact_subtitle: '상담 예약으로 중한 해외진출 여정을 시작하세요',
        service_china: '중국 기업의 한국 진출',
        service_china_desc: '중국 기업 대상 한국 시장 진출, 법인 설립, 세무 계획 등 종합 서비스',
        service_korea: '한국 기업의 중국 진출',
        service_korea_desc: '한국 기업 대상 중국 시장 진출, 규제 진단, 브랜드 론칭 등 원스톱 솔루션',
        service_ai: 'AI 서비스',
        service_ai_desc: 'AI 디지털 직원 기반 시장 분석, 규제 진단, 정보 모니터링',
        feature_employees: '디지털 규제 전문가',
        feature_employees_desc: '6명의 AI 디지털 직원이 업종 허가, 데이터 보안, 지식재산권, 재무세무, 고용, 비자 전 과정 커버',
    }
};
