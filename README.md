# Tech Content Weekly

自动汇总 Bilibili、YouTube 与播客/小宇宙科技创作者的新内容，生成深绿色、适合 PC 与手机阅读的 HTML/Markdown 周报，并可通过 Gmail 自动发送。

## v0.2 能力

- YouTube 使用官方 Data API v3，采集上传时间、时长、播放量和评论数。
- 播客及 Bilibili 使用用户配置的公开 RSS/Atom；不硬编码不稳定的非公开接口或 Cookie。
- 展示本周新内容；视频按公开播放量统计最近 30 天 Top 3，播客按时间展示最近 3 期。
- 每个创作者单独容错：失败时读取该创作者最近缓存并在报告中标注，不影响其他来源。
- 可选 AI 导读：OpenAI 优先，调用失败或额度不足时自动回退 DeepSeek，页尾标注实际供应商和模型。
- Gmail SMTP 支持多个收件人；GitHub Actions 每周三 07:00（Asia/Shanghai）运行，也可手动触发。

## 本地运行

```bash
python -m pip install -e .
copy .env.example .env
tech-content-weekly --sample
```

样例模式不访问平台；在线生成使用：

```bash
tech-content-weekly
```

生成并发送邮件：

```bash
tech-content-weekly --send
```

输出位于 `output/weekly-日期.md` 和 `output/weekly-日期.html`，采集或模型降级信息写入 `output/warnings.log`。

## 创作者配置

编辑 `config.toml`，复制一个 `[[creators]]` 区块即可扩展列表。

YouTube 的 `id` 必须是 `UC` 开头的 channel ID：

```toml
[[creators]]
name = "3Blue1Brown"
platform = "youtube"
id = "UCYO_jab_esuFRV4b17AJtAw"
url = "https://www.youtube.com/@3blue1brown"
enabled = true
```

播客使用节目官方公开 RSS；`url` 可继续填写小宇宙页面，用作报告跳转：

```toml
[[creators]]
name = "节目名称"
platform = "podcast"
id = "唯一英文标识"
url = "https://www.xiaoyuzhoufm.com/podcast/..."
feed_url = "https://节目公开RSS地址"
enabled = true
```

Bilibili 目前使用你确认可访问的 RSS/Atom 地址，例如自建 RSSHub。项目不内置第三方公共 RSSHub 实例，以免服务失效：

```toml
[[creators]]
name = "UP 主名称"
platform = "bilibili"
id = "主页 UID"
url = "https://space.bilibili.com/UID"
feed_url = "https://你的RSS服务/bilibili/user/video/UID"
enabled = true
```

播客 RSS 一般不提供统一播放量和评论数，因此报告不会把最新单集包装成热度排名。

## 环境变量

本地填写 `.env`，不要提交该文件：

| 变量 | 是否必需 | 用途 |
|---|---:|---|
| `YOUTUBE_API_KEY` | 使用 YouTube 时 | Google Cloud 中启用 YouTube Data API v3 后创建 |
| `OPENAI_API_KEY` | AI 二选一 | 首选 AI 服务 |
| `DEEPSEEK_API_KEY` | AI 二选一 | OpenAI 失败后的回退服务 |
| `OPENAI_MODEL` | 否 | 覆盖 `config.toml` 的 OpenAI 模型 |
| `DEEPSEEK_MODEL` | 否 | 覆盖 `config.toml` 的 DeepSeek 模型 |
| `SMTP_USER` | 发送邮件时 | Gmail 完整邮箱地址 |
| `SMTP_PASSWORD` | 发送邮件时 | Gmail 两步验证生成的应用专用密码，不是登录密码 |
| `SMTP_FROM` | 否 | 发件人，默认等于 `SMTP_USER` |
| `EMAIL_RECIPIENTS` | 否 | 覆盖 TOML 收件人，多个地址用英文逗号分隔 |

默认模型为 `gpt-5-mini` 和 `deepseek-chat`。如果账号无权使用默认 OpenAI 模型，可通过 OpenAI 的 `GET /v1/models` 查看当前 API Key 可用模型后设置 `OPENAI_MODEL`；DeepSeek 同理可通过其模型列表接口或控制台确认。

## GitHub Actions 配置

仓库 `Settings → Secrets and variables → Actions` 中配置：

Secrets（敏感值）：

- `YOUTUBE_API_KEY`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `SMTP_USER`
- `SMTP_PASSWORD`

Variables（普通配置）：

- `EMAIL_RECIPIENTS`，例如 `stargazerq@foxmail.com,871517518@qq.com`
- `SMTP_FROM`（可选）
- `OPENAI_MODEL`（可选）
- `DEEPSEEK_MODEL`（可选）

进入 `Actions → weekly-content-report → Run workflow` 可手动验证。建议第一次选择 `sample=true`、`send_email=true`，先验证排版和 Gmail；第二次使用在线数据。定时表达式使用 UTC：`0 23 * * 2`，对应上海时间每周三 07:00。

## 测试与限制

```bash
python -m unittest discover -s tests -v
```

- 公开播放量和评论数是报告生成时快照，不代表历史时点值。
- YouTube API 有每日配额；当前每个频道最多读取最近 50 条上传记录。
- Bilibili 的稳定公开数据渠道有限，因此 v0.2 要求用户配置 RSS，并以缓存保证单源失败不拖垮整期。
- 报告中的 AI 导读只依据采集到的标题、简介和指标，不等同于完整观看/收听后的内容总结。
