"""
中韩出海数智港 - Pydantic数据模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date


class ContactForm(BaseModel):
    """联系表单模型 — 同时兼容线上 contact 字段和本地 name 字段"""
    name: str = Field("", min_length=0, max_length=100, description="联系人姓名")
    company: Optional[str] = Field(None, max_length=200, description="公司名称")
    email: str = Field(..., description="电子邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    message: Optional[str] = Field(None, max_length=2000, description="留言内容")
    contact: Optional[str] = Field(None, max_length=100, description="线上版联系人字段")

    @classmethod
    def validate_contact(cls, values):
        """如果线上发来的字段是 contact 而不是 name，自动填充 name"""
        if not values.get("name") and values.get("contact"):
            values["name"] = values["contact"]
        return values


class DemoRequest(BaseModel):
    """预约演示模型"""
    name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    company: Optional[str] = Field(None, max_length=200, description="公司名称")
    email: str = Field(..., description="电子邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    preferred_date: Optional[str] = Field(None, description="期望日期")
    notes: Optional[str] = Field(None, max_length=2000, description="备注")


class PricingInquiry(BaseModel):
    """定价咨询模型"""
    name: str = Field(..., min_length=1, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    email: str = Field(...)
    phone: Optional[str] = Field(None, max_length=50)
    plan_type: Optional[str] = Field(None, description="感兴趣的套餐")
    message: Optional[str] = Field(None, max_length=2000)


class ServiceInquiry(BaseModel):
    """服务邀请（数字员工邀请）模型"""
    name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    company: Optional[str] = Field(None, max_length=200, description="公司名称")
    email: str = Field(..., description="电子邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    employee_id: Optional[int] = Field(None, description="感兴趣的数字员工ID")
    employee_name: Optional[str] = Field(None, max_length=100, description="感兴趣的数字员工姓名")
    message: Optional[str] = Field(None, max_length=2000, description="需求描述")


class APIResponse(BaseModel):
    """统一API响应格式"""
    success: bool = True
    message: str = "操作成功"


# ── 支付系统模型 ──────────────────────────────────────

class OrderCreate(BaseModel):
    """创建订单请求"""
    user_company: str = Field(..., min_length=1, max_length=200, description="企业名称")
    user_name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    user_phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    user_email: str = Field(..., description="电子邮箱")
    plan_type: str = Field(..., pattern=r'^(free|depth|annual|source)$', description="套餐类型: free/depth/annual/source")
    price: float = Field(..., ge=0, description="金额")


class PaymentCreate(BaseModel):
    """上传付款凭证请求（JSON部分）"""
    order_id: int = Field(..., description="订单ID")
    method: str = Field(..., pattern=r'^(alipay|wechat|transfer)$', description="付款方式")
    amount: float = Field(..., ge=0, description="付款金额")


class StatusUpdate(BaseModel):
    """订单状态更新请求"""
    status: str = Field(..., pattern=r'^(paid|cancelled)$', description="目标状态: paid/cancelled")


# ── 支付系统模型（新JWT认证版）──────────────────────────

class TopUpRequest(BaseModel):
    """人工充值请求（admin接口）"""
    user_id: int = Field(..., description="用户ID")
    amount: float = Field(..., gt=0, description="充值金额（元）")
    plan_type: str = Field("pro", pattern=r'^(basic|pro)$', description="充值到的套餐类型")
    remark: Optional[str] = Field(None, max_length=200, description="充值备注")


class PaymentOrderResponse(BaseModel):
    """支付订单创建响应"""
    success: bool = True
    message: str = "订单创建成功"
    order_id: int
    order_no: str
    price: float
    plan_type: str
    plan_name: str
    status: str
    qr_code_url: Optional[str] = None
    alipay_trade_no: Optional[str] = None
    is_free: bool = False
    simulate_mode: bool = False