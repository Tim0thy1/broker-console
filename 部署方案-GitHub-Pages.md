# 模拟盘控制台 · GitHub Pages 部署方案

本方案的**核心架构**：纯静态网站（GitHub Pages 托管） + 网页直写 JSON + GitHub Actions 定时同步 + 手机/电脑浏览器访问。数据与界面分离，省 token。

---

## 一、要部署的文件（都在 `broker-console/` 目录）

| 文件 | 作用 |
|---|---|
| `index.html` | 券商风格控制台主页（账户总览/持仓/预测/战绩/画像/资料库） |
| `record.html` | **记录与反思中心**（盘前预测/操作反思/修炼手记，可网页写回 GitHub JSON） |
| `sync_eastmoney.py` | 东财组合同步脚本（拉取实时数据生成 `live-snapshot.json`） |
| `live-snapshot.json` | 实时快照（账户/持仓/调仓），由同步脚本生成 |
| `manifest.json` + `icon-*.png` | PWA 支持，iPhone 可"添加到主屏幕"全屏运行 |
| `.github/workflows/sync-eastmoney.yml` | GitHub Actions 定时同步（默认关闭定时） |

---

## 二、一键部署到 GitHub Pages（手机+电脑都能访问）

### 结果
部署后你获得一个公网网址，例如：
- `https://你的用户名.github.io/broker-console/index.html`
- iPhone（Safari 浏览器）、电脑 Chrome 打开同一网址即可访问，**跨设备数据完全一致**（因为都读 GitHub 仓库里的 JSON）。

### 步骤

**1. 建 GitHub 仓库**
- 登录 GitHub → New repository
- 仓库名建议 `broker-console`，选 **Public**（Private 也可以，但 Pages 有额度限制）
- 不要勾选 "Add a README"（保持空仓库）

**2. 把 broker-console 内容推上去**
```bash
cd "d:\AI\trae work\个人系统\broker-console"
git init
git add .
git commit -m "initial: 模拟盘控制台 + 东财同步"
git branch -M main
git remote add origin https://github.com/你的用户名/broker-console.git
git push -u origin main
```

**3. 开启 GitHub Pages**
- 仓库页 → **Settings** → **Pages**
- Source → 选 **Deploy from a branch** → Branch 选 **main /** → 根目录 `/ ` → Save
- 等 1-2 分钟，出现网址 `https://你的用户名.github.io/broker-console/`

### 手机访问
- iPhone 用 **Safari** 打开网址，点「分享」→「添加到主屏幕」，即可像 App 一样全屏打开（PWA 图标）。
- 电脑 Chrome 直接打开网址。两边数据完全一样。

---

## 三、启用自动同步（可选）

### 1. 手动同步（不依赖 Actions）
本机跑一次脚本，把 `live-snapshot.json` 更新并推送到 GitHub：
```bash
python sync_eastmoney.py --snap-dir .
git add live-snapshot.json
git commit -m "同步"
git push
```
刷新网页即看到最新持仓/资产。

### 2. 定时自动同步（GitHub Actions）
编辑 `.github/workflows/sync-eastmoney.yml`，去掉 `schedule` 块前的注释：
```yaml
on:
  schedule:
    - cron: "0 9,11,13,15 * * 1-5"   # A股工作日 9/11/13/15 点(UTC)
    - cron: "30 15 * * 5"            # 周五收盘后
```
保存并推送后，GitHub 会在这些时间自动拉东财数据并更新快照。也可以到 **Actions** 页手动点 Run。

> 注意：GitHub Actions 访问东财接口在部分网络环境下可能被限流。若失败，退回到"手动同步"。**在没有确认 Actions 能正常拿到东财数据前，不建议启用定时**（这符合你"先不自己跑"的要求）。

---

## 四、record.html 的 Token 配置（网页直写 JSON）

`record.html` 通过 **GitHub Contents API** 把预测/反思/手记直接写回仓库 JSON，这样网页提交无需经过 AI 对话，**极省 token**。

要开启写回，需要一个 **GitHub Personal Access Token**：

1. GitHub → 头像 → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → Generate new token
2. 权限（最小化）：
   - Repository access → 只选 `broker-console` 这一个仓库
   - Permissions → **Contents** → 选 `Read and write`
3. 生成的 token 复制下来

> ⚠️ Token 只显示一次。它存储在**你浏览器 localStorage**（仅你本机，不会上传到别处）。任何人拿到 token 都能改你的仓库，**切勿泄露/提交到代码里**。

**在 record.html 顶部框里填写**：
- 输入 Token → 保存
- 输入 `你的用户名/broker-console` → 保存

配置后状态显示"已连接"。

**Token 直传推荐**：也可在 URL 后加 `#token=xxx` 自动填写并保存（方便手机快速配置）：
```
https://你的用户名.github.io/broker-console/record.html#token=你的token
```

设置页 → 一键清除可随时移除 Token（恢复只读展示）。

---

## 五、数据文件说明

记录与反思页面读写这些 JSON（都在仓库 `data/` 下，首次提交后由页面自动创建）：

| 文件 | 由谁写 | 内容 |
|---|---|---|
| `data/forecast.json` | 网页表单 → GitHub API | 盘前预测历史（方向/依据/预案/情绪 + 收盘评分） |
| `data/reflection.json` | 网页表单 → GitHub API | 操作反思时间线（做了什么/得失/明日注意） |
| `data/journal.json` | AI 定期提炼 → commit | 正式修炼手记（多段，最新置顶） |
| `live-snapshot.json` | sync 脚本 | 东财实时账户/持仓/调仓 |

**工作流**：
1. **日常**：网页上写预测、记反思（不耗 token）
2. **定期**：攒几天草稿/反思 → 让 AI 提炼成正式修炼手记，写进 `journal.json`（每次只改一个 JSON，省 token）
3. **同步**：Actions 或手动跑脚本刷新账户数据 → 网页自动变最新

---

## 六、目录结构（部署后）

```
broker-console/
├── index.html
├── record.html
├── sync_eastmoney.py
├── live-snapshot.json
├── manifest.json
├── icon-192.png
├── icon-512.png
└── .github/workflows/sync-eastmoney.yml  (可选自动同步)
```