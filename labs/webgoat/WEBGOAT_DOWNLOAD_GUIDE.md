# WebGoat 手动下载安装指南

## 下载地址

**GitHub Releases页面**: https://github.com/WebGoat/WebGoat/releases

### 最新版本下载链接

| 文件 | 下载地址 |
|------|----------|
| webgoat-server-8.2.2.jar | https://github.com/WebGoat/WebGoat/releases/download/v8.2.2/webgoat-server-8.2.2.jar |
| webwolf-server-8.2.2.jar | https://github.com/WebGoat/WebGoat/releases/download/v8.2.2/webwolf-server-8.2.2.jar |

---

## 安装步骤

### 步骤1: 下载文件

**方法1: 浏览器下载**
- 打开 https://github.com/WebGoat/WebGoat/releases
- 找到最新版本 (v8.2.2)
- 点击 Assets 展开
- 下载 `webgoat-server-8.2.2.jar`

**方法2: curl/wget下载**
```bash
# 创建目录
mkdir -p D:/password_guesser/labs/webgoat

# 下载WebGoat
curl -L -o D:/password_guesser/labs/webgoat/webgoat-server-8.2.2.jar \
  https://github.com/WebGoat/WebGoat/releases/download/v8.2.2/webgoat-server-8.2.2.jar

# 下载WebWolf
curl -L -o D:/password_guesser/labs/webgoat/webwolf-server-8.2.2.jar \
  https://github.com/WebGoat/WebGoat/releases/download/v8.2.2/webwolf-server-8.2.2.jar
```

### 步骤2: 检查Java环境

```bash
# 检查Java版本
java -version

# 需要Java 11+
```

如果没有Java，下载安装:
- https://adoptium.net/ (推荐)

### 步骤3: 启动WebGoat

```bash
# 进入目录
cd D:/password_guesser/labs/webgoat

# 启动WebGoat
java -jar webgoat-server-8.2.2.jar --server.port=8080

# 同时启动WebWolf (可选)
java -jar webwolf-server-8.2.2.jar --server.port=9090
```

### 步骤4: 访问WebGoat

打开浏览器访问:
- **WebGoat**: http://localhost:8080/WebGoat
- **WebWolf**: http://localhost:9090/WebWolf

---

## 课程列表

| 序号 | 课程名称 | 难度 |
|------|----------|------|
| 1 | General | 入门 |
| 2 | Authentication & Authorization | 中等 |
| 3 | Session Management | 中等 |
| 4 | Access Control | 中等 |
| 5 | SQL Injection | 高 |
| 6 | XSS | 高 |
| 7 | Path Traversal | 中等 |
| 8 | Insecure Deserialization | 高 |
| 9 | Vulnerable Components | 高 |
| 10 | Crypto | 中等 |
| 11 | HTTP Basics | 入门 |

---

## 自动化测试脚本

下载完成后运行:

```bash
python labs/scripts/test_webgoat_local.py
```

---

## 状态检查

| 步骤 | 状态 |
|------|------|
| 下载JAR文件 | ⚠️ 需手动下载 |
| 安装Java | ⚠️ 需检查 |
| 启动服务 | ⚠️ 待启动 |
| 访问测试 | ⚠️ 待验证 |

---

*指南生成: 2026-06-05*