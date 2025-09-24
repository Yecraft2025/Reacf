# 📧 Reacf

一个基于 Python + GitHub Actions 的邮件发送工具，支持：

✅ 支持 curl 调用触发

✅ 支持 GitHub Actions 手动触发

✅ 多账号、多收件人批量发送

✅ 自定义 HTML 模板

❌ 信息完全加密

✅ 发送统计日志

## 📦 使用方式

### 1. 环境变量

在 **Reacf→ Settings → Secrets and variables → Actions → New repository secret** 配置：

| 变量名        | 说明                                                         | 必填 |
| ------------- | ------------------------------------------------------------ | ---- |
| `EMAIL_USER`  | 邮箱账号                                                     | ❌    |
| `EMAIL_PASS`  | 授权码                                                       | ❌    |
| `EMAIL_TO`    | 默认收件人（当 CF 未传入时使用）                             | ❌    |
| `SMTP_SERVER` | SMTP 地址（常见邮箱可不填写）                                | ❌    |
| `SMTP_PORT`   | SMTP 端口（同SMTP_SERVER）                                   | ❌    |
| `SMTP_SSL`    | 是否启用 SSL，`true` / `false`（默认自动判断）               | ❌    |
| `ENABLE_LOG`  | 日志保存选项：`one`（一个文件），`date`（按日期分），`unique`（按调用次数），其他值则不保存 | ❌    |
| `MESSAGES`    | 内部测试用（格式同messages）                                 | ❌    |

**⚠️非必填不代表不需要，要保证至少一种有效的传入方式**

**⚠️核心参数建议保存到部署环境，网络传输不能保证完全安全！！！**

------

### 2. 使用 curl 调用 GitHub Actions

| 参数       | 说明                                           | 必填 |
| ---------- | ---------------------------------------------- | ---- |
| `title`    | 标题                                           | ✅    |
| `message`  | 内容                                           | ✅    |
| `to`       | 收件人（优先级高于Actions，用于单独发送）      | ❌    |
| `user`     | 邮箱账号                                       | ❌    |
| `pass`     | 授权码                                         | ❌    |
| `server`   | SMTP 地址（常见邮箱可不填写）                  | ❌    |
| `port`     | SMTP 端口（同SMTP_SERVER）                     | ❌    |
| `ssl`      | 是否启用 SSL，`true` / `false`（默认自动判断） | ❌    |

**⚠️不建议通过网络传递核心参数**

向 Actions 传递的 `messages`，格式如下：

```txt
[
  {
    "title": "测试邮件 1",
    "message": "这里是邮件内容 1"
  },
  {
    "title": "测试邮件 2",
    "message": "这里是邮件内容 2",
    "to": "user1@example.com"
  },
  {
    "title": "测试邮件 3",
    "message": "这里是邮件内容 3",
    "user": "user1@example.com",
    "pass": "user1@example.com授权码"
  },
  {
    "title": "测试邮件 4",
    "message": "这里是邮件内容 4",
    "to": "user2@example.com",
    "user": "user2@example.com",
    "pass": "user2@example.com授权码"
  },
  {
    "title": "测试邮件 5",
    "message": "这里是邮件内容 5",
    "user": "user3@example.com",
    "pass": "user3@example.com授权码"，
    "server": "smtp.example.com",
    "port": "465",
    "ssl": "True"
  },
  {
    "title": "测试邮件 6",
    "message": "这里是邮件内容 6",
    "to": "user3@example.com",
    "user": "user4@example.com",
    "pass": "user4@example.com授权码"，
    "server": "smtp.example.com",
    "port": "465",
    "ssl": "True"
  }
]
```

说明：

- `title` 和 `message` 是必填内容！
- `to` 可选，如果缺失会使用 Actions 的 `EMAIL_TO`。
- `user`/`pass`/`server`/`port`/`ssl`不建议直接使用，除非需要其他邮箱发送

**可以通过 GitHub API 使用 `curl` 触发事件，向 Actions 传递邮件参数：**

```txt
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <YOUR_GITHUB_TOKEN>" \
  https://api.github.com/repos/<OWNER>/<REPO>/actions/workflows/send_email.yml/dispatches \
  -d '{
    "ref": "cf-send-main",
    "inputs": {
      "messages": "填入messages"
    }
  }'

```

说明

- `<YOUR_GITHUB_TOKEN>` 必须是 **具有 repo 权限的 PAT（Personal Access Token）** 或者 **仓库的 GitHub Actions Token**。
  - https://github.com/settings/personal-access-tokens -> Fine-grained personal access tokens -> Add permissions -> Actions -> Read and write

- `<OWNER>` 替换为你的 GitHub 用户名或组织名。
- `<REPO>` 替换为你的仓库名，默认为 `Reacf`。
- `messages` 的值必须是 **转义后的 JSON 字符串**。
- 除了`messages`，也可以直接传入**环境变量**，但不推荐！

------

### 3. 日志管理

日志会存放在 `logs/` 目录下：

- `one` → `logs/send_email.log`
- `date` → `logs/send_email_2025-09-20.log`
- `unique` → `logs/send_email_20250920_12345678.log`
- 其他 → 仅打印，不保存

**⚠️在`one`和`date`模式下，如果连续调用，会导致 push 错误**

------

### 4. 模板

HTML 模板文件默认从 `index.html` 加载，支持以下占位符：

| 占位符        | 替换内容             |
| ------------- | -------------------- |
| `tip-YES`     | 消息标题             |
| `time-YES`    | 发送时间（北京时间） |
| `system-YES`  | 系统信息             |
| `sip-YES`     | 本地 IP              |
| `gip-YES`     | 公网 IP              |
| `content-YES` | 消息正文             |

**⚠️至少要保留`tip-YES`和`content-YES`存在**

------

## ⚠️ 注意事项

- Gmail、Outlook 等需要开启 **应用专用密码**，不能用普通登录密码。
- QQ 邮箱需要开启 **SMTP 服务** 并使用授权码。

- 建议用 **专门的发件邮箱**，避免被封。
