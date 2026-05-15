"""
中韩出海数智港 - 用户行为分析 CLI 仪表盘
在终端中直接运行： python -m backend.analytics.analytics_dashboard
"""
import sys
from datetime import datetime
from .event_tracker import (
    get_today_active_users,
    get_today_events_count,
    get_popular_pages,
    get_conversion_funnel,
    get_event_type_breakdown,
    FUNNEL_STAGES,
)


class AnalyticsDashboard:
    """简单CLI仪表盘：今日活跃用户、热门页面、转化漏斗"""

    @staticmethod
    def print_separator(char="=", width=60):
        print(char * width)

    @staticmethod
    def print_header(text):
        AnalyticsDashboard.print_separator()
        print(f"  {text}")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        AnalyticsDashboard.print_separator()

    @staticmethod
    def print_footer():
        AnalyticsDashboard.print_separator("=")
        print()

    @staticmethod
    def show_active_users():
        """显示今日活跃用户"""
        users = get_today_active_users()
        events = get_today_events_count()
        print(f"\n  📊 今日活跃用户: {users}")
        print(f"  📈 今日事件总数: {events}")
        if users > 0:
            avg = events / users
            print(f"  🎯 人均事件数:   {avg:.1f}")

    @staticmethod
    def show_popular_pages(limit=8):
        """显示热门页面排行"""
        print("\n  🔥 热门页面 (今日/累计):")
        pages = get_popular_pages(limit)
        if not pages:
            print("    (暂无数据)")
            return
        for i, p in enumerate(pages, 1):
            url = p["page_url"] or "(未知)"
            views = p["views"]
            bar = "█" * min(views, 50)
            print(f"  {i:2d}. {url:<30s} {views:>5d} 次  {bar}")

    @staticmethod
    def show_conversion_funnel():
        """显示转化漏斗"""
        print("\n  🥊 转化漏斗 (独立访客):")
        funnel = get_conversion_funnel(FUNNEL_STAGES)
        if not funnel or all(f["visitors"] == 0 for f in funnel):
            print("    (暂无数据)")
            return

        max_visitors = max(f["visitors"] for f in funnel) or 1
        for i, stage in enumerate(funnel):
            visitors = stage["visitors"]
            bar_len = int((visitors / max_visitors) * 30)
            bar = "▓" * bar_len + "░" * (30 - bar_len)

            # 转化率计算
            if i == 0:
                conversion_rate = 100.0
            elif funnel[i - 1]["visitors"] > 0:
                conversion_rate = (visitors / funnel[i - 1]["visitors"]) * 100
            else:
                conversion_rate = 0.0

            # 整体转化率（从第一步起）
            if funnel[0]["visitors"] > 0:
                overall_rate = (visitors / funnel[0]["visitors"]) * 100
            else:
                overall_rate = 0.0

            arrow = "  →  " if i > 0 else "     "
            print(f"  {stage['stage']:<8s} {arrow} {visitors:>5d} 访客  {bar}")
            if i > 0:
                print(f"           步骤转化率: {conversion_rate:>6.1f}%")
            print(f"           整体转化率: {overall_rate:>6.1f}%")

    @staticmethod
    def show_event_breakdown():
        """显示事件类型分布"""
        print("\n  📋 事件类型分布 (今日):")
        events = get_event_type_breakdown()
        if not events:
            print("    (暂无数据)")
            return

        total = sum(e["count"] for e in events) or 1
        for e in events:
            pct = (e["count"] / total) * 100
            bar = "█" * int(pct / 2)
            print(f"  {e['event_type']:<20s} {e['count']:>5d}  {pct:>5.1f}%  {bar}")

    @staticmethod
    def show_full_report():
        """显示完整仪表盘报告"""
        AnalyticsDashboard.print_header("  中韩出海数智港 - 用户行为分析仪表盘")
        AnalyticsDashboard.show_active_users()
        AnalyticsDashboard.show_popular_pages()
        AnalyticsDashboard.show_conversion_funnel()
        AnalyticsDashboard.show_event_breakdown()
        AnalyticsDashboard.print_footer()


def main():
    """CLI入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="中韩出海数智港 - 用户行为分析仪表盘"
    )
    parser.add_argument(
        "--full", "-f",
        action="store_true",
        default=True,
        help="显示完整报告（默认）"
    )
    parser.add_argument(
        "--users", "-u",
        action="store_true",
        help="仅显示活跃用户统计"
    )
    parser.add_argument(
        "--pages", "-p",
        action="store_true",
        help="仅显示热门页面"
    )
    parser.add_argument(
        "--funnel", "-c",
        action="store_true",
        help="仅显示转化漏斗"
    )
    parser.add_argument(
        "--events", "-e",
        action="store_true",
        help="仅显示事件类型分布"
    )

    args = parser.parse_args()

    # 如果指定了任何子选项，则只显示对应的部分
    any_sub = args.users or args.pages or args.funnel or args.events

    if not any_sub or args.full:
        AnalyticsDashboard.show_full_report()
    else:
        if args.users:
            AnalyticsDashboard.print_header("  活跃用户统计")
            AnalyticsDashboard.show_active_users()
        if args.pages:
            AnalyticsDashboard.print_header("  热门页面排行")
            AnalyticsDashboard.show_popular_pages()
        if args.funnel:
            AnalyticsDashboard.print_header("  转化漏斗")
            AnalyticsDashboard.show_conversion_funnel()
        if args.events:
            AnalyticsDashboard.print_header("  事件类型分布")
            AnalyticsDashboard.show_event_breakdown()
        AnalyticsDashboard.print_footer()


if __name__ == "__main__":
    main()
