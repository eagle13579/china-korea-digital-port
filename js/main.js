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

// 表单提交
const form = document.querySelector('.form');
if (form) {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 获取表单数据
        const formData = {
            company: document.querySelector('input[placeholder="请输入企业名称"]').value,
            contact: document.querySelector('input[placeholder="请输入联系人姓名"]').value,
            phone: document.querySelector('input[placeholder="请输入联系电话"]').value,
            email: document.querySelector('input[placeholder="请输入邮箱地址"]').value,
            message: document.querySelector('textarea[placeholder="请简述您的需求"]').value
        };
        
        // 简单验证
        if (!formData.company || !formData.contact || !formData.phone || !formData.email) {
            alert('请填写必填字段');
            return;
        }
        
        // 模拟提交
        alert('表单提交成功！我们会尽快与您联系。');
        form.reset();
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
}, observerOptions);

const statsSection = document.querySelector('.about__stats');
if (statsSection) {
    statsObserver.observe(statsSection);
}

// 鼠标悬停效果增强
const cards = document.querySelectorAll('.feature__card, .service__item, .info__item, .stat__card');
cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-4px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// 按钮点击效果
const buttons = document.querySelectorAll('.btn');
buttons.forEach(button => {
    button.addEventListener('click', function(e) {
        // 创建点击效果
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
});

// 添加CSS动画样式
const style = document.createElement('style');
style.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 语言数据
const langData = {
    'zh-CN': {
        logo: '中韩出海数智港',
        about: '关于我们',
        services: '服务内容',
        features: '核心功能',
        contact: '联系我们',
        consult: '预约咨询',
        hero_title: '中韩出海数智港',
        hero_subtitle: 'AI赋能企业跨境发展，助力中国企业进韩国，韩国企业进中国',
        hero_consult: '立即咨询',
        hero_learn: '了解更多',
        about_title: '关于中韩出海数智港',
        about_subtitle: 'OPC+AI模式，打造中韩企业跨境发展新生态',
        about_text1: '中韩出海数智港是一个专注于中韩双边企业跨境发展的数智化服务平台，通过AI技术赋能企业，帮助中国企业进入韩国市场，同时助力韩国企业拓展中国市场。',
        about_text2: '我们采用OPC（超级个体）+AI模式，构建高效的服务体系，为企业提供从市场调研、品牌定位到销售增长的全链路解决方案。',
        about_text3: '依托AI销售增长引擎，我们帮助企业实现精准获客、智能谈客、高效管客，大幅提升跨境业务的成功率和效率。',
        stat_companies: '服务企业',
        stat_satisfaction: '客户满意度',
        stat_efficiency: '效率提升',
        features_title: 'AI赋能核心功能',
        features_subtitle: '利用人工智能技术，为企业跨境发展提供智能解决方案',
        feature_analysis: 'AI市场分析',
        feature_analysis_desc: '智能分析中韩市场趋势、竞争格局，为企业提供数据驱动的市场进入策略',
        feature_sales: 'AI销售增长引擎',
        feature_sales_desc: '智能获客、自动谈客、高效管客，提升销售转化率和客户满意度',
        feature_language: 'AI语言服务',
        feature_language_desc: '中韩双语智能翻译、跨文化沟通，消除语言和文化障碍',
        feature_data: 'AI数据分析',
        feature_data_desc: '实时分析业务数据，提供智能决策支持，优化运营策略',
        feature_compliance: 'AI合规审查',
        feature_compliance_desc: '智能识别合规风险，确保企业跨境业务符合两国法规要求',
        feature_talent: 'AI人才匹配',
        feature_talent_desc: '智能匹配中韩双语人才，为企业跨境发展提供人才支持',
        services_title: '中韩双边服务',
        services_subtitle: '为中国企业和韩国企业提供定制化的跨境发展服务',
        service_china_to_korea: '中国企业进韩国',
        service_market_access: '市场准入咨询',
        service_market_access_desc: '韩国市场法规、行业标准、准入要求等专业咨询',
        service_localization: '品牌本地化',
        service_localization_desc: '品牌名称、包装、营销内容的韩国本地化',
        service_channels: '销售渠道搭建',
        service_channels_desc: '韩国线上线下销售渠道的建立和优化',
        service_operation: '本地化运营',
        service_operation_desc: '韩国市场的本地化运营策略和执行',
        service_korea_to_china: '韩国企业进中国',
        service_research: '市场调研分析',
        service_research_desc: '中国市场需求、竞争格局、消费者行为分析',
        service_registration: '合规注册服务',
        service_registration_desc: '中国公司注册、商标申请、资质认证等服务',
        service_ecommerce: '电商平台入驻',
        service_ecommerce_desc: '天猫、京东、抖音等主流电商平台的入驻服务',
        service_marketing: '数字营销',
        service_marketing_desc: '中国社交媒体、搜索营销、内容营销等服务',
        contact_title: '联系我们',
        contact_subtitle: '预约咨询，开启中韩跨境发展之旅',
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
        footer_about: '关于',
        footer_company: '公司介绍',
        footer_advantages: '核心优势',
        footer_partners: '合作伙伴',
        footer_follow: '关注我们',
         '© 2026 中韩出海数智港. 保留所有权利. 沪ICP备2026007459号  
        footer_privacy: '隐私政策',
        footer_terms: '服务条款'
    },
    'ko-KR': {
        logo: '한중 해외진출 디지털 포트',
        about: '회사 소개',
        services: '서비스 내용',
        features: '핵심 기능',
        contact: '연락처',
        consult: '상담 예약',
        hero_title: '한중 해외진출 디지털 포트',
        hero_subtitle: 'AI로 기업 해외진출을赋能，중국 기업의 한국 진출과 한국 기업의 중국 진출을 지원',
        hero_consult: '즉시 상담',
        hero_learn: '자세히 알아보기',
        about_title: '한중 해외진출 디지털 포트 소개',
        about_subtitle: 'OPC+AI 모델로 한중 기업 해외진출 새로운 생태계 구축',
        about_text1: '한중 해외진출 디지털 포트는 한중 양국 기업의 해외진출을 위한 디지털 서비스 플랫폼으로, AI 기술을 통해 기업을赋能하여 중국 기업의 한국 시장 진출과 한국 기업의 중국 시장 확장을 도와줍니다.',
        about_text2: '우리는 OPC(슈퍼 개체)+AI 모델을 채택하여 효율적인 서비스 체계를 구축하고, 기업에 시장 조사、브랜드 위치 설정부터 판매 성장까지 전 과정 솔루션을 제공합니다.',
        about_text3: 'AI 판매 성장 엔진을依托하여 기업이 정확한 고객 획득、지능형 고객 상담、효율적인 고객 관리를 실현하도록 도와줌으로써 해외 사업의 성공률과 효율성을 크게 향상시킵니다.',
        stat_companies: '서비스 기업',
        stat_satisfaction: '고객 만족도',
        stat_efficiency: '효율성 향상',
        features_title: 'AI赋能 핵심 기능',
        features_subtitle: '인공 지능 기술을 활용하여 기업 해외진출을 위한 지능형 솔루션 제공',
        feature_analysis: 'AI 시장 분석',
        feature_analysis_desc: '한중 시장 동향、경쟁 구조를 지능적으로 분석하여 기업에 데이터 기반 시장 진입 전략 제공',
        feature_sales: 'AI 판매 성장 엔진',
        feature_sales_desc: '지능형 고객 획득、자동 상담、효율적인 고객 관리로 판매 전환율과 고객 만족도 향상',
        feature_language: 'AI 언어 서비스',
        feature_language_desc: '한중 양국 언어 지능 번역、문화 차이 해소를 통한 원활한 의사소통',
        feature_data: 'AI 데이터 분석',
        feature_data_desc: '실시간 비즈니스 데이터 분석으로 지능형 의사결정 지원，운영 전략 최적화',
        feature_compliance: 'AI 준법 검토',
        feature_compliance_desc: '준법 위험을 지능적으로 식별하여 기업 해외 사업이 양국 법규 요구사항을 준수하도록 보장',
        feature_talent: 'AI 인재 매칭',
        feature_talent_desc: '한중 양국 언어 능력을 가진 인재를 지능적으로 매칭하여 기업 해외진출에 인재 지원',
        services_title: '한중 양국 서비스',
        services_subtitle: '중국 기업과 한국 기업을 위한 맞춤형 해외진출 서비스 제공',
        service_china_to_korea: '중국 기업 한국 진출',
        service_market_access: '시장 진입 상담',
        service_market_access_desc: '한국 시장 법규、산업 표준、진입 요구사항 등 전문 상담',
        service_localization: '브랜드 현지화',
        service_localization_desc: '브랜드 이름、포장、마케팅 콘텐츠의 한국 현지화',
        service_channels: '판매 채널 구축',
        service_channels_desc: '한국 온라인 및 오프라인 판매 채널 구축 및 최적화',
        service_operation: '현지화 운영',
        service_operation_desc: '한국 시장의 현지화 운영 전략 및 실행',
        service_korea_to_china: '한국 기업 중국 진입',
        service_research: '시장 조사 분석',
        service_research_desc: '중국 시장 수요、경쟁 구조、소비자 행동 분석',
        service_registration: '준법 등록 서비스',
        service_registration_desc: '중국 회사 등록、상표 신청、자격 인증 등 서비스',
        service_ecommerce: '전자상거래 플랫폼 입점',
        service_ecommerce_desc: '티몰、징동、도인 등 주요 전자상거래 플랫폼 입점 서비스',
        service_marketing: '디지털 마케팅',
        service_marketing_desc: '중국 소셜 미디어、검색 마케팅、콘텐츠 마케팅 등 서비스',
        contact_title: '연락처',
        contact_subtitle: '상담 예약으로 한중 해외진출 여정을 시작하세요',
        form_company: '기업 이름',
        form_contact: '연락처',
        form_phone: '전화',
        form_email: '이메일',
        form_message: '상담 내용',
        form_submit: '상담 제출',
        info_phone: '전화',
        info_email: '이메일',
        info_address: '주소',
        info_address_detail: '베이징시 조양구 건국로 88호',
        info_hours: '업무 시간',
        info_hours_detail: '월요일부터 금요일 9:00-18:00',
        footer_tagline: 'AI로 기업 해외진출赋能',
        footer_services: '서비스',
        footer_ai_services: 'AI赋能 서비스',
        footer_opc_ai: 'OPC+AI 모델',
        footer_about: '소개',
        footer_company: '회사 소개',
        footer_advantages: '핵심 장점',
        footer_partners: '협력 파트너',
        footer_follow: '팔로우',
         '© 2026 한중 해외진출 디지털 포트. 모든 권리 보유.',
        footer_privacy: '개인 정보 보호 정책',
        footer_terms: '서비스 약관'
    }
};

// 语言切换函数
function changeLanguage(lang) {
    // 更新语言按钮状态
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.lang === lang) {
            btn.classList.add('active');
        }
    });
    
    // 更新所有带有data-lang-key属性的元素
    document.querySelectorAll('[data-lang-key]').forEach(el => {
        const key = el.dataset.langKey;
        if (langData[lang][key]) {
            el.textContent = langData[lang][key];
        }
    });
    
    // 更新placeholder
    document.querySelectorAll('[data-placeholder-zh]').forEach(el => {
        if (lang === 'zh-CN') {
            el.placeholder = el.dataset.placeholderZh;
        } else if (lang === 'ko-KR') {
            el.placeholder = el.dataset.placeholderKo;
        }
    });
    
    // 保存当前语言到本地存储
    localStorage.setItem('preferredLanguage', lang);
}

// 初始化语言
function initLanguage() {
    // 从本地存储获取语言，默认中文
    const savedLang = localStorage.getItem('preferredLanguage') || 'zh-CN';
    changeLanguage(savedLang);
}

// 主题切换函数
function toggleTheme() {
    const body = document.body;
    const themeBtn = document.getElementById('themeToggle');
    const themeIcon = themeBtn.querySelector('i');
    
    // 切换主题类
    body.classList.toggle('light-mode');
    
    // 更新图标
    if (body.classList.contains('light-mode')) {
        themeIcon.classList.remove('bi-moon');
        themeIcon.classList.add('bi-sun');
        localStorage.setItem('theme', 'light');
    } else {
        themeIcon.classList.remove('bi-sun');
        themeIcon.classList.add('bi-moon');
        localStorage.setItem('theme', 'dark');
    }
}

// 初始化主题
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    const body = document.body;
    const themeIcon = document.querySelector('#themeToggle i');
    
    if (savedTheme === 'light') {
        body.classList.add('light-mode');
        themeIcon.classList.remove('bi-moon');
        themeIcon.classList.add('bi-sun');
    } else {
        body.classList.remove('light-mode');
        themeIcon.classList.remove('bi-sun');
        themeIcon.classList.add('bi-moon');
    }
}

// 页面加载完成后的初始化
window.addEventListener('load', function() {
    // 为Hero区域添加入场动画
    const heroText = document.querySelector('.hero__text');
    if (heroText) {
        heroText.style.animation = 'fadeIn 1s ease-out';
    }
    
    const heroVisual = document.querySelector('.hero__visual');
    if (heroVisual) {
        heroVisual.style.animation = 'fadeIn 1s ease-out 0.3s both';
    }
    
    // 初始化语言
    initLanguage();
    
    // 初始化主题
    initTheme();
    
    // 添加语言切换事件监听器
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const lang = this.dataset.lang;
            changeLanguage(lang);
        });
    });
    
    // 添加主题切换事件监听器
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
});
