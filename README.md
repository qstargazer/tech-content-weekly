# Tech Content Weekly · 科技新知周报

自动汇总 Bilibili、YouTube、播客/小宇宙与豆瓣热门图书的新内容，生成深绿色、适合 PC 与手机阅读的 HTML/Markdown 周报，并可通过 Gmail 自动发送。

## v0.3 能力

- YouTube 使用官方 Data API v3，采集上传时间、时长、播放量和评论数。
- 播客使用公开 RSS/Atom；Bilibili 使用 QNAP 自建 RSSHub，避免依赖容易出现 403 的第三方公共实例。
- 豆瓣读书使用自建 RSSHub 的热门图书排行与非虚构/新书速递榜单，展示评分。
- 展示本周新内容；视频按公开播放量统计最近 30 天 Top 3，播客按时间展示最近 3 期。
- 每个创作者单独容错：失败时读取该创作者最近缓存并在报告中标注，不影响其他来源。
- 可选 AI 导读：DeepSeek 优先，失败时回退 OpenAI；OpenAI 额度不足只写入 Actions 日志，不在周报中展示。
- 场景分类推荐：将本周内容分为「通勤 / 碎片时间」与「需要专门时间深入研究」两类并给出理由，附本周最值得投入的一条。AI 可用时由模型分类，否则使用内置规则兜底。
- Gmail SMTP 支持多个收件人；GitHub Actions 每周二、周五 05:00（Asia/Shanghai）运行，也可手动触发。

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

默认列表当前包含：

- Bilibili: 8 configured accounts (including “MUSI的运动日记 · 骑行路线” and account 349169140; see config.toml)
- YouTube: 3Blue1Brown（YouTube）、初日医学 - 宋晏仁医师 x Cofit；前者提供最新英文原版，后者提供控糖与减重等健康内容
- 小宇宙：Huberman Lab、张小珺商业访谈录、津津乐道、家庭教育圆桌谈、天才捕手FM、沈奕斐的播客，以及已有的其他订阅
- 豆瓣读书：非虚构热门榜、科学新知新书速递、商业经管新书速递

豆瓣榜单走自建 RSSHub 的 `douban` 路由，榜单条目没有独立发布时间，程序自动以频道更新时间归类到本周：

```toml
[[creators]]
name = "豆瓣热门图书 · 非虚构"
platform = "douban"
id = "douban-book-rank-nonfiction"
url = "https://book.douban.com/"
feed_url = "$RSSHUB_BASE_URL/douban/book/rank/nonfiction?key=$RSSHUB_ACCESS_KEY"
enabled = true
```

可选榜单：`/douban/book/rank/fiction`（虚构类）、`/douban/book/rank/nonfiction`（非虚构类）；新书速递 `/douban/book/latest/science|business|history|fiction|art|...`。

YouTube / Bilibili 视频默认过滤低于 10 分钟的内容，可在 `config.toml` 中调整：

```toml
[filters]
min_video_duration_minutes = 10
```

如果源站无法提供真实时长，则按未知时长保留，不会误删。

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

Bilibili 默认读取 `RSSHUB_BASE_URL` 指向的自建 RSSHub。配置文件中的 `$RSSHUB_BASE_URL` 会在运行时展开：

```toml
[[creators]]
name = "UP 主名称"
platform = "bilibili"
id = "主页 UID"
url = "https://space.bilibili.com/UID"
feed_url = "$RSSHUB_BASE_URL/bilibili/user/video/UID?key=$RSSHUB_ACCESS_KEY"
enabled = true
```

GitHub 托管的 runner 无法访问 QNAP 内网地址。推荐在 QNAP 上安装 GitHub Actions self-hosted runner，让周报和 RSSHub 在同一内网运行；或者给 RSSHub 配置受认证保护的 HTTPS 公网入口。不要直接将 `1200` 端口暴露到公网。

### QNAP 上部署 RSSHub

仓库提供 `deploy/rsshub/docker-compose.yml`。先将该目录复制到 QNAP 的持久化目录（例如 `/share/CACHEDEV1_DATA/docker/rsshub`），再在 QNAP Container Station 的 Compose 项目中启动。服务只绑定 QNAP 的 LAN 地址和端口 `1200`，包含 Redis 缓存和 Chromium 支持。

启动后先在局域网验证：

```text
http://QNAP_IP:1200/healthz
http://QNAP_IP:1200/bilibili/user/video/163682133
```

然后在周报运行环境中设置：

```text
RSSHUB_BASE_URL=http://QNAP_IP:1200
```

如果 Bilibili 路由返回 `412` 或 `-352 风控校验失败`，需要在 QNAP 的 RSSHub 目录创建 `.env`（可参考 `.env.example`），加入你自己 Bilibili 账号的完整浏览器 Cookie：

```text
BILIBILI_COOKIE_data1=这里填写完整 Cookie 字符串
```

Cookie 只保存在 QNAP，不要提交到 Git 或发送到聊天中。保存后执行 `docker compose up -d` 重新创建 RSSHub 容器，再访问上面的两个路由验证。RSSHub 的 Bilibili 配置文档说明了 `BILIBILI_COOKIE_*` 的用途和获取方式。

RSSHub 镜像版本应在升级前固定并保留旧镜像；Compose 文件中的版本是经过部署时确认的日期标签，不建议直接改为 `latest`。

播客 RSS 一般不提供统一播放量和评论数，因此报告不会把最新单集包装成热度排名。

## 环境变量

本地填写 `.env`，不要提交该文件：

| 变量 | 是否必需 | 用途 |
|---|---:|---|
| `YOUTUBE_API_KEY` | 使用 YouTube 时 | Google Cloud 中启用 YouTube Data API v3 后创建 |
| `OPENAI_API_KEY` | AI 二选一 | DeepSeek 失败后的回退服务 |
| `DEEPSEEK_API_KEY` | AI 二选一 | 首选 AI 服务 |
| `OPENAI_MODEL` | 否 | 覆盖 `config.toml` 的 OpenAI 模型 |
| `DEEPSEEK_MODEL` | 否 | 覆盖 `config.toml` 的 DeepSeek 模型 |
| `SMTP_USER` | 发送邮件时 | Gmail 完整邮箱地址 |
| `SMTP_PASSWORD` | 发送邮件时 | Gmail 两步验证生成的应用专用密码，不是登录密码 |
| `SMTP_FROM` | 否 | 发件人，默认等于 `SMTP_USER` |
| `EMAIL_RECIPIENTS` | 否 | 覆盖 TOML 收件人，多个地址用英文逗号分隔 |
| `RSSHUB_BASE_URL` | RSSHub 来源必需 | QNAP 自建 RSSHub 地址，例如 `https://rsshub.example.com:10443` |
| `RSSHUB_ACCESS_KEY` | RSSHub 必需 | RSSHub 访问密钥；只放在 GitHub Secrets / QNAP `.env` |

默认模型为 `deepseek-chat` 和 `gpt-5-mini`。如果 DeepSeek 不可用，程序才尝试 OpenAI；两个服务都不可用时保留基础数据报告。

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
- `RSSHUB_BASE_URL`，QNAP RSSHub 地址，例如 `http://192.168.100.172:1200`；仅适用于能访问 QNAP 内网的 self-hosted runner
- `RSSHUB_ACCESS_KEY`（Secret），RSSHub 的访问密钥；公网 RSSHub 必须配置
- `SMTP_FROM`（可选）
- `OPENAI_MODEL`（可选）
- `DEEPSEEK_MODEL`（可选）

进入 `Actions → weekly-content-report → Run workflow` 可手动验证。建议第一次选择 `sample=true`、`send_email=true`，先验证排版和 Gmail；第二次使用在线数据。定时表达式使用 UTC：`0 21 * * 1,4`，对应上海时间每周二、周五 05:00。

## 测试与限制

```bash
python -m unittest discover -s tests -v
```

- 公开播放量和评论数是报告生成时快照，不代表历史时点值。
- YouTube API 有每日配额；当前每个频道最多读取最近 50 条上传记录。
- Bilibili 的公开接口容易出现 403；当前通过 QNAP 自建 RSSHub 获取，并以缓存保证单源失败不拖垮整期。
- 报告中的 AI 导读只依据采集到的标题、简介和指标，不等同于完整观看/收听后的内容总结。
