"""
中韩出海数智港 · 北极星看板 —— 产品薄层

继承自 polaris_framework.PolarisFramework，只写差异化代码。
"""
import sys
from pathlib import Path

# 添加框架所在目录到 Python 路径
_FRAMEWORK_DIR = Path(__file__).parent / "../../../../../L3工作室/CEO战略分析/北极星看板"
sys.path.insert(0, str(_FRAMEWORK_DIR.resolve()))

from polaris_framework import PolarisFramework


class ChinaKoreaPortPolaris(PolarisFramework):
    """中韩出海数智港 · 产品北极星看板

    继承 PolarisFramework 基类，仅添加产品特有的：
    - 配置路径指向本地 polaris_config.yaml
    - 产品专用 API 路由
    """

    def __init__(self):
        palace = self._get_palace()
        self.product_dir = palace / "L5孵化室/产品开发/出海项目/中韩出海数智港/china-korea-digital-port"

        super().__init__(
            palace_root=palace,
            config_relpath="L5孵化室/产品开发/出海项目/中韩出海数智港/china-korea-digital-port/polaris_config.yaml",
            import_name=__name__,
            template_folder=None,
        )

        # 注册产品特有的路由
        self._register_product_routes()

    @staticmethod
    def _get_palace():
        """获取记忆宫殿根路径"""
        from polaris_framework.core import get_palace_root
        return get_palace_root()

    # ──────────────────────────────────────────────
    #  产品特有路由
    # ──────────────────────────────────────────────

    def _register_product_routes(self):
        app = self.app

        @app.route('/')
        def index():
            """中韩出海数智港 · 北极星主页"""
            return self.render(
                'base.html',
                title='中韩出海数智港 · 北极星看板',
                subtitle='中韩跨境数智化服务平台 · 合规+市场+技术全维度',
            )

        @app.route('/api/compliance-score')
        def api_compliance_score():
            """合规完成度详情"""
            config = self.load_config()
            indicators = config.get('indicators', [])
            compliance_ind = next(
                (i for i in indicators if i.get('id') == 'compliance_readiness'), {}
            )
            children = compliance_ind.get('children', [])
            details = {
                c.get('id'): {
                    "name": c.get('name'),
                    "progress": c.get('progress', 0),
                    "target": c.get('target', 100),
                    "status": "🟢" if c.get('progress', 0) >= 60 else ("🟡" if c.get('progress', 0) >= 30 else "🔴"),
                    "actions": [
                        {"name": a.get('name'), "progress": a.get('progress', 0)}
                        for a in c.get('actions', [])
                    ],
                }
                for c in children
            }
            return self.jsonify({
                "product": "中韩出海数智港",
                "compliance_score": details,
            })

        @app.route('/api/customer-count')
        def api_customer_count():
            """客户数统计"""
            config = self.load_config()
            indicators = config.get('indicators', [])
            customer_ind = next(
                (i for i in indicators if i.get('id') == 'customer_count'), {}
            )
            children = customer_ind.get('children', [])
            return self.jsonify({
                "product": "中韩出海数智港",
                "onboarded_clients": next(
                    (c.get('progress', 0) for c in children if c.get('id') == 'onboarded_clients'), 0
                ),
                "pipeline_leads": next(
                    (c.get('progress', 0) for c in children if c.get('id') == 'pipeline_leads'), 0
                ),
                "satisfaction": next(
                    (c.get('progress', 0) for c in children if c.get('id') == 'satisfaction'), 0
                ),
            })

    # ──────────────────────────────────────────────
    #  override 基类方法
    # ──────────────────────────────────────────────

    def _list_projects(self) -> list:
        """中韩出海数智港的子模块"""
        return [
            {"name": "合规诊断", "type": "核心模块", "health": 62},
            {"name": "知识图谱", "type": "核心模块", "health": 68},
            {"name": "AI对话", "type": "核心模块", "health": 75},
            {"name": "客户面板", "type": "核心模块", "health": 50},
            {"name": "支付系统", "type": "扩展模块", "health": 45},
            {"name": "销售管道", "type": "扩展模块", "health": 35},
        ]


# ══════════════════════════════════════════════════
#  启动入口
# ══════════════════════════════════════════════════

if __name__ == '__main__':
    app = ChinaKoreaPortPolaris()
    print(f"🌉 中韩出海数智港 · 北极星看板启动中...")
    print(f"  ├ 配置路径: {app.config_path}")
    print(f"  └ 访问地址: http://localhost:5052")
    app.run(host='0.0.0.0', port=5052, debug=True)
