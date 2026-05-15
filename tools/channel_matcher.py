#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中韩贸易网关 — 渠道AI匹配引擎
=============================
为中国进口渠道与韩国产品提供智能匹配评分，
支持精品超市、便利店、电商、社区团购、私域、企业等多种渠道类型。

Usage:
    python3 tools/channel_matcher.py latte                  # 匹配抹茶拿铁的最佳渠道
    python3 tools/channel_matcher.py latte --top 5          # 只看 Top 5
    python3 tools/channel_matcher.py --list-channels        # 列出所有渠道
    python3 tools/channel_matcher.py latte --format json    # JSON 格式输出
    python3 tools/channel_matcher.py --help                 # 帮助信息
"""

import json
import sys
import math
from copy import deepcopy

# ═══════════════════════════════════════════════════════════════
# 第一部分：中国渠道数据库（20+ 渠道，含渠道画像）
# ═══════════════════════════════════════════════════════════════

CHANNELS = [
    # ─── 精品超市 ───
    {
        "name": "盒马鲜生",
        "type": "精品超市",
        "city_coverage": ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "重庆", "西安", "苏州", "长沙", "宁波", "青岛", "合肥", "福州", "厦门", "天津", "郑州", "昆明"],
        "min_order_value": 50000,
        "preferred_categories": ["冲饮", "乳制品", "烘焙", "方便食品", "进口食品", "有机食品", "咖啡"],
        "commission_rate": 0.20,
        "contact_person": "盒马国际采购部（待确认）",
        "rating": 4.8,
        "notes": "阿里旗下新零售标杆，日式+韩式进口食品接受度高，有专门的国际食品区"
    },
    {
        "name": "KKV",
        "type": "精品超市",
        "city_coverage": ["上海", "北京", "广州", "深圳", "成都", "武汉", "重庆", "杭州", "南京", "长沙", "西安", "苏州", "天津", "宁波", "郑州", "合肥", "佛山", "东莞", "厦门", "沈阳"],
        "min_order_value": 30000,
        "preferred_categories": ["进口食品", "零食", "咖啡", "冲饮", "美妆", "生活用品"],
        "commission_rate": 0.25,
        "contact_person": "KKV 选品部（待确认）",
        "rating": 4.5,
        "notes": "以Z世代为目标客群的高颜值潮流集合店，韩系产品热度高"
    },
    {
        "name": "山姆会员商店",
        "type": "精品超市",
        "city_coverage": ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "重庆", "苏州", "宁波", "长沙", "福州", "厦门", "天津", "郑州", "沈阳", "大连", "青岛", "昆明"],
        "min_order_value": 200000,
        "preferred_categories": ["进口食品", "乳制品", "冲饮", "烘焙", "冷冻食品", "有机食品"],
        "commission_rate": 0.15,
        "contact_person": "沃尔玛国际采购（待确认）",
        "rating": 4.7,
        "notes": "仓储式会员制，对进口食品的品控严格，包装规格要求大包装"
    },
    {
        "name": "Costco",
        "type": "精品超市",
        "city_coverage": ["上海", "深圳", "广州", "杭州", "苏州", "宁波", "南京", "北京"],
        "min_order_value": 300000,
        "preferred_categories": ["进口食品", "冲饮", "烘焙", "冷冻食品", "乳制品", "有机食品"],
        "commission_rate": 0.12,
        "contact_person": "Costco 亚洲采购部（待确认）",
        "rating": 4.6,
        "notes": "会员制仓储超市，对单品的大规模稳定供应要求高"
    },
    {
        "name": "Ole' 精品超市",
        "type": "精品超市",
        "city_coverage": ["深圳", "广州", "上海", "北京", "成都", "重庆", "杭州", "南京", "西安", "武汉", "长沙", "苏州", "沈阳", "大连", "南宁", "昆明", "厦门", "福州", "天津"],
        "min_order_value": 50000,
        "preferred_categories": ["进口食品", "冲饮", "咖啡", "乳制品", "烘焙", "有机食品", "酒类"],
        "commission_rate": 0.22,
        "contact_person": "华润万家 Ole' 采购部（待确认）",
        "rating": 4.4,
        "notes": "华润旗下高端精品超市，进口食品占比极高，韩系产品接受度好"
    },
    {
        "name": "绿地优选",
        "type": "精品超市",
        "city_coverage": ["上海", "北京", "广州", "深圳", "成都", "重庆", "武汉", "南京", "杭州", "西安", "苏州", "宁波", "长沙", "天津", "济南", "青岛", "大连"],
        "min_order_value": 40000,
        "preferred_categories": ["进口食品", "冲饮", "咖啡", "乳制品", "冷冻食品", "酒类"],
        "commission_rate": 0.23,
        "contact_person": "绿地全球商品贸易港（待确认）",
        "rating": 4.0,
        "notes": "依托绿地全球商品贸易港，进口渠道资源丰富"
    },
    # ─── 便利店 ───
    {
        "name": "罗森",
        "type": "便利店",
        "city_coverage": ["上海", "北京", "广州", "深圳", "重庆", "成都", "武汉", "杭州", "南京", "苏州", "宁波", "无锡", "常州", "沈阳", "天津", "大连", "合肥", "长沙", "福州", "厦门"],
        "min_order_value": 20000,
        "preferred_categories": ["冲饮", "咖啡", "乳制品", "零食", "烘焙", "方便食品"],
        "commission_rate": 0.18,
        "contact_person": "罗森中国商品部（待确认）",
        "rating": 4.6,
        "notes": "日系便利店，对日韩饮料接受度极高，鲜食+饮品组合销售能力强"
    },
    {
        "name": "全家",
        "type": "便利店",
        "city_coverage": ["上海", "广州", "深圳", "北京", "成都", "杭州", "苏州", "无锡", "南京", "武汉", "宁波", "重庆", "天津", "东莞", "佛山", "中山", "珠海", "厦门", "沈阳", "大连"],
        "min_order_value": 20000,
        "preferred_categories": ["冲饮", "咖啡", "乳制品", "零食", "烘焙", "方便食品"],
        "commission_rate": 0.20,
        "contact_person": "全家FamilyMart商品部（待确认）",
        "rating": 4.5,
        "notes": "日系便利店，擅长打造爆款饮品，有指定进口商品货架"
    },
    {
        "name": "7-11",
        "type": "便利店",
        "city_coverage": ["北京", "天津", "上海", "广州", "深圳", "成都", "重庆", "青岛", "杭州", "南京", "武汉", "西安", "郑州", "长沙", "福州", "厦门", "珠海", "东莞", "沈阳", "大连"],
        "min_order_value": 15000,
        "preferred_categories": ["冲饮", "咖啡", "零食", "乳制品", "烘焙", "方便食品"],
        "commission_rate": 0.20,
        "contact_person": "7-11 中国商品部（待确认）",
        "rating": 4.4,
        "notes": "全球最大便利店品牌，标准化程度高，对标准包装饮品需求大"
    },
    # ─── 电商平台 ───
    {
        "name": "京东自营",
        "type": "电商",
        "city_coverage": ["全国（京东物流可达）"],
        "min_order_value": 100000,
        "preferred_categories": ["冲饮", "咖啡", "乳制品", "进口食品", "有机食品", "方便食品"],
        "commission_rate": 0.25,
        "contact_person": "京东国际采销部（待确认）",
        "rating": 4.7,
        "notes": "自营物流+仓配一体，适合品牌旗舰店或自营采购模式"
    },
    {
        "name": "天猫国际",
        "type": "电商",
        "city_coverage": ["全国"],
        "min_order_value": 80000,
        "preferred_categories": ["进口食品", "冲饮", "咖啡", "美妆", "乳制品", "有机食品"],
        "commission_rate": 0.28,
        "contact_person": "天猫国际 KA 商家运营（待确认）",
        "rating": 4.6,
        "notes": "阿里平台，对进口品牌友好，适合开设海外旗舰店"
    },
    {
        "name": "抖音电商",
        "type": "电商",
        "city_coverage": ["全国"],
        "min_order_value": 30000,
        "preferred_categories": ["冲饮", "零食", "咖啡", "进口食品", "方便食品", "烘焙"],
        "commission_rate": 0.30,
        "contact_person": "抖音电商食品饮料类目（待确认）",
        "rating": 4.5,
        "notes": "兴趣电商+直播带货，适合做短视频种草和达人分销"
    },
    {
        "name": "快手电商",
        "type": "电商",
        "city_coverage": ["全国"],
        "min_order_value": 20000,
        "preferred_categories": ["冲饮", "零食", "方便食品", "咖啡", "烘焙"],
        "commission_rate": 0.28,
        "contact_person": "快手电商食品运营（待确认）",
        "rating": 4.2,
        "notes": "下沉市场渗透率高，适合走量大、性价比高的产品"
    },
    # ─── 社区团购 ───
    {
        "name": "美团优选",
        "type": "社区团购",
        "city_coverage": ["全国（2000+ 市县）"],
        "min_order_value": 10000,
        "preferred_categories": ["冲饮", "乳制品", "方便食品", "零食", "烘焙", "冷冻食品"],
        "commission_rate": 0.12,
        "contact_person": "美团优选食品招商（待确认）",
        "rating": 4.3,
        "notes": "美团旗下社区电商，覆盖极广，适合家庭装大规格产品"
    },
    {
        "name": "朴朴超市",
        "type": "社区团购",
        "city_coverage": ["福州", "厦门", "广州", "深圳", "武汉", "成都", "重庆", "上海", "南京", "杭州"],
        "min_order_value": 15000,
        "preferred_categories": ["冲饮", "乳制品", "咖啡", "零食", "生鲜", "进口食品"],
        "commission_rate": 0.18,
        "contact_person": "朴朴超市采购部（待确认）",
        "rating": 4.4,
        "notes": "前置仓模式，配送时效快，对即时消费饮品需求大"
    },
    {
        "name": "叮咚买菜",
        "type": "社区团购",
        "city_coverage": ["上海", "北京", "深圳", "广州", "杭州", "南京", "苏州", "宁波", "无锡", "常州", "东莞", "佛山", "天津", "嘉兴", "绍兴", "湖州", "南通", "合肥"],
        "min_order_value": 10000,
        "preferred_categories": ["乳制品", "冲饮", "咖啡", "零食", "烘焙", "进口食品"],
        "commission_rate": 0.18,
        "contact_person": "叮咚买菜商品中心（待确认）",
        "rating": 4.3,
        "notes": "生鲜电商，但非生鲜品类也有较好流量，适合搭配场景营销"
    },
    # ─── 私域/团长 ───
    {
        "name": "海拍客",
        "type": "私域",
        "city_coverage": ["全国（母婴店/社群分销）"],
        "min_order_value": 10000,
        "preferred_categories": ["进口食品", "乳制品", "冲饮", "母婴", "有机食品", "零食"],
        "commission_rate": 0.15,
        "contact_person": "海拍客招商部（待确认）",
        "rating": 4.1,
        "notes": "海拍客是进口供应链分销平台，连接线下母婴店和社群"
    },
    # ─── 传统商超 ───
    {
        "name": "永辉超市",
        "type": "企业",
        "city_coverage": ["全国（29省市，超1000家门店）"],
        "min_order_value": 80000,
        "preferred_categories": ["冲饮", "乳制品", "进口食品", "方便食品", "烘焙", "有机食品"],
        "commission_rate": 0.18,
        "contact_person": "永辉超市国际采购（待确认）",
        "rating": 4.2,
        "notes": "全国性大型连锁超市，覆盖广但单品竞争激烈"
    },
    {
        "name": "大润发",
        "type": "企业",
        "city_coverage": ["全国（华东/华北/华南/华中/西南/东北）"],
        "min_order_value": 60000,
        "preferred_categories": ["冲饮", "乳制品", "进口食品", "方便食品", "烘焙", "冷冻食品"],
        "commission_rate": 0.18,
        "contact_person": "大润发采购部（待确认）",
        "rating": 4.1,
        "notes": "阿里旗下商超品牌，线上线下融合（淘鲜达），社区覆盖好"
    },
    {
        "name": "华润万家",
        "type": "企业",
        "city_coverage": ["全国（华东/华南/华北/西北/东北/华中）"],
        "min_order_value": 50000,
        "preferred_categories": ["冲饮", "乳制品", "进口食品", "方便食品", "烘焙", "有机食品"],
        "commission_rate": 0.20,
        "contact_person": "华润万家食品采购（待确认）",
        "rating": 4.0,
        "notes": "大型连锁商超，华润集团旗下，进口资源丰富"
    },
]

# 按类型分类（仅用于展示）
CHANNEL_TYPES = {
    "精品超市": [c for c in CHANNELS if c["type"] == "精品超市"],
    "便利店": [c for c in CHANNELS if c["type"] == "便利店"],
    "电商": [c for c in CHANNELS if c["type"] == "电商"],
    "社区团购": [c for c in CHANNELS if c["type"] == "社区团购"],
    "私域": [c for c in CHANNELS if c["type"] == "私域"],
    "企业": [c for c in CHANNELS if c["type"] == "企业"],
}

# ═══════════════════════════════════════════════════════════════
# 第二部分：匹配算法
# ═══════════════════════════════════════════════════════════════

# 品类相似度映射：扩展品类到相似品类的关系
CATEGORY_SIMILARITY = {
    "冲饮": ["咖啡", "乳制品", "茶饮", "方便食品", "饮料"],
    "咖啡": ["冲饮", "饮料", "茶饮", "烘焙"],
    "乳制品": ["冲饮", "烘焙", "冷冻食品"],
    "进口食品": ["冲饮", "咖啡", "零食", "有机食品"],
    "零食": ["烘焙", "冲饮", "方便食品"],
    "有机食品": ["进口食品", "冲饮", "烘焙"],
}


def category_match_score(product_categories, channel_categories):
    """计算品类匹配度 (0.0 ~ 1.0)
    
    - 直接匹配：1.0
    - 相似品类匹配：0.6
    - 不匹配：0.0
    """
    if not product_categories or not channel_categories:
        return 0.0

    # 标准化为列表
    if isinstance(product_categories, str):
        product_categories = [product_categories]
    if isinstance(channel_categories, str):
        channel_categories = [channel_categories]

    product_cats = [c.strip().lower() for c in product_categories]
    channel_cats = [c.strip().lower() for c in channel_categories]

    best_score = 0.0
    for pc in product_cats:
        for cc in channel_cats:
            if pc == cc:
                best_score = max(best_score, 1.0)
            elif _is_similar_category(pc, cc):
                best_score = max(best_score, 0.6)

    return best_score


def _is_similar_category(cat1, cat2):
    """判断两个品类是否相似"""
    # 扩展相似关系
    similarity_map = {
        "咖啡": {"冲饮", "饮料", "茶饮"},
        "冲饮": {"咖啡", "饮料", "乳制品"},
        "抹茶拿铁": {"咖啡", "冲饮", "饮料"},
        "茶饮": {"冲饮", "咖啡", "饮料"},
        "饮料": {"冲饮", "咖啡", "茶饮"},
        "乳制品": {"冲饮", "烘焙"},
        "进口食品": {"进口食品", "有机食品"},
        "有机食品": {"进口食品"},
        "零食": {"烘焙", "方便食品"},
        "方便食品": {"零食", "冲饮", "烘焙"},
        "烘焙": {"咖啡", "零食", "方便食品"},
        "冷冻食品": {"乳制品", "方便食品"},
    }
    c1 = cat1.lower().strip()
    c2 = cat2.lower().strip()
    if c1 == c2:
        return True
    return c2 in similarity_map.get(c1, set())


def price_match_score(price, channel_type):
    """产品单价（USD）与渠道类型的价格偏好匹配度 (0.0 ~ 1.0)
    
    不同渠道类型对价格敏感度不同：
    - 精品超市：中高端（$2~$8）最佳
    - 便利店：中端（$1~$5）最佳
    - 电商：广泛（$1~$10）
    - 社区团购：低端（$0.5~$4）
    - 私域：中端（$2~$6）
    - 企业：中端（$1~$5）
    """
    price_ranges = {
        "精品超市": (2.0, 8.0),
        "便利店": (1.0, 5.0),
        "电商": (1.0, 10.0),
        "社区团购": (0.5, 4.0),
        "私域": (2.0, 6.0),
        "企业": (1.0, 5.0),
    }
    ideal_low, ideal_high = price_ranges.get(channel_type, (1.0, 5.0))
    if ideal_low <= price <= ideal_high:
        return 1.0
    # 超出但接近：线性衰减
    if price < ideal_low:
        ratio = price / ideal_low
        return max(0.0, ratio)
    # price > ideal_high
    ratio = ideal_high / price
    return max(0.0, ratio)


def moq_match_score(product_moq, channel_min_order, product_price):
    """MOQ 与渠道最低起订量的匹配度 (0.0 ~ 1.0)
    
    计算预估进货额 = MOQ × 单价
    与渠道 min_order_value 对比
    """
    if product_moq <= 0 or product_price <= 0:
        return 0.5  # 无法判断
    estimated_value = product_moq * product_price
    if estimated_value >= channel_min_order:
        return 1.0
    ratio = estimated_value / channel_min_order
    return max(0.0, ratio)


def origin_match_score(origin, features):
    """原产地/特色匹配度 (0.0 ~ 1.0)
    
    基于产品特色（进口、有机、韩系等）的额外加分
    """
    score = 0.5  # 基础分
    origin_lower = (origin or "").lower()
    features_lower = (features or "").lower()
    
    # 进口产品加分
    if "进口" in origin_lower or "进口" in features_lower:
        score += 0.2
    # 有机加分
    if "有机" in features_lower:
        score += 0.1
    # 韩国产品加分（韩流热度）
    if "韩国" in origin_lower or "korea" in origin_lower or "韩" in features_lower:
        score += 0.2
    
    return min(1.0, score)


def channel_preference_score(channel, features):
    """渠道偏好额外匹配度 (0.0 ~ 1.0)
    
    基于渠道 notes 和产品 features 的关键词匹配
    """
    score = 0.5
    text = (channel.get("notes", "") + " " + channel.get("name", "")).lower()
    features_lower = (features or "").lower()

    # 关键词匹配
    keywords = {
        "进口": ["进口", "海外", "foreign", "global"],
        "有机": ["有机", "organic", "自然"],
        "韩": ["韩", "korea", "korean", "日韩"],
        "咖啡": ["咖啡", "coffee", "饮品"],
        "年轻": ["z世代", "年轻", "潮流", "高颜值"],
        "下沉": ["下沉", "性价比"],
    }
    for category, words in keywords.items():
        for w in words:
            if w in features_lower and w in text:
                score += 0.08
                break

    return min(1.0, score)


def compute_match(product, channel, verbose=False):
    """计算产品与渠道的综合匹配度
    
    返回字典：{channel, score, reason, suggestion}
    """
    # 1. 品类匹配 (权重 0.35)
    cat_score = category_match_score(
        product.get("category", ""),
        channel["preferred_categories"]
    )

    # 2. 价格区间匹配 (权重 0.25)
    price = product.get("price", 3.5)
    p_score = price_match_score(price, channel["type"])

    # 3. MOQ/起订量匹配 (权重 0.15)
    m_score = moq_match_score(
        product.get("moq", 500),
        channel["min_order_value"],
        price
    )

    # 4. 地域覆盖匹配 (权重 0.10)
    coverage = channel["city_coverage"]
    target_regions = product.get("target_regions", [])
    geo_score = 0.5
    if target_regions:
        match_count = 0
        for region in target_regions:
            for city in coverage:
                if region.lower() in city.lower() or city.lower() in region.lower():
                    match_count += 1
                    break
        geo_score = min(1.0, match_count / len(target_regions) * 1.5)

    # 5. 原产地/特色匹配 (权重 0.10)
    o_score = origin_match_score(product.get("origin", ""), product.get("features", ""))

    # 6. 渠道偏好匹配 (权重 0.05)
    cp_score = channel_preference_score(channel, product.get("features", ""))

    # 综合评分
    total_score = (
        cat_score * 0.35 +
        p_score * 0.25 +
        m_score * 0.15 +
        geo_score * 0.10 +
        o_score * 0.10 +
        cp_score * 0.05
    )

    # 生成匹配理由
    reasons = []
    if cat_score >= 1.0:
        reasons.append("品类高度匹配")
    elif cat_score >= 0.6:
        reasons.append("品类部分匹配")
    else:
        reasons.append("品类匹配度较低")

    if p_score >= 1.0:
        reasons.append("价格区间合适")
    elif p_score >= 0.6:
        reasons.append("价格区间基本合适")
    else:
        reasons.append("价格区间需协商")

    if m_score >= 1.0:
        reasons.append("起订量满足要求")
    elif m_score >= 0.6:
        reasons.append("起订量基本达标")
    else:
        reasons.append("起订量可能偏低")

    if o_score > 0.7:
        reasons.append("进口/韩系产品有额外优势")

    # 建议合作方式
    suggestions = _generate_suggestion(channel, total_score, product)

    return {
        "channel": channel["name"],
        "type": channel["type"],
        "score": round(total_score * 100, 1),
        "match_detail": {
            "品类匹配": round(cat_score, 2),
            "价格区间": round(p_score, 2),
            "起订量匹配": round(m_score, 2),
            "地域覆盖": round(geo_score, 2),
            "原产地特色": round(o_score, 2),
            "渠道偏好": round(cp_score, 2),
        },
        "reason": "；".join(reasons),
        "suggestion": suggestions,
        "commission_rate": channel["commission_rate"],
        "min_order_value": channel["min_order_value"],
        "rating": channel["rating"],
        "contact": channel["contact_person"],
    }


def _generate_suggestion(channel, score, product):
    """根据匹配度生成合作建议"""
    if score >= 0.85:
        return f"强烈推荐入驻 {channel['name']}。品类匹配度高，建议直接联系{channel['contact_person']}，准备样品和报价单推进合作。"
    elif score >= 0.7:
        return f"推荐尝试 {channel['name']}。可先以试销小批量（{product.get('moq', 500)}盒以内）进入，验证市场反应后扩大合作。"
    elif score >= 0.5:
        return f"可探索合作 {channel['name']}。建议提供定制化方案（规格/包装调整）以提高匹配度。"
    else:
        return f"匹配度一般，暂不优先推荐 {channel['name']}。可考虑在其他渠道验证产品力后再进入。"


# ═══════════════════════════════════════════════════════════════
# 第三部分：内置默认产品 — 抹茶拿铁
# ═══════════════════════════════════════════════════════════════

DEFAULT_PRODUCT = {
    "name": "CAFE MORI JARDIN 抹茶拿铁（6口味）",
    "category": ["冲饮", "咖啡", "进口食品"],
    "price": 3.50,  # USD FOB 单价
    "moq": 500,     # 首单最小起订量
    "origin": "韩国（首尔）",
    "features": "韩国原装进口、济州岛有机抹茶、6种口味、韩国优质乳粉、月销50,000盒韩国本土验证",
    "target_regions": ["上海", "广州", "深圳", "北京", "杭州", "成都"],
    "spec": "15g/条 × 10条/盒",
    "hs_code": "2101.20",
}


# ═══════════════════════════════════════════════════════════════
# 第四部分：匹配引擎入口
# ═══════════════════════════════════════════════════════════════

def match_channels(product=None, top_n=None):
    """主匹配函数
    
    参数：
        product: 产品信息字典，为 None 时使用默认抹茶拿铁
        top_n: 返回前 N 个结果，None 则返回全部
    
    返回：按匹配度降序排列的渠道列表
    """
    if product is None:
        product = DEFAULT_PRODUCT

    results = []
    for channel in CHANNELS:
        result = compute_match(product, channel)
        results.append(result)

    # 按匹配度降序
    results.sort(key=lambda x: x["score"], reverse=True)

    if top_n and top_n > 0:
        results = results[:top_n]

    return results


def list_channels(channel_type=None):
    """列出所有渠道（可选按类型过滤）"""
    if channel_type:
        channels = CHANNEL_TYPES.get(channel_type, [])
    else:
        channels = CHANNELS
    
    result = []
    for ch in channels:
        result.append({
            "name": ch["name"],
            "type": ch["type"],
            "city_count": len(ch["city_coverage"]),
            "min_order_value": ch["min_order_value"],
            "preferred_categories": ch["preferred_categories"],
            "commission_rate": ch["commission_rate"],
            "rating": ch["rating"],
            "contact": ch["contact_person"],
        })
    return result


def format_text_output(results, show_detail=True):
    """格式化为终端文本输出"""
    lines = []
    lines.append("=" * 72)
    lines.append("  中韩贸易网关 — 渠道AI匹配引擎  v1.0")
    lines.append("=" * 72)
    lines.append("")
    
    if not results:
        lines.append("  暂无匹配结果。")
        return "\n".join(lines)

    lines.append(f"  共匹配 {len(results)} 个渠道\n")
    
    for i, r in enumerate(results, 1):
        score = r["score"]
        bar = _score_bar(score)
        rank_tag = "★" if score >= 85 else "◆" if score >= 70 else "▸" if score >= 50 else " "
        
        lines.append(f"  {rank_tag} #{i}  {r['channel']}")
        lines.append(f"     类型: {r['type']}")
        lines.append(f"     匹配度: {score:.1f}%  {bar}")
        lines.append(f"     评分: {r['rating']}/5.0  |  佣金: {r['commission_rate']*100:.0f}%  |  起订: ¥{r['min_order_value']:,}")
        
        if show_detail and "match_detail" in r:
            detail = r["match_detail"]
            cats = "  ".join([f"{k}:{v:.2f}" for k, v in detail.items()])
            lines.append(f"     维度: {cats}")
        
        lines.append(f"     理由: {r['reason']}")
        lines.append(f"     建议: {r['suggestion']}")
        lines.append(f"     联系: {r['contact']}")
        lines.append("  " + "-" * 68)
    
    return "\n".join(lines)


def _score_bar(score):
    """生成简单的分数条"""
    filled = int(score / 10)
    filled = max(0, min(10, filled))
    bar = "█" * filled + "░" * (10 - filled)
    return bar


# ═══════════════════════════════════════════════════════════════
# 第五部分：CLI 入口
# ═══════════════════════════════════════════════════════════════

def print_help():
    """打印帮助信息"""
    help_text = """
中韩贸易网关 — 渠道AI匹配引擎  v1.0

用法:
    python3 tools/channel_matcher.py latte             匹配抹茶拿铁的最佳渠道
    python3 tools/channel_matcher.py latte --top 5     只看 Top 5
    python3 tools/channel_matcher.py --list-channels   列出所有渠道
    python3 tools/channel_matcher.py --list-types      按类型分组列出渠道
    python3 tools/channel_matcher.py latte --format json  JSON 格式输出
    python3 tools/channel_matcher.py latte --top 5 --format json  Top 5 JSON
    python3 tools/channel_matcher.py --help            显示此帮助

内置默认产品: CAFE MORI JARDIN 抹茶拿铁（6口味）
    - 品类: 冲饮/咖啡/进口食品
    - FOB 单价: $3.50 USD/盒
    - MOQ: 500盒（首单）
    - 原产地: 韩国（首尔）
    - 特色: 韩国原装进口、济州岛有机抹茶、6种口味

渠道数据库: 共 %d 个渠道（精品超市/便利店/电商/社区团购/私域/企业）
    """ % len(CHANNELS)
    print(help_text.strip())


def main():
    """CLI 主入口"""
    args = sys.argv[1:]
    
    # 解析参数
    product_name = None
    top_n = None
    output_format = "text"
    list_mode = False
    list_types = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--help" or arg == "-h":
            print_help()
            return
        elif arg == "--list-channels":
            list_mode = True
        elif arg == "--list-types":
            list_types = True
        elif arg == "--top" or arg == "-n":
            i += 1
            if i < len(args):
                top_n = int(args[i])
        elif arg == "--format" or arg == "-f":
            i += 1
            if i < len(args):
                output_format = args[i]
        elif arg.startswith("--"):
            print(f"未知参数: {arg}")
            print("使用 --help 查看帮助")
            return
        else:
            product_name = arg
        i += 1

    # --list-channels 模式
    if list_mode:
        channels = list_channels()
        print(f"\n  渠道数据库共 {len(channels)} 个渠道：\n")
        print(f"  {'序号':<4} {'名称':<18} {'类型':<10} {'城市覆盖':<30} {'起订额':<10} {'佣金':<8} {'评分':<6}")
        print("  " + "-" * 96)
        for idx, ch in enumerate(channels, 1):
            city_str = str(ch["city_count"]) + " 城市" if ch["city_count"] <= 50 else "全国"
            print(f"  {idx:<4} {ch['name']:<18} {ch['type']:<10} {city_str:<30} ¥{ch['min_order_value']:<8,} {ch['commission_rate']*100:<7.0f}% {ch['rating']:<5.1f}")
        print()
        return

    # --list-types 模式
    if list_types:
        print(f"\n  按类型分组（共 {len(CHANNELS)} 个渠道）：\n")
        for t_name, t_channels in CHANNEL_TYPES.items():
            print(f"  📦 {t_name} ({len(t_channels)} 个)")
            for c in t_channels:
                print(f"     - {c['name']}  (评分 {c['rating']}/5.0)")
            print()
        return

    # 匹配模式
    product = None
    if product_name and product_name.lower() in ("latte", "matcha", "抹茶拿铁"):
        product = DEFAULT_PRODUCT
    elif product_name:
        # 支持自定义产品（简单 JSON 字符串）
        try:
            product = json.loads(product_name)
        except json.JSONDecodeError:
            print(f"未知产品: {product_name}")
            print("使用默认抹茶拿铁数据进行匹配。\n")
            product = DEFAULT_PRODUCT
    else:
        product = DEFAULT_PRODUCT

    # 执行匹配
    results = match_channels(product=product, top_n=top_n)

    if output_format == "json":
        output = {
            "product": {
                "name": product.get("name", ""),
                "category": product.get("category", ""),
                "price": product.get("price", 0),
                "moq": product.get("moq", 0),
                "origin": product.get("origin", ""),
            },
            "total_channels": len(results),
            "top_n": top_n,
            "results": results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 文本输出
        header = f"\n  产品: {product.get('name', '未知')}"
        if "category" in product:
            header += f"  |  品类: {product['category']}"
        if "price" in product:
            header += f"  |  FOB: ${product['price']}/盒"
        if "moq" in product:
            header += f"  |  MOQ: {product['moq']}盒"
        if "origin" in product:
            header += f"  |  产地: {product['origin']}"
        print(header)
        print(format_text_output(results))
        print(f"  * 匹配完成于 {len(results)} 个渠道 | 使用 --help 查看帮助\n")


if __name__ == "__main__":
    main()
