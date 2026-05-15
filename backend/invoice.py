"""
中韩出海数智港 - 发票自动生成模块

功能：
  1. 订单→自动生成PDF发票
  2. 发票信息写入SQLite invoices表
  3. API端点查询和下载发票

技术：
  - reportlab 生成PDF（与合规报告模块保持一致）
  - SQLite invoices 表存储发票记录
  - 统一API前缀: /api/v1/invoices/*

发票号码规则：INV-YYYYMMDD-XXXX（日期+4位序号）
"""

import os
import uuid
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from backend.database import get_db

# reportlab 用于PDF生成（与 compliance/report_pdf.py 保持一致）
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors

router = APIRouter(tags=["invoices"])

# ── 常量 ──────────────────────────────────────────

INVOICE_DIR = Path(__file__).parent / "data" / "invoices"
INVOICE_DIR.mkdir(parents=True, exist_ok=True)

# 颜色方案
BRAND_COLOR = HexColor("#6366f1")  # indigo-500
BRAND_DARK = HexColor("#111827")
BRAND_GRAY = HexColor("#6b7280")
LIGHT_GRAY = HexColor("#f3f4f6")
LIGHT_INDIGO = HexColor("#eef2ff")

# ── 样式 ──────────────────────────────────────────

styles = getSampleStyleSheet()

INVOICE_STYLES = {
    "title": ParagraphStyle(
        "InvoiceTitle", fontName="Helvetica-Bold", fontSize=28, leading=36,
        alignment=TA_CENTER, textColor=BRAND_DARK, spaceAfter=4*mm,
    ),
    "subtitle": ParagraphStyle(
        "InvoiceSubtitle", fontName="Helvetica", fontSize=10, leading=14,
        alignment=TA_CENTER, textColor=BRAND_GRAY, spaceAfter=8*mm,
    ),
    "company_name": ParagraphStyle(
        "CompanyName", fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=BRAND_DARK, spaceAfter=2*mm,
    ),
    "company_info": ParagraphStyle(
        "CompanyInfo", fontName="Helvetica", fontSize=9, leading=13,
        textColor=BRAND_GRAY, spaceAfter=1*mm,
    ),
    "section_title": ParagraphStyle(
        "SectionTitle", fontName="Helvetica-Bold", fontSize=12, leading=16,
        textColor=BRAND_COLOR, spaceAfter=4*mm, spaceBefore=6*mm,
    ),
    "label": ParagraphStyle(
        "Label", fontName="Helvetica", fontSize=9, leading=13,
        textColor=BRAND_GRAY,
    ),
    "value": ParagraphStyle(
        "Value", fontName="Helvetica", fontSize=10, leading=14,
        textColor=BRAND_DARK,
    ),
    "amount": ParagraphStyle(
        "Amount", fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=BRAND_DARK, alignment=TA_RIGHT,
    ),
    "total": ParagraphStyle(
        "Total", fontName="Helvetica-Bold", fontSize=18, leading=24,
        textColor=BRAND_COLOR, alignment=TA_RIGHT,
    ),
    "footer": ParagraphStyle(
        "Footer", fontName="Helvetica", fontSize=8, leading=11,
        textColor=BRAND_GRAY, alignment=TA_CENTER, spaceBefore=10*mm,
    ),
    "note": ParagraphStyle(
        "Note", fontName="Helvetica-Oblique", fontSize=9, leading=13,
        textColor=BRAND_GRAY, spaceBefore=4*mm,
    ),
}


# ── 辅助函数 ──────────────────────────────────────

def _generate_invoice_no() -> str:
    """生成发票号码：INV-YYYYMMDD-XXXX"""
    date_str = datetime.now().strftime("%Y%m%d")
    # 查询当天已生成的发票数量，用于序号
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE invoice_no LIKE ?",
            (f"INV-{date_str}-%",),
        )
        count = cursor.fetchone()[0]
    except Exception:
        count = 0
    finally:
        conn.close()
    seq = count + 1
    return f"INV-{date_str}-{seq:04d}"


def _get_order_info(order_id: int) -> dict:
    """从数据库获取订单信息，兼容 orders 表和 saas_subscriptions 表"""
    conn = get_db()
    try:
        # 先查 orders 表（V1一次性订单）
        cursor = conn.execute(
            """SELECT id, order_no, user_company, user_name, user_phone, user_email,
                      plan_type, price, status, created_at
               FROM orders WHERE id = ?""",
            (order_id,),
        )
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            order = dict(zip(columns, row))
            order["source"] = "orders"
            return order

        # 再查 saas_subscriptions 表（V2订阅订单）
        cursor = conn.execute(
            """SELECT id, subscription_no as order_no, user_company, user_name,
                      user_phone, user_email, plan_type, price, status, created_at
               FROM saas_subscriptions WHERE id = ?""",
            (order_id,),
        )
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            order = dict(zip(columns, row))
            order["source"] = "saas_subscriptions"
            return order

        return None
    finally:
        conn.close()


def _format_currency(amount: float) -> str:
    """格式化金额为人民币显示"""
    return f"¥{amount:,.2f}"


def _build_pdf_invoice(invoice_data: dict) -> BytesIO:
    """
    构建PDF发票文档

    invoice_data 字段:
        invoice_no: str        - 发票号码
        order_no: str          - 订单号
        user_company: str      - 客户企业名称
        user_name: str         - 联系人
        user_email: str        - 邮箱
        user_phone: str        - 电话
        plan_type: str         - 套餐类型
        plan_name: str         - 套餐中文名
        price: float           - 金额
        price_display: str     - 格式化金额
        status: str            - 发票状态
        created_at: str        - 开票日期
    """
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=15*mm,
        leftMargin=20*mm,
        rightMargin=20*mm,
    )

    elements = []
    S = INVOICE_STYLES

    # ── 页眉：公司信息 ──
    elements.append(Paragraph("中韩出海数智港", S["title"]))
    elements.append(Paragraph("China-Korea Digital Port", S["subtitle"]))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=BRAND_COLOR,
        spaceAfter=6*mm, spaceBefore=2*mm,
    ))

    # ── 发票标题 ──
    elements.append(Paragraph(f"<b>增值税电子普通发票</b>", ParagraphStyle(
        "InvoiceLabel", fontName="Helvetica-Bold", fontSize=16, leading=22,
        alignment=TA_CENTER, textColor=BRAND_DARK, spaceAfter=2*mm,
    )))
    elements.append(Paragraph(
        f"发票号码: {invoice_data['invoice_no']}",
        S["subtitle"],
    ))
    elements.append(Spacer(1, 4*mm))

    # ── 发票抬头信息 ──
    elements.append(Paragraph("购买方信息", S["section_title"]))

    buyer_data = [
        [Paragraph("企业名称", S["label"]),
         Paragraph(invoice_data["user_company"], S["value"])],
        [Paragraph("联系人", S["label"]),
         Paragraph(invoice_data["user_name"], S["value"])],
        [Paragraph("电子邮箱", S["label"]),
         Paragraph(invoice_data["user_email"], S["value"])],
        [Paragraph("联系电话", S["label"]),
         Paragraph(invoice_data.get("user_phone", "—"), S["value"])],
    ]

    buyer_table = Table(buyer_data, colWidths=[80*mm, 110*mm])
    buyer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BRAND_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 4*mm),
    ]))
    elements.append(buyer_table)
    elements.append(Spacer(1, 4*mm))

    # ── 商品明细 ──
    elements.append(Paragraph("商品明细", S["section_title"]))

    plan_name = invoice_data.get("plan_name", invoice_data["plan_type"])
    quantity = "1"
    unit_price = _format_currency(invoice_data["price"])
    total = _format_currency(invoice_data["price"])

    detail_header = [
        Paragraph("<b>商品名称</b>", S["label"]),
        Paragraph("<b>数量</b>", S["label"]),
        Paragraph("<b>单价</b>", S["label"]),
        Paragraph("<b>金额</b>", S["label"]),
    ]
    detail_row = [
        Paragraph(f"中韩出海数智港 - {plan_name}", S["value"]),
        Paragraph(quantity, S["value"]),
        Paragraph(unit_price, S["value"]),
        Paragraph(total, S["amount"]),
    ]

    detail_table = Table(
        [detail_header, detail_row],
        colWidths=[100*mm, 25*mm, 30*mm, 35*mm],
    )
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BRAND_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3*mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 4*mm))

    # ── 合计 ──
    total_data = [
        [Paragraph("合计金额（大写）", S["label"]),
         Paragraph("", S["value"]),
         Paragraph("小写", S["label"]),
         Paragraph(invoice_data["price_display"], S["total"])],
    ]
    total_table = Table(total_data, colWidths=[80*mm, 55*mm, 25*mm, 30*mm])
    total_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 4*mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4*mm),
        ("BACKGROUND", (2, 0), (3, 0), LIGHT_INDIGO),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 4*mm))

    # ── 开票信息 ──
    elements.append(Paragraph("开票信息", S["section_title"]))

    issue_data = [
        [Paragraph("开票日期", S["label"]),
         Paragraph(invoice_data["created_at"].split(" ")[0] if " " in invoice_data["created_at"]
                   else invoice_data["created_at"], S["value"])],
        [Paragraph("发票状态", S["label"]),
         Paragraph("已开票", S["value"])],
        [Paragraph("订单编号", S["label"]),
         Paragraph(invoice_data["order_no"], S["value"])],
    ]

    issue_table = Table(issue_data, colWidths=[80*mm, 110*mm])
    issue_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BRAND_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 4*mm),
    ]))
    elements.append(issue_table)
    elements.append(Spacer(1, 8*mm))

    # ── 备注 ──
    elements.append(Paragraph(
        "备注：本发票为系统自动生成电子发票，与纸质发票具有同等法律效力。如信息有误，请联系客服。",
        S["note"],
    ))

    # ── 页脚 ──
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=BRAND_GRAY,
        spaceAfter=3*mm, spaceBefore=3*mm,
    ))
    elements.append(Paragraph(
        "中韩出海数智港 | 沪ICP备2026007459号-1 | 客服邮箱: support@go-aiport.com",
        S["footer"],
    ))
    elements.append(Paragraph(
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        S["footer"],
    ))

    doc.build(elements)
    buf.seek(0)
    return buf


# ── 数据库初始化 ──────────────────────────────────

def init_invoice_tables():
    """初始化发票相关数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            order_id INTEGER NOT NULL,
            order_no TEXT NOT NULL,
            order_source TEXT NOT NULL DEFAULT 'orders'
                CHECK(order_source IN ('orders', 'saas_subscriptions')),
            user_company TEXT NOT NULL,
            user_name TEXT NOT NULL,
            user_phone TEXT,
            user_email TEXT NOT NULL,
            plan_type TEXT NOT NULL,
            plan_name TEXT,
            price REAL NOT NULL,
            tax_rate REAL NOT NULL DEFAULT 0.0,
            tax_amount REAL NOT NULL DEFAULT 0.0,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'issued'
                CHECK(status IN ('issued', 'cancelled', 'voided')),
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cancelled_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ════════════════════════════════════════════════════════════
# API端点
# ════════════════════════════════════════════════════════════

@router.post("/api/v1/invoices/generate")
async def generate_invoice(body: dict):
    """
    从订单生成发票

    请求体:
    {
        "order_id": 123,
        "order_source": "orders"  // 可选: "orders" (默认) | "saas_subscriptions"
    }

    响应:
    {
        "success": true,
        "invoice_id": 1,
        "invoice_no": "INV-20260514-0001",
        "message": "发票生成成功",
        "download_url": "/api/v1/invoices/1/download"
    }
    """
    order_id = body.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="缺少 order_id")

    # 获取订单信息
    order = _get_order_info(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")

    if order["status"] not in ("paid", "active"):
        raise HTTPException(
            status_code=400,
            detail=f"订单状态为 {order['status']}，仅已支付(paid/active)的订单可生成发票",
        )

    # 检查是否已生成过发票
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT id, invoice_no FROM invoices WHERE order_id = ? AND status = 'issued'",
            (order_id,),
        )
        existing = cursor.fetchone()
        if existing:
            return {
                "success": True,
                "invoice_id": existing[0],
                "invoice_no": existing[1],
                "message": "该订单已生成过发票",
                "download_url": f"/api/v1/invoices/{existing[0]}/download",
            }

        # 生成发票号码
        invoice_no = _generate_invoice_no()

        # 套餐中文名映射
        plan_names = {
            "free": "免费初评",
            "depth": "深度方案",
            "annual": "年订阅",
            "source": "源码授权",
            "basic": "基础版",
            "professional": "专业版",
            "enterprise": "企业版",
        }
        plan_name = plan_names.get(order.get("plan_type", ""), order.get("plan_type", ""))

        price = order["price"]
        total_amount = price

        # 插入发票记录
        cursor = conn.execute(
            """INSERT INTO invoices
               (invoice_no, order_id, order_no, order_source,
                user_company, user_name, user_phone, user_email,
                plan_type, plan_name, price, total_amount, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'issued')""",
            (invoice_no, order_id, order.get("order_no", ""),
             order.get("source", "orders"),
             order["user_company"], order["user_name"],
             order.get("user_phone", ""), order["user_email"],
             order.get("plan_type", ""), plan_name,
             price, total_amount),
        )
        conn.commit()
        invoice_id = cursor.lastrowid

        # 生成PDF
        invoice_data = {
            "invoice_no": invoice_no,
            "order_no": order.get("order_no", ""),
            "user_company": order["user_company"],
            "user_name": order["user_name"],
            "user_email": order["user_email"],
            "user_phone": order.get("user_phone", ""),
            "plan_type": order.get("plan_type", ""),
            "plan_name": plan_name,
            "price": price,
            "price_display": _format_currency(price),
            "total_amount": total_amount,
            "status": "issued",
            "created_at": datetime.now().isoformat(),
        }

        try:
            pdf_buf = _build_pdf_invoice(invoice_data)
            pdf_filename = f"{invoice_no}.pdf"
            pdf_path = INVOICE_DIR / pdf_filename
            with open(pdf_path, "wb") as f:
                f.write(pdf_buf.getvalue())

            # 更新PDF路径
            conn.execute(
                "UPDATE invoices SET pdf_path = ? WHERE id = ?",
                (str(pdf_path), invoice_id),
            )
            conn.commit()
        except Exception as pdf_err:
            print(f"[Invoice] PDF生成失败: {pdf_err}")
            # 即使PDF生成失败，发票记录依然存在

        return {
            "success": True,
            "invoice_id": invoice_id,
            "invoice_no": invoice_no,
            "message": "发票生成成功",
            "download_url": f"/api/v1/invoices/{invoice_id}/download",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成发票失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/invoices/{invoice_id}/download")
async def download_invoice(invoice_id: int):
    """
    下载发票PDF

    响应的 Content-Disposition 为 attachment 触发下载
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT * FROM invoices WHERE id = ?",
            (invoice_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="发票不存在")

        columns = [desc[0] for desc in cursor.description]
        invoice = dict(zip(columns, row))

        # 如果已有PDF文件，直接返回
        if invoice.get("pdf_path"):
            pdf_path = Path(invoice["pdf_path"])
            if pdf_path.exists():
                return StreamingResponse(
                    open(pdf_path, "rb"),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="{invoice["invoice_no"]}.pdf"',
                    },
                )

        # 没有PDF文件，实时生成
        invoice_data = {
            "invoice_no": invoice["invoice_no"],
            "order_no": invoice["order_no"],
            "user_company": invoice["user_company"],
            "user_name": invoice["user_name"],
            "user_email": invoice["user_email"],
            "user_phone": invoice.get("user_phone", ""),
            "plan_type": invoice["plan_type"],
            "plan_name": invoice.get("plan_name", invoice["plan_type"]),
            "price": invoice["price"],
            "price_display": _format_currency(invoice["price"]),
            "total_amount": invoice["total_amount"],
            "status": invoice["status"],
            "created_at": invoice.get("created_at", ""),
        }

        pdf_buf = _build_pdf_invoice(invoice_data)

        # 缓存到磁盘
        pdf_filename = f"{invoice['invoice_no']}.pdf"
        pdf_path = INVOICE_DIR / pdf_filename
        try:
            with open(pdf_path, "wb") as f:
                f.write(pdf_buf.getvalue())
            conn.execute(
                "UPDATE invoices SET pdf_path = ? WHERE id = ?",
                (str(pdf_path), invoice_id),
            )
            conn.commit()
        except Exception:
            pass

        pdf_buf.seek(0)
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{invoice["invoice_no"]}.pdf"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载发票失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/invoices")
async def list_invoices(
    order_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """查询发票列表"""
    conn = get_db()
    try:
        query = "SELECT * FROM invoices WHERE 1=1"
        params = []

        if order_id is not None:
            query += " AND order_id = ?"
            params.append(order_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        # 先查总数
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        invoices = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return {
            "success": True,
            "data": invoices,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


@router.get("/api/v1/invoices/{invoice_id}")
async def get_invoice(invoice_id: int):
    """获取发票详情"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT * FROM invoices WHERE id = ?",
            (invoice_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="发票不存在")

        columns = [desc[0] for desc in cursor.description]
        invoice = dict(zip(columns, row))

        return {
            "success": True,
            "data": invoice,
            "download_url": f"/api/v1/invoices/{invoice_id}/download",
        }
    finally:
        conn.close()
