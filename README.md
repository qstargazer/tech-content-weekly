# Tech Content Weekly · 认知漫游周报

自动汇总 Bilibili、YouTube、播客/小宇宙、微信公众号与豆瓣新书速递的新内容，生成深绿色、适合 PC 与手机阅读的 HTML/Markdown 周报，并可通过 Gmail 自动发送。

## v0.3 能力

- YouTube 使用官方 Data API v3，采集上传时间、时长、播放量和评论数。
- 播客使用公开 RSS/Atom；Bilibili 使用 QNAP 自建 RSSHub，避免依赖容易出现 403 的第三方公共实例。
- 豆瓣读书使用自建 RSSHub 的新书速递榜单，展示评分。
- 微信公众号通过自建 RSSHub 的新榜路由监视（可在 config.toml 的 `wechat` 平台 creator 中启用）。微信公众号没有官方 RSS，需在 RSSHub 侧配置 `NEWRANK_COOKIE`，并接受偶发风控或延迟。
- 展示本周新内容；视频按公开播放量统计最近 30 天 Top 3，播客按时间展示最近 3 期。
- 每个创作者单独容错：失败时读取该创作者最近缓存并在报告中标注，不影响其他来源。
- 可选 AI 导读：DeepSeek 优先，失败时回退 OpenAI；OpenAI 额度不足只写入 Actions 日志，不在周报中展示。
- 场景分类推荐：将本周内容分为「通勤 / 碎片时间」与「需要专门时间深入研究」两类并给出理由，附本周最值得投入的一条。AI 可用时由模型分类，否则使用内置规则兜底。
- Gmail SMTP 支持多个收件人；GitHub Actions 每周二、周五 04:24（Asia/Shanghai）运行，也可手动触发。

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

- Bilibili：9 个账号（包括“opus精译”“MUSI的运动日记 · 骑行路线”和账号 349169140，详见 config.toml）
- YouTube：3Blue1Brown（YouTube）、小岛浪吹、初日医学 - 宋晏仁医师 x Cofit、和之梦 - 官方频道；分别提供英文科普、中文内容、健康内容和中日纪录片内容
- 小宇宙：Huberman Lab、张小珺商业访谈录、津津乐道、家庭教育圆桌谈、天才捕手FM、沈奕斐的播客，以及已有的其他订阅
- 豆瓣读书：科学新知、商业经管、历史文化、社会纪实新书速递

豆瓣新书速递走自建 RSSHub 的 `douban` 路由，榜单条目没有独立发布时间，程序自动以频道更新时间归类到本周：

```toml
[[creators]]
name = "豆瓣新书速递 · 科学新知"
platform = "douban"
id = "douban-book-latest-science"
url = "https://book.douban.com/latest"
feed_url = "$RSSHUB_BASE_URL/douban/book/latest/science?key=$RSSHUB_ACCESS_KEY"
enabled = true
```

可选新书速递：`/douban/book/latest/science|business|history|fiction|art|...`。

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
| `NEWRANK_COOKIE` | 监视微信公众号时 | 仅放在 QNAP RSSHub 的 `.env`，用于新榜微信公众号路由 |

默认模型为 `deepseek-chat` 和 `gpt-5-mini`。如果 DeepSeek 不可用，程序才尝试 OpenAI；两个服务都不可用时保留基础数据报告。

## GitHub Actions 配置

仓库 `Settings → Secrets and variables → Actions` 中配置：

Secrets（敏感值）：

- `YOUTUBE_API_KEY`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `RSSHUB_ACCESS_KEY`

Variables（普通配置）：

- `EMAIL_RECIPIENTS`，例如 `stargazerq@foxmail.com,871517518@qq.com`
- `RSSHUB_BASE_URL`，QNAP RSSHub 地址，例如 `http://192.168.100.172:1200`；仅适用于能访问 QNAP 内网的 self-hosted runner
- `SMTP_FROM`（可选）
- `OPENAI_MODEL`（可选）
- `DEEPSEEK_MODEL`（可选）

进入 `Actions → weekly-content-report → Run workflow` 可手动验证。建议第一次选择 `sample=true`、`send_email=true`，先验证排版和 Gmail；第二次使用在线数据。当前定时表达式使用 UTC：`24 20 * * 1,4`，对应上海时间每周二、周五 04:24。工作流当前运行在 GitHub-hosted `ubuntu-latest`；若使用 QNAP 内网 RSSHub，需要改用能访问 QNAP 的 self-hosted runner，或提供受保护的公网 RSSHub 地址。

### 配置微信公众号

微信公众号没有官方 RSS。本项目使用 RSSHub 的新榜路由 `/newrank/wechat/:wxid` 获取公众号文章列表，再尝试补全文章正文。该路由要求登录新榜（`newrank.cn`）后的 Cookie；Cookie 会过期，也可能因新榜或微信反爬策略变化而暂时失效。

#### 获取 `NEWRANK_COOKIE`

建议使用 Chrome 或 Edge 桌面浏览器，并在自己的电脑上完成以下操作：

1. 打开 `https://www.newrank.cn/`，登录新榜账号。账号不需要提交给本仓库，但必须能够访问公众号数据页面。
2. 登录成功后打开任意新榜页面，按 `F12` 打开开发者工具。
3. 切换到 `Application`（应用）选项卡；如果看不到，点击 `»` 展开更多选项。
4. 左侧展开 `Storage → Cookies → https://www.newrank.cn`。
5. 找到名称为 `token` 的 Cookie，复制它的 `Value`。RSSHub 官方配置说明中，`token` 是必要部分，其他 Cookie 字段可以不复制。
6. 如果 Cookie 列表中没有 `token`，切换到 `Network`（网络），刷新页面，打开一个发往 `www.newrank.cn` 的请求，在 `Request Headers` 中找到 `Cookie`，复制其中的 `token=...` 部分。不要复制或公开完整浏览器 Cookie。

`NEWRANK_COOKIE` 的值应类似下面这样，只保留 `token`，不要包含反引号：

```text
token=这里替换为新榜登录后的token值
```

#### 写入 QNAP RSSHub

1. 在 QNAP 上进入 RSSHub Compose 目录。该目录中应有 `docker-compose.yml` 和 `.env`；没有 `.env` 时复制仓库提供的 `deploy/rsshub/.env.example`。
2. 编辑 `.env`，加入刚才复制的值：

```dotenv
NEWRANK_COOKIE=token=这里替换为新榜登录后的token值
```

3. 确认 `.env` 仅保存在 QNAP，不要提交到 Git，也不要放进 GitHub Actions 的 Secrets 或公开聊天。
4. 在该 Compose 目录重新创建 RSSHub 容器，使环境变量生效：

```bash
docker compose up -d
```

5. 在能访问 QNAP 的电脑上验证公众号路由。将 `QNAP_IP`、访问密钥和账号标识（示例 `NeuralTalk`）替换为实际值：

```text
http://QNAP_IP:1200/newrank/wechat/NeuralTalk?key=RSSHUB_ACCESS_KEY
```

浏览器应返回 XML/RSS，且至少能看到文章标题、链接和发布时间。若返回 `ConfigNotFoundError`，说明容器没有读到 `NEWRANK_COOKIE`；若只有标题没有正文，通常是 Cookie 失效、正文补全被微信拦截，或当前 RSSHub 镜像版本与新榜接口不兼容。

#### 常见问题

- `NEWRANK_COOKIE` 不是微信公众号文章链接，也不是 RSSHub 的 `RSSHUB_ACCESS_KEY`，两者用途不同。
- Cookie 中的 `token` 过期后，重新从新榜浏览器会话获取并替换 QNAP `.env`，然后再次执行 `docker compose up -d`。
- 路由参数是新榜账号标识，不一定等于公众号显示名称，应以新榜页面 URL 中的 `account` 参数为准，并同步修改 `config.toml` 中的 `feed_url`。
- 如果只需要标题和链接，RSSHub 可以正常返回列表但正文可能为空；周报仍会收录文章，但 AI 导读信息会较少。

### 监视其他微信公众号

可以。每个公众号增加一个 `[[creators]]` 配置块即可，但每个账号都必须先能被新榜识别，并使用同一个有效的 `NEWRANK_COOKIE`：

```toml
[[creators]]
name = "其他公众号名称"
platform = "wechat"
id = "other-account"
url = "https://mp.weixin.qq.com/s/该公众号的一篇文章链接"
feed_url = "$RSSHUB_BASE_URL/newrank/wechat/新榜账号标识?key=$RSSHUB_ACCESS_KEY"
enabled = true
```

获取其他公众号的账号标识时，可以先将该公众号的一篇文章提交到新榜的公众号搜索或账号页面，查看页面 URL 中的 `account` 值。RSSHub 路由的参数说明是“微信号；若微信号与新榜信息不一致，以新榜为准”。配置后先直接访问对应 RSS URL 验证，再运行周报。

需要注意：

- 可以添加多个公众号，程序会并行采集，每个来源独立缓存和容错。
- 不建议为每个公众号配置一套 Cookie；通常一个新榜登录 Cookie 可以访问多个账号，但具体权限以新榜账号为准。
- 新榜和微信都存在反爬限制，不应高频刷新；周报按现有计划运行即可。
- 公众号文章可能删除、限制访问或延迟进入新榜，程序无法保证实时性和永久可读性。
- 也可以使用其他能输出 RSS/Atom 的公众号服务，只需将其 RSS 地址填入 `feed_url`，`platform` 仍使用 `wechat`；不要把第三方服务的密码或私有 Token 直接写进 `config.toml`。

## 测试与限制

```bash
python -m unittest discover -s tests -v
```

- 公开播放量和评论数是报告生成时快照，不代表历史时点值。
- YouTube API 有每日配额；当前每个频道最多读取最近 50 条上传记录。
- Bilibili 的公开接口容易出现 403；当前通过 QNAP 自建 RSSHub 获取，并以缓存保证单源失败不拖垮整期。
- 报告中的 AI 导读只依据采集到的标题、简介和指标，不等同于完整观看/收听后的内容总结。
