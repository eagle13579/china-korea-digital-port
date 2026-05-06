"""
中韩出海数智港 - License授权校验模块

功能：
  - generate_license(licensee, plan, days) → str: 生成授权码
  - check_license() → dict: 校验当前授权有效性（环境变量或文件）
  - validate_license_key(key) → dict: 校验指定授权码

SOP依据: product-deployment-commercialization-sop 第4步(源码授权) + 第5步(对外版License校验)
项目前缀: ckdp (China-Korea Digital Port)
"""
import os
import json
import base64
import hashlib
import datetime
from pathlib import Path
from typing import Optional

# ── 常量 ──────────────────────────────────────────────

# License文件路径（相对或绝对）
LICENSE_FILE = Path(__file__).parent.parent / "data" / "license.key"

# 环境变量名称（优先级高于文件）
ENV_VAR_NAME = "CKDP_LICENSE"

# 签名密钥 - 与项目绑定，不可对外泄露
SIGNING_SECRET = "ckdp-digital-port-seed-2026"

# 支持的套餐类型
PLAN_TYPES = {"free", "one-time", "annual", "enterprise"}

# 套餐名称映射
PLAN_NAMES = {
    "free": "免费初评",
    "one-time": "深度方案",
    "annual": "年订阅",
    "enterprise": "企业定制",
}

# ── 核心函数 ──────────────────────────────────────────


def generate_license(
    licensee: str,
    plan: str = "one-time",
    days: int = 365,
    seats: int = 1,
) -> str:
    """
    生成License授权码。

    参数：
        licensee : str  - 被授权方名称（企业名或个人名）
        plan     : str  - 套餐类型: free | one-time | annual | enterprise
        days     : int  - 授权天数（默认365）
        seats    : int  - 授权席位（默认1）

    返回：
        str - Base64编码的授权码字符串

    示例：
        >>> key = generate_license("首尔贸易株式会社", "annual", 365, 5)
        >>> print(key)
        eyJsaWNlbnNlZSI6...  # Base64字符串
    """
    if plan not in PLAN_TYPES:
        raise ValueError(f"不支持的套餐类型: {plan}，支持: {', '.join(PLAN_TYPES)}")

    expires = (datetime.datetime.now(datetime.timezone.utc) +
               datetime.timedelta(days=days)).isoformat()

    payload = {
        "licensee": licensee,
        "plan": plan,
        "plan_name": PLAN_NAMES.get(plan, plan),
        "seats": seats,
        "issued": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "expires": expires,
    }

    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    signature = _sign(payload_json)

    combined = json.dumps({
        "payload": payload,
        "signature": signature,
    }, sort_keys=True, ensure_ascii=False)

    return base64.b64encode(combined.encode("utf-8")).decode("utf-8")


def validate_license_key(key: str) -> dict:
    """
    校验指定的授权码字符串有效性。

    参数：
        key : str - Base64编码的授权码

    返回：
        dict - {
            "valid": bool,          # 是否有效
            "licensee": str|None,   # 被授权方
            "plan": str|None,       # 套餐类型
            "plan_name": str|None,  # 套餐名称
            "seats": int|None,      # 授权席位
            "issued": str|None,     # 签发时间
            "expires": str|None,    # 过期时间
            "expired": bool|None,   # 是否已过期
            "error": str|None,      # 错误信息
        }
    """
    result = {
        "valid": False,
        "licensee": None,
        "plan": None,
        "plan_name": None,
        "seats": None,
        "issued": None,
        "expires": None,
        "expired": None,
        "error": None,
    }

    if not key:
        result["error"] = "授权码为空"
        return result

    try:
        decoded = base64.b64decode(key.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)

        payload = data.get("payload", {})
        signature = data.get("signature", "")

        # 验证签名
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        expected_sig = _sign(payload_json)

        if signature != expected_sig:
            result["error"] = "授权码签名无效，可能被篡改"
            return result

        # 提取字段
        result["licensee"] = payload.get("licensee")
        result["plan"] = payload.get("plan")
        result["plan_name"] = payload.get("plan_name")
        result["seats"] = payload.get("seats", 1)
        result["issued"] = payload.get("issued")
        result["expires"] = payload.get("expires")

        # 检查过期
        expires_str = payload.get("expires", "")
        if expires_str:
            try:
                expires_dt = datetime.datetime.fromisoformat(expires_str)
                result["expired"] = datetime.datetime.now(datetime.timezone.utc) > expires_dt
            except (ValueError, TypeError):
                result["expired"] = None
        else:
            result["expired"] = None

        result["valid"] = True
        result["error"] = None

    except (json.JSONDecodeError, UnicodeDecodeError, base64.binascii.Error) as e:
        result["error"] = f"授权码格式无效: {str(e)}"

    return result


def check_license() -> dict:
    """
    校验当前环境的License有效性。
    优先级：环境变量 > license.key文件

    返回：
        dict - validate_license_key() 的返回格式，增加 key_source 字段
    """
    result = {
        "valid": False,
        "licensee": None,
        "plan": None,
        "plan_name": None,
        "seats": None,
        "issued": None,
        "expires": None,
        "expired": None,
        "key_source": None,
        "error": None,
    }

    # 1. 优先读取环境变量
    key = os.environ.get(ENV_VAR_NAME, "")

    if key:
        result["key_source"] = "env"
    else:
        # 2. 尝试从文件读取
        if LICENSE_FILE.exists():
            try:
                key = LICENSE_FILE.read_text("utf-8").strip()
                result["key_source"] = "file"
            except (OSError, IOError):
                result["error"] = f"无法读取授权文件: {LICENSE_FILE}"
                return result
        else:
            result["error"] = f"未找到授权信息（环境变量{ENV_VAR_NAME}未设置，文件{LICENSE_FILE}不存在）"
            return result

    # 3. 校验授权码
    validation = validate_license_key(key)
    result.update(validation)
    result["key_source"] = result.get("key_source") or validation.get("key_source")

    return result


def _sign(payload_json: str) -> str:
    """内部签名函数 - 基于 payload + 项目密钥 生成签名"""
    raw = f"{SIGNING_SECRET}-{payload_json}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def format_license_status(result: dict) -> str:
    """格式化授权状态为可读字符串（用于启动日志）"""
    if result["valid"]:
        status = "✅ 授权有效"
        licensee = result.get("licensee", "未知")
        plan_name = result.get("plan_name", "未知")
        seats = result.get("seats", 1)
        expires = result.get("expires", "未知")
        source = result.get("key_source", "未知")

        expired = result.get("expired", False)
        if expired:
            status = "⚠️ 授权已过期"

        return (
            f"{status}\n"
            f"   被授权方: {licensee}\n"
            f"   套餐: {plan_name} ({seats}席)\n"
            f"   过期时间: {expires}\n"
            f"   授权来源: {source}"
        )
    else:
        return f"❌ 授权无效: {result.get('error', '未知错误')}"


# ── 独立测试 ──────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("中韩出海数智港 - License授权模块自检")
    print("=" * 60)

    # 1. 生成测试授权码
    print("\n[1] 生成测试授权码...")
    test_key = generate_license("首尔贸易株式会社", "annual", 365, 5)
    print(f"    授权码: {test_key[:60]}...")

    # 2. 校验生成的授权码
    print("\n[2] 校验授权码...")
    validation = validate_license_key(test_key)
    print(format_license_status(validation))

    # 3. 校验篡改的授权码
    print("\n[3] 篡改测试...")
    tampered = test_key[:-5] + "AAAAA"
    v2 = validate_license_key(tampered)
    print(f"    结果: {'✅ 正确拒绝' if not v2['valid'] else '❌ 异常通过'}")
    print(f"    错误: {v2['error']}")

    # 4. 生成各种套餐授权码
    print("\n[4] 各套餐授权码生成:")
    for plan in ["free", "one-time", "annual", "enterprise"]:
        k = generate_license("测试客户", plan, 30)
        v = validate_license_key(k)
        print(f"    {PLAN_NAMES[plan]:8s} → {v['valid']} | {k[:40]}...")

    # 5. 检查当前环境
    print("\n[5] 当前环境授权检查:")
    env_check = check_license()
    print(format_license_status(env_check))

    print("\n" + "=" * 60)
    print("自检完成")
    print("=" * 60)
