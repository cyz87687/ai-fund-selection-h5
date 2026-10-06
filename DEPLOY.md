# AI 智能选基 H5 — 剩余未闭环事项部署说明

## 一、Cloudflare Worker 代理（P0，线上 AI 生效必需）

当前 `index.html` 中 `ARK_PROXY_URL` 为空，GitHub Pages 仍为本地规则引擎。

### 前提
- 已注册 Cloudflare 账号
- 已安装 Node.js + npm

### 步骤

```bash
# 1. 安装 wrangler
npm install -g wrangler

# 2. 登录 Cloudflare
npx wrangler login

# 3. 设置方舟 API Key（不会写入仓库）
npx wrangler secret put ARK_API_KEY
# 按提示粘贴你的火山方舟 API Key

# 4. 部署
npx wrangler deploy

# 5. 部署成功后会得到 Worker URL，例如：
#    https://ai-fund-ark-proxy.xxx.workers.dev
```

### 回填前端

把 `index.html` 中：

```js
const ARK_PROXY_URL = '';
```

改为：

```js
const ARK_PROXY_URL = 'https://ai-fund-ark-proxy.xxx.workers.dev';
```

然后重新提交 `index.html` 到 GitHub Pages。

---

## 二、iFinD 估值数据补全（P0，需要密钥）

当前估值字段（PE/PB/ROE/ROA 等）79.1% 缺失，模块已优雅隐藏。ttfund 不提供这些字段，需 iFinD `fund` 服务补全。

### 方案

在 `build_fund_pool.py` 中增加 iFinD 数据源调用：

```python
# 示例（需替换为你的 iFinD SDK/HTTP 调用）
import ifind  # 或调用 iFinD API

for code in fund_codes:
    # 取最新报告期估值指标
    pe = ifind.get_fund_pe(code)
    pb = ifind.get_fund_pb(code)
    roe = ifind.get_fund_roe(code)
    ...
```

### 需要的信息

- iFinD 账号/密码，或
- iFinD API Key / Token

拿到后我可以把 `build_fund_pool.py` 接上 iFinD，重新生成 `fund-pool.js`/`fund-pool-base.js`/`fund-pool-detail.js`。

---

## 三、本次已完成的剩余项

| 事项 | 状态 | 文件/说明 |
|---|---|---|
| KYC 问卷进入时不裸弹 | 已完成 | `index.html` 加 `v-cloak` + CSS |
| fund-pool 分片加载 | 已完成 | `fund-pool-base.js` (479KB) + `fund-pool-detail.js` (476KB)，详情懒加载 |
| Vue/ECharts CDN 本地化 | 已完成 | `assets/vue.global.prod.min.js` + `assets/echarts.min.js`，失败自动回退 CDN |
