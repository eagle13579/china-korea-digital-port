#!/usr/bin/env python3
"""
AI 营销素材生成器 — AI Marketing Generator
=============================================
为中韩出海数智港产品自动生成多平台中文营销文案。

支持平台：
  - xiaohongshu   小红书笔记
  - wechat        微信公众号文章
  - moments       微信朋友圈文案
  - douyin        抖音短视频脚本

CLI 用法：
  python3 tools/ai_marketing_generator.py latte --platform all
  python3 tools/ai_marketing_generator.py latte --platform xiaohongshu
  python3 tools/ai_marketing_generator.py --new-product
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProductInfo:
    """产品信息"""
    name: str                    # 产品名称
    brand: str                   # 品牌名
    origin: str                  # 产地/来源国
    features: List[str]          # 卖点列表
    price: str                   # 价格区间
    target_audience: str         # 目标人群描述
    category: str = ""           # 产品品类
    package: str = ""            # 包装规格
    tasting_notes: str = ""      # 品鉴描述


# ═══════════════════════════════════════════════════════════════
# 内置演示数据 — 抹茶拿铁（CAFE MORI / JARDIN 品牌）
# ═══════════════════════════════════════════════════════════════

DEMO_PRODUCTS = {
    "latte": ProductInfo(
        name="抹茶拿铁（6口味装）",
        brand="CAFE MORI / JARDIN",
        origin="韩国",
        features=[
            "济州岛有机抹茶粉，100%国产抹茶",
            "6种口味：经典抹茶、炼乳、黑糖、燕麦、椰奶、香草",
            "0反式脂肪酸，每杯仅45kcal",
            "冷热双泡，3秒速溶",
            "独立条装便携设计，随身携带",
            "韩国FDA认证，HACCP食品安全认证",
        ],
        price="¥69.9/盒（6条装）",
        target_audience="20-35岁都市女性、上班族、学生党、抹茶爱好者、健康生活方式追求者",
        category="速溶饮品/健康茶饮",
        package="12g×6条/盒",
        tasting_notes="入口丝滑，抹茶清香混合奶香，甜度适中不腻，余韵清爽回甘",
    ),
    "matcha": ProductInfo(
        name="济州抹茶粉（精品装）",
        brand="JARDIN",
        origin="韩国济州岛",
        features=[
            "济州岛有机茶园种植",
            "石磨研磨，超微粉达1000目",
            "色泽翠绿，香气浓郁",
            "无添加、无农残",
            "适合点茶、烘焙、拿铁",
        ],
        price="¥128/罐（80g）",
        target_audience="抹茶爱好者、茶道爱好者、精品咖啡店、烘焙达人",
        category="精品抹茶粉",
        package="80g/罐",
        tasting_notes="鲜绿明亮，海苔香与甜感平衡，泡沫细腻持久",
    ),
}


# ═══════════════════════════════════════════════════════════════
# 模板库 — 每个平台 5 个版本
# ═══════════════════════════════════════════════════════════════

# ── 小红书笔记模板 ──────────────────────────────────────────────

XIAOHONGSHU_TEMPLATES = [
    {
        "style": "种草安利型",
        "title": "韩国代购都抢疯了🔥这杯抹茶拿铁我能喝一辈子！",
        "content_template": (
            "姐妹们！！我终于找到了最好喝的抹茶拿铁！\n\n"
            "是韩国欧尼安利给我的CAFE MORI抹茶拿铁。\n"
            "济州岛有机抹茶粉做基底，一盒6种口味喝一周不重样。\n\n"
            "🍵 【经典抹茶】— 最纯正的味道，抹茶控闭眼冲\n"
            "🥛 【炼乳抹茶】— 甜而不腻，奶香爆炸\n"
            "🖤 【黑糖抹茶】— 焦糖香+抹茶香，绝配\n"
            "🌾 【燕麦抹茶】— 植物奶党狂喜\n"
            "🥥 【椰奶抹茶】— 一秒穿越到东南亚\n"
            "🌿 【香草抹茶】— 清新高级感\n\n"
            "✨ 0反式脂肪酸，一杯才45kcal，减脂期也能喝！\n"
            "冷热水都能泡，3秒搞定，懒人福音。\n\n"
            "每天一杯，幸福感拉满。冲它！！\n"
        ),
        "hashtags": [
            "#抹茶拿铁", "#韩国零食", "#CAFEMORI",
            "#我的私藏美食", "#减脂饮品", "#上班族必备",
            "#抹茶控", "#好物分享", "#小红书爆款美食"
        ],
        "suggested_images": [
            "六口味全家福摆拍（俯拍）",
            "冲泡过程动图（热水倒入杯中3秒溶解）",
            "拿铁+阳光+绿植的ins风场景图",
            "六种口味一字排开+手写标签",
        ],
    },
    {
        "style": "反差/真香型",
        "title": "🇰🇷我开始也以为是智商税…结果真香了🥹",
        "content_template": (
            "说实话，刚开始朋友给我推荐这款韩国抹茶拿铁的时候\n"
            "我心想：不就是个速溶嘛能有多好喝？\n\n"
            "结果喝了一口直接打脸。。。\n\n"
            "CAFE MORI这个牌子在韩国便利店就很火\n"
            "用的是济州岛有机抹茶，不是那种廉价粉\n"
            "一盒6种口味，每个都很好喝没有雷\n\n"
            "我最爱的是炼乳味和黑糖味\n"
            "甜度刚好不腻，抹茶味超浓\n"
            "泡牛奶比泡水好喝100倍！！\n\n"
            "下午茶时间来一杯，比奶茶健康多了\n"
            "热量才45kcal，奶茶一杯顶这个6杯。\n\n"
            "我已经回购3盒了…真的值得试试。\n"
        ),
        "hashtags": [
            "#真香警告", "#韩国抹茶拿铁", "#回购无数遍",
            "#下午茶时光", "#低卡饮品", "#美食测评",
            "#CAFEMORI", "#济州岛抹茶"
        ],
        "suggested_images": [
            "手拿产品+惊讶表情（前/后对比）",
            "产品配料表特写（展示0反式脂肪酸）",
            "泡好的抹茶拿铁+电脑/书本的办公桌场景",
            "已购买的多盒产品堆叠（暗示回购）",
        ],
    },
    {
        "style": "干货科普型",
        "title": "抹茶拿铁怎么挑？韩国人在喝的6款测评✨",
        "content_template": (
            "作为一个喝了5年抹茶拿铁的资深抹茶控。。\n"
            "今天来给大家扒一扒CAFE MORI的6口味到底值不值得入。\n\n"
            "⭐️ 品牌背景\n"
            "CAFE MORI是韩国国民咖啡品牌JARDIN旗下的即饮产品线\n"
            "所有抹茶原料来自济州岛有机茶园\n"
            "通过HACCP食品安全认证 + 韩国FDA认证。\n\n"
            "⭐️ 6口味测评（个人向）\n"
            "•• 经典抹茶→ 8/10，纯正抹茶味，入门首选\n"
            "•• 炼乳抹茶→ 9/10，奶香浓郁，我的最爱\n"
            "•• 黑糖抹茶→ 8.5/10，焦糖控必入\n"
            "•• 燕麦抹茶→ 7.5/10，乳糖不耐友好\n"
            "•• 椰奶抹茶→ 8/10，夏天喝清爽\n"
            "•• 香草抹茶→ 8.5/10，高级感满满\n\n"
            "⭐️ 性价比\n"
            "¥69.9/盒 = 6杯 = 一杯才¥11.6\n"
            "比奶茶店20+一杯的抹茶拿铁划算太多了！\n"
        ),
        "hashtags": [
            "#抹茶测评", "#韩国必买", "#美食评测",
            "#抹茶拿铁测评", "#济州岛", "#性价比好物",
            "#CAFEMORI抹茶拿铁", "#口味测评"
        ],
        "suggested_images": [
            "六种口味分别展示（每支产品+对应主角原料）",
            "测评表格图（口味/甜度/推荐指数）",
            "营养成分表解读图",
            "产品认证/标识特写",
        ],
    },
    {
        "style": "场景代入型",
        "title": "打工人的早C晚M☕️早上咖啡下午抹茶拿铁yyds",
        "content_template": (
            "当代打工人续命法则：\n"
            "☀️ 早上：冰美式清醒\n"
            "🌙 下午：抹茶拿铁抚慰\n\n"
            "最近入手了这款韩国CAFE MORI抹茶拿铁\n"
            "我的下午茶已经彻底被它承包了。\n\n"
            "办公室里备一盒，3秒冲泡搞定\n"
            "再也不用排队等外卖了。\n\n"
            "同事都问我每天下午喝的是什么这么香\n"
            "结果一个下午就被借走了3条…\n\n"
            "好在它有6种口味，借出去也不心疼\n"
            "最爱的留给自己！嘿嘿。\n\n"
            "强烈建议上班族、学生党人手一盒\n"
            "比奶茶便宜、比咖啡温柔、比白水好喝。\n"
        ),
        "hashtags": [
            "#打工人的下午茶", "#办公室好物", "#懒人饮品",
            "#早C晚M", "#抹茶拿铁", "#下午茶必备",
            "#职场好物分享", "#CAFEMORI"
        ],
        "suggested_images": [
            "办公桌俯拍（电脑+抹茶拿铁+绿植）",
            "手拿杯子+窗边阳光逆光拍摄",
            "产品条装在办公桌抽屉里的场景",
            "和同事分享/互动的场景图",
        ],
    },
    {
        "style": "颜值/视觉型",
        "title": "这个绿太好看了🟢韩国抹茶拿铁也太会了吧",
        "content_template": (
            "不是吧不是吧。。\n"
            "这杯抹茶拿铁的颜色也太治愈了吧🟢\n\n"
            "来自韩国的CAFE MORI抹茶拿铁\n"
            "用济州岛有机抹茶粉，泡出来是那种\n"
            "高级的抹茶绿✨ 完全不是人工色素那种\n\n"
            "倒进透明杯子里 配点冰块\n"
            "颜值直接拉满 拍100张不嫌多📸\n\n"
            "一盒6种口味 每个颜色搭配都好美\n"
            "经典抹茶→ 翠绿\n"
            "炼乳抹茶→ 奶绿\n"
            "黑糖抹茶→ 焦糖绿（这个分层绝了）\n"
            "燕麦抹茶→ 米绿\n"
            "椰奶抹茶→ 浅绿\n"
            "香草抹茶→ 奶油绿\n\n"
            "每杯都是艺术品。 收藏家模式已启动。\n"
        ),
        "hashtags": [
            "#高颜值饮品", "#抹茶绿", "#治愈系美食",
            "#随手拍美食", "#ins风", "#抹茶拿铁",
            "#韩国美食", "#CAFEMORI", "#拍照打卡"
        ],
        "suggested_images": [
            "透明玻璃杯中抹茶拿铁的分层效果",
            "六种口味颜色渐变排列",
            "抹茶拿铁+鲜花/阳光的ins风大片",
            "手持产品+抹茶绿的穿搭呼应",
        ],
    },
]


# ── 微信公众号文章模板 ──────────────────────────────────────────

WECHAT_TEMPLATES = [
    {
        "style": "品牌故事型",
        "title": "从济州岛到你的茶杯：这款韩国抹茶拿铁，藏着海风和阳光的味道",
        "content_template": (
            "济州岛的冬天，雨水充沛，茶树在火山岩土壤里静静生长。\n\n"
            "第二年春天，嫩芽被手工采摘，经过蒸汽杀青、石磨研磨，\n"
            "成为1000目以上的超微抹茶粉。\n\n"
            "CAFE MORI的研发团队花了8个月，才找到「抹茶+奶+甜」的黄金三角比例——\n"
            "既要保留抹茶原本的鲜香，又要让不习惯抹茶苦涩的人也能爱上它。\n\n"
            "于是有了这盒6口味装。\n\n"
            "---\n\n"
            "▍经典抹茶 — 向传统致敬\n"
            "没有多余的修饰，就是最好的抹茶该有的味道。\n"
            "海苔香、鲜甜感、回甘——一个不少。\n\n"
            "▍炼乳抹茶 — 温柔一击\n"
            "炼乳的甜厚包裹着抹茶的清冽，\n"
            "像是济州岛的春天海风，温柔又清爽。\n\n"
            "▍黑糖抹茶 — 深度诱惑\n"
            "冲绳黑糖的焦香撞上韩国抹茶的清鲜，\n"
            "是东西方风味的完美联姻。\n\n"
            "▍燕麦抹茶 — 植物革命\n"
            "专为乳糖不耐和植物基爱好者打造，\n"
            "燕麦的谷物香和抹茶意外地搭。\n\n"
            "▍椰奶抹茶 — 热带风情\n"
            "椰奶的浓郁遇上抹茶的清新，\n"
            "喝一口仿佛到了东南亚的海边。\n\n"
            "▍香草抹茶 — 经典升级\n"
            "马达加斯加香草籽的加入，\n"
            "让抹茶的层次感直接提升一个档次。\n\n"
            "---\n\n"
            "一杯45kcal，0反式脂肪酸。\n"
            "冷热双泡，3秒即溶。\n\n"
            "这是济州岛想对你说的话：\n"
            "「忙了一天，是时候停下来，喝杯好的。」\n"
        ),
        "hashtags": [
            "#济州岛抹茶", "#CAFEMORI", "#韩国美食",
            "#抹茶拿铁", "#品牌故事", "#慢生活"
        ],
        "suggested_images": [
            "济州岛茶园航拍图（或素材图）",
            "产品6口味全家福素雅摆拍",
            "每个口味的单独特写+原料搭配",
            "冲泡步骤分解图",
            "手持茶杯+生活场景的温暖照片",
        ],
    },
    {
        "style": "种草清单型",
        "title": "2026春季必买清单✔️韩国带回来的抹茶拿铁我不允许你没喝过",
        "content_template": (
            "每年春天，我们的选品团队都会去韩国跑一圈。\n\n"
            "今年的惊喜来自CAFE MORI。\n\n"
            "这个品牌在韩国本土非常能打——\n"
            "母公司JARDIN是韩国三大咖啡品牌之一，\n"
            "所有抹茶来自济州岛有机茶园。\n\n"
            "---\n\n"
            "【为什么它值得进入你的必买清单？】\n\n"
            "✅ 原料硬核\n"
            "济州岛有机抹茶，不是普通绿茶粉冒充的。\n"
            "1000目石磨研磨，色泽翠绿，香气纯正。\n\n"
            "✅ 无需冲泡技巧\n"
            "热水或冷水直接冲泡，3秒完全溶解。\n"
            "不会结块，不会沉淀——这一点秒杀市面90%的同类产品。\n\n"
            "✅ 健康无负担\n"
            "0反式脂肪酸，每杯仅45kcal。\n"
            "减脂期可以放心喝，抹茶本身富含茶多酚和叶绿素。\n\n"
            "✅ 口味丰富不踩雷\n"
            "6种口味，总有一款是你的菜。\n"
            "据我们测试，99%的人能找到至少2个真爱口味。\n\n"
            "---\n\n"
            "价格：¥69.9/盒（6条装）\n"
            "相当于一杯不到¥12\n"
            "比奶茶店便宜一半，品质翻倍。\n\n"
            "👉 点击下方小程序立即购买\n"
        ),
        "hashtags": [
            "#必买清单", "#韩国零食推荐", "#春季限定",
            "#CAFEMORI", "#抹茶控必入", "#好物推荐"
        ],
        "suggested_images": [
            "首图：产品+花/春季元素的氛围图",
            "配料表特写+认证标识图",
            "同价格带对比图（vs奶茶店）",
            "6口味排列+口味标签图",
            "用户好评/返图合集",
        ],
    },
    {
        "style": "知识科普型",
        "title": "抹茶和绿茶粉的区别？韩国人喝抹茶的100种方式",
        "content_template": (
            "很多人以为「抹茶=绿茶粉」。\n\n"
            "不，它们不是一回事。\n\n"
            "---\n\n"
            "【抹茶 vs 绿茶粉】\n\n"
            "抹茶：\n"
            "- 采摘前覆盖遮光20-30天，增加叶绿素和氨基酸\n"
            "- 只取嫩叶，蒸汽杀青\n"
            "- 石磨低温研磨成超微粉（1000目以上）\n"
            "- 颜色鲜绿，能打出细腻泡沫\n\n"
            "绿茶粉：\n"
            "- 普通绿茶直接磨粉\n"
            "- 颜色偏黄绿或褐绿\n"
            "- 口感苦涩，不易溶解\n\n"
            "CAFE MORI用的就是100%真正的抹茶粉。\n\n"
            "---\n\n"
            "【韩国人的100种喝法】\n\n"
            "1⃣ 经典喝法：热水+抹茶粉，直接冲泡\n"
            "2⃣ 冰拿铁：冷水+冰块+抹茶粉，摇匀\n"
            "3⃣ 抹茶牛奶：热牛奶+抹茶粉，咖啡店同款\n"
            "4⃣ 抹茶酸奶：抹茶粉+希腊酸奶，早餐吃\n"
            "5⃣ 抹茶燕麦碗：燕麦+抹茶粉+水果\n"
            "6⃣ 抹茶冰激凌：抹茶粉+奶油冷冻\n\n"
            "一盒CAFE MORI，解锁100种快乐。\n"
        ),
        "hashtags": [
            "#抹茶知识", "#抹茶和绿茶的区别", "#韩国抹茶文化",
            "#CAFEMORI", "#冷知识", "#DIY饮品"
        ],
        "suggested_images": [
            "抹茶粉vs绿茶粉对比图（颜色/质地）",
            "抹茶制作工艺流程图",
            "抹茶的100种喝法拼图",
            "CAFE MORI产品+DIY场景展示",
        ],
    },
    {
        "style": "限时活动型",
        "title": "⭐限时福利⭐韩国爆款抹茶拿铁尝鲜价¥49.9，手慢无！",
        "content_template": (
            "各位抹茶控注意了⚠️\n\n"
            "中韩出海数智港首单福利来了！\n\n"
            "---\n\n"
            "CAFE MORI 抹茶拿铁6口味装\n"
            "❌ 限时尝鲜价：¥49.9/盒（原价69.9）\n"
            "❌ 买2盒再减10元\n"
            "❌ 前100名下单送定制抹茶杯\n\n"
            "---\n\n"
            "为什么现在入手？\n\n"
            "① 全网首发价\n"
            "韩国的爆款刚到国内，我们是第一批拿到货的。\n"
            "等铺货之后就是全网统一价了。\n\n"
            "② 尝鲜不踩雷\n"
            "6种口味一盒搞定，总有一款你喜欢。\n"
            "不喜欢？7天无理由退。\n\n"
            "③ 限量周边\n"
            "抹茶杯是韩国设计师联名款，错过不再有。\n\n"
            "---\n\n"
            "⏰ 活动时间：即日起至本月底\n"
            "📦 48小时内发货 | 全国包邮\n\n"
            "👇 点击下方小程序抢购\n"
        ),
        "hashtags": [
            "#限时活动", "#新品首发", "#韩国抹茶拿铁",
            "#CAFEMORI", "#首单福利", "#手慢无"
        ],
        "suggested_images": [
            "首图：大促风格主视觉（价格突出）",
            "产品+赠品（定制杯）展示",
            "购买二维码/小程序码图",
            "限时倒计时+库存数字的动态效果图",
            "产品+优惠信息长图",
        ],
    },
    {
        "style": "跨界联名型",
        "title": "韩国CAFE MORI x 中韩出海数智港 | 这杯抹茶拿铁是我们的第一个孩子",
        "content_template": (
            "2026年春天，我们做了一个大胆的决定。\n\n"
            "不做平台，不做软件，\n"
            "先卖一盒抹茶拿铁试试看。\n\n"
            "---\n\n"
            "【为什么是抹茶拿铁？】\n\n"
            "因为它是中韩两国年轻人都在喝的东西。\n"
            "因为它的供应链足够简单——韩国生产，中国消费者。\n"
            "因为它足够好。\n\n"
            "我们让韩国的选品伙伴浩然在首尔跑了10家供应商，\n"
            "盲测了30多款产品，\n"
            "最后选定了CAFE MORI的这盒6口味装。\n\n"
            "---\n\n"
            "【关于CAFE MORI】\n"
            "韩国国民咖啡品牌JARDIN旗下\n"
            "济州岛有机抹茶\n"
            "HACCP + 韩国FDA双重认证\n\n"
            "---\n\n"
            "【关于数智港】\n"
            "我们不是跨境电商。\n"
            "我们是AI驱动的中韩贸易网关。\n"
            "帮韩国好产品找中国渠道，帮中国企业找韩国好产品。\n\n"
            "这盒抹茶拿铁，就是我们的起点。\n\n"
            "希望你喝到的每一口，都能感受到济州岛的海风和我们的诚意。\n"
        ),
        "hashtags": [
            "#中韩出海数智港", "#CAFEMORI", "#联名",
            "#抹茶拿铁", "#中韩贸易", "#品牌故事"
        ],
        "suggested_images": [
            "双品牌logo联名主视觉",
            "济州岛风景+产品融合图",
            "团队选品/测试花絮图",
            "产品使用场景+数智港品牌元素",
            "从韩国到中国的旅程示意图",
        ],
    },
]


# ── 朋友圈文案模板 ──────────────────────────────────────────────

MOMENTS_TEMPLATES = [
    {
        "style": "安利种草型",
        "content_template": (
            "被韩国同事种草的这个抹茶拿铁，一盒6种口味，\n"
            "每一款都好喝到想囤一箱😭\n\n"
            "济州岛有机抹茶做的，0反式脂肪酸，\n"
            "一杯才45大卡，比奶茶健康太多了✨\n\n"
            "冷热水都能泡，3秒搞定，懒人必备🔥\n\n"
            "链接放评论区了，自取👇"
        ),
        "hashtags": ["#抹茶拿铁", "#韩国零食", "#减脂也能喝", "#CAFEMORI"],
        "suggested_images": [
            "产品六口味摆拍",
            "泡好的抹茶拿铁在手中",
            "配料表/热量标注特写",
        ],
    },
    {
        "style": "日常分享型",
        "content_template": (
            "下午三点的续命水☕️\n"
            "今天喝的是黑糖抹茶味❤️\n\n"
            "韩国的CAFE MORI，一盒6个味道天天换着喝\n"
            "喜欢抹茶的姐妹可以冲👌"
        ),
        "hashtags": ["#下午茶", "#抹茶拿铁", "#日常"],
        "suggested_images": [
            "泡好的抹茶拿铁+窗外风景",
            "产品条装+今天的口味标签",
        ],
    },
    {
        "style": "福利分享型",
        "content_template": (
            "🎁帮大家薅到了韩国抹茶拿铁的羊毛！\n\n"
            "原价69.9的CAFE MORI六口味装\n"
            "现在只要49.9！！！\n\n"
            "济州岛有机抹茶，0反式脂肪酸\n"
            "一杯不到12块，比奶茶划算太多了。\n\n"
            "限时活动，我直接囤了3盒🤫\n"
            "评论区取链接👇"
        ),
        "hashtags": ["#薅羊毛", "#限时优惠", "#抹茶拿铁", "#CAFEMORI"],
        "suggested_images": [
            "价格对比图（vs奶茶）",
            "产品+优惠券/折扣信息图",
            "多盒囤货展示",
        ],
    },
    {
        "style": "测评推荐型",
        "content_template": (
            "CAFE MORI抹茶拿铁6口味真实测评🍵\n\n"
            "❤️ 炼乳味 > 我的top1，奶香爆炸\n"
            "❤️ 黑糖味 > 焦糖香太绝了\n"
            "❤️ 经典抹茶 > 纯正抹茶味\n"
            "❤️ 香草味 > 高级感，适合下午茶\n"
            "❤️ 椰奶味 > 清爽夏天的感觉\n"
            "❤️ 燕麦味 > 植物奶爱好者冲\n\n"
            "没有踩雷的，可以闭眼入✨"
        ),
        "hashtags": ["#美食测评", "#抹茶拿铁", "#韩国零食", "#真实评价"],
        "suggested_images": [
            "六口味一字排开+手写评分标签",
            "每个口味的特写拼图",
        ],
    },
    {
        "style": "情感共鸣型",
        "content_template": (
            "长大之后才发现，\n"
            "能让自己开心的都是小事。\n\n"
            "比如下午三点的办公室，\n"
            "泡一杯抹茶拿铁，\n"
            "看着窗外的阳光发五分钟呆。\n\n"
            "用的是韩国朋友送的CAFE MORI\n"
            "一盒6种口味，每天都有小惊喜🍵\n\n"
            "生活嘛，不就是这样被一杯杯好喝的填满的。"
        ),
        "hashtags": ["#生活需要仪式感", "#下午茶时光", "#抹茶拿铁", "#治愈系"],
        "suggested_images": [
            "手握抹茶拿铁+阳光逆光氛围图",
            "产品+手写卡片/花的温馨场景",
        ],
    },
]


# ── 抖音短视频脚本模板 ──────────────────────────────────────────

DOUYIN_TEMPLATES = [
    {
        "style": "开箱测评型",
        "title": "韩国便利店爆款抹茶拿铁6口味开箱！到底哪个最好喝？",
        "content_template": (
            "【0-3秒 引人】\n"
            "（快速剪辑/快节奏背景音乐）\n"
            "画外音：韩国便利店卖断货的抹茶拿铁，我给你们搞来了！\n"
            "动作：拆开快递包装，拿出产品盒\n\n"
            "【3-10秒 展示】\n"
            "特写产品包装，打开盒子，6条口味一字排开\n"
            "字幕：CAFE MORI 济州岛抹茶拿铁 6口味装\n"
            "画外音：济州岛有机抹茶做的，一盒六个味道!\n\n"
            "【10-30秒 逐个测评】\n"
            "（切换镜头/每个口味5秒）\n"
            "1. 经典抹茶：撕开→倒入杯子→加水→搅拌→喝一口\n"
            "   字幕/画外音：经典抹茶，纯正，8分\n"
            "2. 炼乳抹茶：同上流程\n"
            "   字幕/画外音：炼乳我的最爱！奶香爆炸！9分！\n"
            "3. 黑糖抹茶\n"
            "   字幕/画外音：黑糖这个焦糖味绝了，8.5分\n"
            "4. 燕麦抹茶\n"
            "   字幕/画外音：燕麦味适合乳糖不耐的宝子，7.5分\n"
            "5. 椰奶抹茶\n"
            "   字幕/画外音：椰奶味夏天喝清爽，8分\n"
            "6. 香草抹茶\n"
            "   字幕/画外音：香草味很高级，8.5分\n\n"
            "【30-40秒 总结】\n"
            "（回到主播口播镜头）\n"
            "总结推荐：炼乳>黑糖>香草>经典>椰奶>燕麦\n"
            "0反式脂肪酸，一杯45大卡，冷热水都能泡\n"
            "一盒69.9，链接在左下角⬅️\n"
        ),
        "hashtags": ["#抹茶拿铁", "#开箱测评", "#韩国零食", "#CAFEMORI", "#美食测评", "#吃货"],
        "suggested_images": [
            "封面：产品盒+六条口味展开",
            "封面关键词：便利店爆款/6口味测评/韩国",
            "重点画面：冲泡溶解过程特写",
        ],
    },
    {
        "style": "剧情故事型",
        "title": "同事每天都喝同款饮料，我终于忍不住问了。。。结局是他被搬空了",
        "content_template": (
            "【0-5秒 悬念】\n"
            "画面：同事工位上总是有一杯绿色饮料，看起来很香\n"
            "字幕：这个同事每天下午都在喝什么？\n"
            "背景音乐：悬疑风格BGM\n\n"
            "【5-15秒 揭秘】\n"
            "画面：走近同事，指着他杯子问\n"
            "同事A：你这个喝的啥啊，天天喝\n"
            "同事B（主角）：CAFE MORI抹茶拿铁啊，韩国买的，你要不要试试？\n"
            "动作：从抽屉里拿出一盒，抽出一条\n\n"
            "【15-25秒 反转】\n"
            "画面：快节奏剪辑\n"
            "同事A喝了一口，表情从怀疑→惊讶→上头\n"
            "同事A：卧槽这个好喝！给我链接！\n"
            "同事B：一盒6种口味，你喜欢哪个味道？\n"
            "同事A：我全要了，这盒归我了\n"
            "（夸张：把整盒抱走）\n\n"
            "【25-30秒 收尾】\n"
            "画面：同事B无奈地看着空抽屉，对着镜头摊手\n"
            "字幕：又被搬空了😂\n"
            "画外音：链接在左下角，自己买吧，别指望同事了👇\n"
        ),
        "hashtags": ["#职场日常", "#搞笑", "#抹茶拿铁", "#同事", "#零食分享", "#CAFEMORI"],
        "suggested_images": [
            "封面：两个同事抢一盒产品的搞笑表情",
            "封面关键词：同事/每天喝/被搬空",
        ],
    },
    {
        "style": "教程/DIY型",
        "title": "咖啡店同款抹茶拿铁，在家3秒搞定！比外卖好喝100倍！",
        "content_template": (
            "【0-3秒 结果先行】\n"
            "画面：一杯完美的分层抹茶拿铁（冰饮）\n"
            "字幕：咖啡店同款抹茶拿铁，在家3秒搞定✨\n\n"
            "【3-15秒 教程开始】\n"
            "Step 1：准备杯子 + 冰块\n"
            "动作：透明杯加满冰块\n\n"
            "Step 2：倒入抹茶粉\n"
            "动作：撕开CAFE MORI抹茶拿铁，倒入杯中\n"
            "特写：抹茶粉细腻翠绿\n\n"
            "Step 3：加冷水\n"
            "动作：倒入冷水/牛奶\n"
            "特写：抹茶瞬间溶解，形成漂亮的分层\n\n"
            "Step 4：搅拌\n"
            "动作：用吸管搅拌，颜色渐变\n\n"
            "【15-25秒 做3种口味对比】\n"
            "快速剪辑做3杯不同口味\n"
            "经典抹茶（翠绿）→ 炼乳（奶绿）→ 黑糖（焦糖色）\n"
            "三杯并列展示，颜色差异明显\n\n"
            "【25-30秒 收尾】\n"
            "三杯举起来碰杯\n"
            "画外音：3块钱一杯的快乐，学会了吗？\n"
            "字幕：左下角get同款⬇️\n"
        ),
        "hashtags": ["#教程", "#DIY饮品", "#抹茶拿铁", "#在家做饮品", "#CAFEMORI", "#夏日饮品"],
        "suggested_images": [
            "封面：分层漂亮的抹茶拿铁冰饮特写",
            "封面关键词：咖啡店同款/3秒搞定/在家做",
        ],
    },
    {
        "style": "对比评测型",
        "title": "奶茶店抹茶拿铁VS速溶抹茶拿铁，差距到底有多大？",
        "content_template": (
            "【0-5秒 挑战设置】\n"
            "画面：桌子上放两杯抹茶拿铁，左边是奶茶店的（¥22），右边是CAFE MORI速溶（¥11.6）\n"
            "字幕：盲测挑战！猜猜哪个是速溶的？\n"
            "画外音：敢不敢盲测一下，到底能不能喝出来区别？\n\n"
            "【5-15秒 盲测过程】\n"
            "朋友上场，蒙眼喝两杯\n"
            "第一口（奶茶店）：嗯，好喝\n"
            "第二口（CAFE MORI）：嗯？？这个更好喝啊，奶味更浓，抹茶味也正\n"
            "揭晓答案：右边是速溶的！\n"
            "朋友震惊表情😮\n\n"
            "【15-25秒 数据分析】\n"
            "画面切到表格/数据对比\n"
            "奶茶店：¥22/杯，300kcal，排队15分钟\n"
            "CAFE MORI：¥11.6/杯，45kcal，3秒冲泡\n"
            "画外音：价格差一倍，热量差6倍，时间和便利性就不用说了吧\n\n"
            "【25-30秒 收尾】\n"
            "画外音：不是我吹，这盒抹茶拿铁真的是今年的宝藏发现了\n"
            "字幕：¥69.9/盒6条，左下角捡漏⬇️\n"
        ),
        "hashtags": ["#测评", "#盲测", "#抹茶拿铁", "#省钱攻略", "#CAFEMORI", "#性价比"],
        "suggested_images": [
            "封面：两杯抹茶拿铁对比+问号",
            "封面关键词：盲测/速溶vs现做/猜猜哪个",
        ],
    },
    {
        "style": "Vlog日常型",
        "title": "韩国打工人的一天vlog：就是靠这杯续命的",
        "content_template": (
            "【0-5秒 早晨通勤】\n"
            "画面：闹钟→起床→地铁通勤\n"
            "字幕：打工人平凡的一天开始了\n"
            "BGM：轻快的Lo-fi音乐\n\n"
            "【5-15秒 办公室】\n"
            "到工位→打开电脑→从抽屉里拿出一盒CAFE MORI\n"
            "抽出一条炼乳抹茶味→撕开→倒入杯中→加热水\n"
            "特写：绿色抹茶在热水中慢慢溶解，画面治愈\n"
            "字幕：早上第一杯，炼乳抹茶味yyds\n\n"
            "【15-25秒 工作片段】\n"
            "快速剪辑工作场景：打字、开会、打电话\n"
            "每个片段切回来都抿一口抹茶拿铁\n"
            "字幕：忙碌中的小确幸☕️\n\n"
            "【25-30秒 下班时刻】\n"
            "画面：下班收拾东西，往包里又放了一条（预备明天）\n"
            "BGM渐强\n"
            "字幕：又是被抹茶拿铁治愈的一天✨\n"
            "画外音：美好的一天，从一杯抹茶拿铁开始和结束～\n"
        ),
        "hashtags": ["#vlog", "#打工人日常", "#抹茶拿铁", "#CAFEMORI", "#治愈系", "#我的日常"],
        "suggested_images": [
            "封面：手握抹茶拿铁+办公桌场景",
            "封面关键词：打工人/续命/抹茶拿铁",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════
# 平台配置
# ═══════════════════════════════════════════════════════════════

PLATFORMS = {
    "xiaohongshu": {
        "name": "小红书",
        "templates": XIAOHONGSHU_TEMPLATES,
        "platform_notes": "标题20字以内最佳，正文需分段+emoji，图片4-6张为宜",
    },
    "wechat": {
        "name": "微信公众号",
        "templates": WECHAT_TEMPLATES,
        "platform_notes": "文章800-1500字，配图6-10张，适合深度内容",
    },
    "moments": {
        "name": "朋友圈",
        "templates": MOMENTS_TEMPLATES,
        "platform_notes": "文案控制在6行以内（约200字），配图3-4张为佳",
    },
    "douyin": {
        "name": "抖音",
        "templates": DOUYIN_TEMPLATES,
        "platform_notes": "视频15-45秒，前3秒必须抓人眼球，脚本含分镜指导",
    },
}


# ═══════════════════════════════════════════════════════════════
# 核心生成逻辑
# ═══════════════════════════════════════════════════════════════

def generate_for_platform(product: ProductInfo, platform_key: str) -> List[Dict]:
    """为指定平台生成所有版本的营销内容"""
    platform = PLATFORMS[platform_key]
    results = []

    for i, tmpl in enumerate(platform["templates"]):
        title = _render_title(tmpl, product, platform_key)
        content = _render_content(tmpl, product, platform_key)
        hashtags = _format_hashtags(tmpl["hashtags"], platform_key)

        entry = {
            "version": i + 1,
            "style": tmpl["style"],
            "title": title,
            "content": content,
            "hashtags": hashtags,
            "suggested_images": tmpl["suggested_images"],
            "platform_notes": platform["platform_notes"],
        }
        results.append(entry)

    return results


def _render_title(tmpl: Dict, product: ProductInfo, platform: str) -> str:
    """渲染标题，替换模板变量"""
    title = tmpl.get("title", "")
    title = title.replace("{product_name}", product.name)
    title = title.replace("{brand}", product.brand)
    title = title.replace("{price}", product.price)
    return title


def _render_content(tmpl: Dict, product: ProductInfo, platform: str) -> str:
    """渲染正文，替换模板变量"""
    content = tmpl.get("content_template", "")
    content = content.replace("{product_name}", product.name)
    content = content.replace("{brand}", product.brand)
    content = content.replace("{origin}", product.origin)
    content = content.replace("{price}", product.price)
    content = content.replace("{target_audience}", product.target_audience)
    content = content.replace("{tasting_notes}", product.tasting_notes)
    content = content.replace("{package}", product.package)

    # 加入特色描述
    features_str = "\n".join(f"  ✔ {f}" for f in product.features)
    content = content.replace("{features_list}", features_str)

    return content


def _format_hashtags(hashtags: List[str], platform: str) -> List[str]:
    """平台对应的标签格式"""
    if platform == "xiaohongshu":
        return [f"#{tag}" for tag in hashtags]
    elif platform == "wechat":
        return [f"#{tag}" for tag in hashtags]
    elif platform == "moments":
        return [f"#{tag}" for tag in hashtags]
    elif platform == "douyin":
        return [f"#{tag}" for tag in hashtags]
    return hashtags


# ═══════════════════════════════════════════════════════════════
# 输出格式化
# ═══════════════════════════════════════════════════════════════

def format_output(data: Dict[str, List[Dict]], output_format: str = "terminal") -> str:
    """格式化输出结果"""
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    # 终端友好格式
    lines = []
    lines.append("=" * 70)
    lines.append("  AI 营销素材生成器 — 生成报告")
    lines.append("=" * 70)
    lines.append("")

    for platform_key, versions in data.items():
        platform_name = PLATFORMS[platform_key]["name"]
        lines.append("━━━ " + platform_name + f"（{len(versions)}个版本）━━━")
        lines.append("  → " + PLATFORMS[platform_key]['platform_notes'])
        lines.append("")

        for v in versions:
            lines.append("  ┌── 版本 " + str(v['version']) + "：" + v['style'] + " ──┐")
            lines.append("  │ 标题：" + v['title'])
            lines.append("  │ 正文：")
            for line in v["content"].split("\n"):
                lines.append("  │ " + line)
            lines.append("  │ 标签：" + ' '.join(v['hashtags']))
            lines.append("  │ 建议图片：")
            for img in v["suggested_images"]:
                lines.append("  │   • " + img)
            lines.append("  └" + "=" * 40 + "┘")
            lines.append("")

    lines.append("=" * 70)
    lines.append("  生成完毕 | 中韩出海数智港 AI Marketing Generator")
    lines.append("=" * 70)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════

def cli():
    parser = argparse.ArgumentParser(
        description="AI 营销素材生成器 — 为中韩出海产品自动生成多平台营销文案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例命令：\n"
            "  python3 tools/ai_marketing_generator.py latte --platform all\n"
            "  python3 tools/ai_marketing_generator.py latte --platform xiaohongshu\n"
            "  python3 tools/ai_marketing_generator.py latte --platform wechat --format json\n"
            "  python3 tools/ai_marketing_generator.py --new-product\n"
            "  python3 tools/ai_marketing_generator.py --list-products\n"
        ),
    )

    parser.add_argument(
        "product",
        nargs="?",
        help="产品名称（内置产品：latte, matcha）",
    )
    parser.add_argument(
        "-p", "--platform",
        choices=["all"] + list(PLATFORMS.keys()),
        default="all",
        help="目标平台（默认：所有平台）",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["terminal", "json"],
        default="terminal",
        help="输出格式（默认：终端图文格式）",
    )
    parser.add_argument(
        "--new-product",
        action="store_true",
        help="添加新产品（交互式输入）",
    )
    parser.add_argument(
        "--list-products",
        action="store_true",
        help="列出内置产品",
    )

    args = parser.parse_args()

    # --list-products
    if args.list_products:
        print("=" * 50)
        print("  内置产品列表")
        print("=" * 50)
        for key, prod in DEMO_PRODUCTS.items():
            print(f"  [{key}] {prod.name}")
            print(f"        品牌：{prod.brand} | 产地：{prod.origin}")
            print(f"        价格：{prod.price}")
            print(f"        人群：{prod.target_audience}")
            print(f"        卖点：{'; '.join(prod.features[:3])}...")
            print()
        return

    # --new-product
    if args.new_product or args.product is None:
        print("=" * 50)
        print("  ✏️ 添加新产品")
        print("=" * 50)
        name = input("  产品名称：").strip()
        brand = input("  品牌：").strip()
        origin = input("  产地：").strip()
        price = input("  价格区间：").strip()
        target_audience = input("  目标人群：").strip()
        print("  卖点（每行一个，输入空行结束）：")
        features = []
        while True:
            f = input("    > ").strip()
            if not f:
                break
            features.append(f)

        if not name:
            print("\n  ⚠️ 产品名称不能为空，使用演示数据")
            product_key = "latte"
        else:
            product_key = name.lower().replace(" ", "_")
            DEMO_PRODUCTS[product_key] = ProductInfo(
                name=name,
                brand=brand or "未填写",
                origin=origin or "未填写",
                features=features or ["无详细卖点"],
                price=price or "待定",
                target_audience=target_audience or "未指定",
            )
            print(f"\n  ✅ 产品「{name}」已保存\n")

    else:
        product_key = args.product.lower().strip()

    if product_key not in DEMO_PRODUCTS:
        print(f"\n  ❌ 未找到产品 '{args.product}'")
        print(f"  可用产品：{[k for k in DEMO_PRODUCTS.keys()]}")
        print("  使用 --new-product 添加新产品\n")
        sys.exit(1)

    product = DEMO_PRODUCTS[product_key]

    # 确定目标平台
    if args.platform == "all":
        targets = list(PLATFORMS.keys())
    else:
        targets = [args.platform]

    # 生成营销素材
    progress = (
        f"\n  ⚙️ 正在为「{product.name}」生成营销素材...\n"
        f"    品牌：{product.brand} | 产地：{product.origin}\n"
        f"    价格：{product.price}\n"
        f"    目标平台：{', '.join(PLATFORMS[p]['name'] for p in targets)}\n"
    )
    if args.format == "json":
        import sys as _sys
        _sys.stderr.write(progress)
    else:
        print(progress)

    result = {}
    for platform_key in targets:
        result[platform_key] = generate_for_platform(product, platform_key)

    output = format_output(result, output_format=args.format)
    print(output)


if __name__ == "__main__":
    cli()
