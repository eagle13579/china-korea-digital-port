# SSH 服务器登录修复指南

## 问题诊断

**目标服务器**: 47.100.160.250 (阿里云ECS)
**域名**: go-aiport.com
**操作系统**: Ubuntu
**当前状态**: ❌ SSH 连接失败

### 检测结果

| 项目 | 状态 | 详情 |
|------|------|------|
| SSH 端口 22 | ✅ 开放 | TCP 连接正常 |
| 用户 root | ❌ 拒绝 | Permission denied (publickey,password) |
| 用户 opc | ❌ 拒绝 | Permission denied (publickey,password) |
| 用户 ubuntu | ❌ 拒绝 | Permission denied (publickey,password) |
| 本地 RSA 密钥 | ❌ 未注册 | 公钥未添加到服务器的 authorized_keys |
| 本地 ED25519 密钥 | ❌ 未注册 | 公钥未添加到服务器的 authorized_keys |

### 原因

服务器开启了密钥认证 + 密码认证，但本地 WSL 环境中的 SSH 公钥 (`~/.ssh/id_rsa.pub` 和 `~/.ssh/id_ed25519.pub`) **未被添加到服务器**的 `~/.ssh/authorized_keys` 或 `/root/.ssh/authorized_keys` 中。

## 需要您提供的信息

要修复 SSH 登录，请**任选其一**方式提供凭据：

### 方式 A：提供 SSH 密码（推荐，最快）

请提供以下任一用户的登录密码：
- `root` 用户密码
- `opc` 用户密码（deploy.sh 中使用的用户）

### 方式 B：提供服务器私钥文件

如果您有连接到 47.100.160.250 的 SSH 密钥对（.pem 或 id_rsa 文件），请将私钥文件提供给开发团队。

### 方式 C：在阿里云控制台重置密码

1. 登录阿里云 ECS 控制台
2. 找到实例 47.100.160.250
3. 点击"重置实例密码"
4. 设置密码后重启实例
5. 将新密码提供给开发团队

## 拿到凭据后的操作步骤

```bash
# 方式 1：使用密码登录
ssh opc@47.100.160.250

# 方式 2：使用密钥文件登录
ssh -i /path/to/your-key.pem opc@47.100.160.250

# 方式 3：使用密码登录后配置密钥认证（推荐）
ssh opc@47.100.160.250
# 在服务器上执行:
# mkdir -p ~/.ssh
# echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDH4H2ndxkP5pEyTPGacnkeTsi4x2OOn2YQCCsmK0FBOuruIpQM4HQRTHwg+jNgxmdx7rnDAUh8Zq4CfCjQpaJSvqpklctlWR14s6Az19qmAsJfRqIgcQWdxPZofOKxFWouSMjqtnbYxZHcSPrxk/gQrtz3YBjKI+yl7xNt9PiPDW9iex7mDbeW6FL1HxI9IHiCYbYBOhkqLZ+npgPKXpvi0FfMxsfuuwdnhnaiB5/bbgGUH30pjQbNxUBhbuBdb3WWftldjbIpxGmb1iqQywLPvztcMMZ0TcU+UvQ8BlpST7Q00gokKNJ07JeSVOVhQDx7pvL9QBU61+U0vF5Tokd4c0GmQ50fbozaEj0CMIP4KWbMd9ZazajctLDsbriYWwSuUt0Te2dsYQbxzwxCzEjh8CBDyf2XYUd8DYftKSUlzJlhKm/9l/hYtul5g4AnyragkVctVyxWipjT/owUz9gi65xsCfA9rRphizkQmyt9jRIHPwNeMQnBSj9bwtQmFDk= 56867@Roger" >> ~/.ssh/authorized_keys
# chmod 600 ~/.ssh/authorized_keys
# chmod 700 ~/.ssh
```

> 注意：部署脚本 `deploy/deploy.sh` 中使用的用户是 `opc`（见脚本第 80-88 行），建议使用 opc 用户登录。
