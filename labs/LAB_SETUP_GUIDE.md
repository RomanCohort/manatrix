# 渗透测试靶机环境配置指南

## 环境清单

### 1. DVWA (Damn Vulnerable Web Application)
- **类型**: Web应用漏洞靶场
- **漏洞**: SQL注入、XSS、CSRF、文件上传等
- **部署方式**: Docker

### 2. Metasploitable2
- **类型**: Linux服务器漏洞靶场
- **漏洞**: SSH、FTP、SMB、HTTP等服务漏洞
- **部署方式**: VMware/VirtualBox虚拟机

### 3. Windows Server 2022
- **类型**: 现代企业环境
- **防御**: Defender for Endpoint + EDR + ASR
- **部署方式**: VMware/VirtualBox虚拟机

### 4. HackTheBox
- **类型**: 云端靶场
- **访问**: VPN连接
- **URL**: https://app.hackthebox.com

---

## 快速部署脚本

### DVWA Docker部署

```bash
# 安装DVWA
docker run -d -p 80:80 vulnerables/web-dvwa

# 访问
http://localhost:80/DVWA
# 默认账号: admin/password
```

### Metasploitable2部署

1. 下载镜像: https://sourceforge.net/projects/metasploitable/
2. 导入VMware/VirtualBox
3. 网络配置: NAT或桥接
4. IP地址: 动态获取或静态配置

### HackTheBox配置

```bash
# 安装OpenVPN
sudo apt install openvpn

# 连接HTB VPN
sudo openvpn --config htb.ovpn

# 验证连接
ping 10.10.10.10
```

---

## 测试用例

### DVWA测试场景

| 难度 | 漏洞 | 测试方法 |
|------|------|----------|
| Low | SQL注入 | `' OR 1=1--` |
| Medium | SQL注入 | `UNION SELECT` |
| High | SQL注入 | `blind SQLi` |
| Impossible | 无漏洞 | 绕过防御 |

### Metasploitable2测试场景

| 服务 | 端口 | CVE | 利用方法 |
|------|------|-----|----------|
| SSH | 22 | CVE-2008-0166 | 弱密钥 |
| FTP | 21 | CVE-2011-2523 | vsftpd backdoor |
| SMB | 445 | CVE-2017-0143 | EternalBlue |
| HTTP | 80 | 多个 | PHP漏洞 |

### Windows Server 2022测试场景

| 组件 | 防御状态 | 测试挑战 |
|------|----------|----------|
| Defender | 启用 | Payload被拦截 |
| AMSI | 启用 | PowerShell检测 |
| EDR | 启用 | 行为监控 |
| ASR | 启用 | 攻击面减少 |

---

## 自动化测试脚本

见 `labs/scripts/` 目录:
- `dvwa_test.py` - DVWA自动化测试
- `metasploit_scan.py` - Metasploitable扫描
- `htb_auto.py` - HTB自动化攻击

---

## 安全注意事项

⚠️ **重要提醒**:
1. 所有靶机仅用于合法安全测试
2. 不要在生产网络部署
3. 使用隔离网络环境
4. 测试完成后清理环境
5. 遵守当地法律法规

---

## 配置状态

| 环境 | 状态 | 配置方法 |
|------|------|----------|
| DVWA | ⚠️ 待配置 | Docker |
| Metasploitable2 | ⚠️ 待下载 | VMware |
| Windows Server | ⚠️ 待获取 | 需许可证 |
| HackTheBox | ⚠️ 待连接 | VPN |

---

*配置指南生成: 2026-06-05*