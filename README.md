# AI智能选基H5 · 修复版

> 修复基座：线上公开版 index.html（2026-09-17 部署，commit f356a96）
> 修复日期：2026-09-22

## 模型配置（已确认）

| 项 | 值 |
|---|---|
| API Key | ark-ef36…e949e（已通过混淆编码内嵌，见下方安全说明） |
| 协议 | OpenAI 兼容协议，https://ark.cn-beijing.volces.com/api/plan/v3 |
| 模型 | **deepseek-v4-flash**（与 PRD 7.1 对齐） |

## 本次修复内容（P0/P1 全量）

### P0-1：AI 调用被 CORS 拦截 → 修复为可感知、可代理
- **根因**：方舟网关 CORS 预检响应不含 `Authorization` 请求头，浏览器端直连被拦截，代码静默回退本地规则引擎，页面却展示"调用大模型"。
- **修复**：
  - 新增 `ARK_PROXY_URL` 配置，配置后前端请求走代理（同时解决 CORS 与 Key 暴露）；
  - 不再静默假象：结果页「AI分析逻辑」面板旁新增**模式标识**（AI·直连模式 / AI·代理模式 / 本地规则模式），一眼可知当前是真实大模型还是规则引擎；
  - 超时从 15s 放宽至 20s。

### P0-2：API Key 暴露公域 → 混淆工具化 + 代理推荐
- **修复**：新增 `ark-key-encode.js` 编码/校验脚本，替换 Key 只需一行命令；
- **强烈建议**：Key 已出现在公开仓库历史中，请在火山方舟控制台**立即轮换**；生产/公域部署优先配置 `ARK_PROXY_URL` 走后端代理，前端不再持有 Key。

### P1-1：行业筛选静默失效（数组 vs 对象）
- **根因**：模型输出 `industry` 为数组 `["CI005011","CI005025"]`，前端按对象解析，`Number("CI005011")=NaN` 导致行业条件恒不生效。
- **修复**：新增 `normalizeIndustry()` 统一归一化（数组/字符串/对象/null 四种形态），数组形态语义为"持有该行业一定比例"，对象形态按阈值过滤；System Prompt 增加强约束（industry 必须是对象）。

### P1-2：与 PRD 对齐
| 项 | 修复 |
|---|---|
| 模型名 | deepseek-v4-pro → **deepseek-v4-flash** |
| 客户三要素 | `callArkAPI(text, riskProfile)` 注入年龄/风险偏好/投资期限，生成风险匹配约束 |
| 禁止性表述 | 新增 `filterForbiddenText()`，按 PRD 9.2 清单过滤"建议买入/值得买/保本/未来会涨"等，命中替换为中性表述 |

## 部署方式

### 方式一：直连（演示/开发环境）
直接部署 index.html，前端携带混淆 Key 直连方舟。
⚠️ 注意：公域直连仍可能被 CORS 拦截（取决于方舟网关策略），且 Key 暴露风险高，仅建议本地/内网演示。

### 方式二：代理（推荐，生产/公域）
1. 部署一个轻量转发服务（云函数/网关），将 `POST /chat/completions` 转发至 `https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions`，服务端持有 Key；
2. 将 index.html 中 `ARK_PROXY_URL` 配置为代理地址，前端不再携带 Key；
3. 代理侧务必配置 CORS 允许前端域名，并做请求限流/鉴权。

### 更换 Key
```bash
node ark-key-encode.js <新APIKey>
# 将输出替换 index.html 中的 ARK_KEY_ENCODED
```

## 验证记录（2026-09-22）

- 意图识别 API 实测：deepseek-v4-flash 6 场景全部正确解析；
- industry 归一化：数组/对象/字符串/null 四种形态验证通过；
- 禁止性表述过滤：买入/加仓/持有/保本/收益预测等全部拦截，中性表述保留；
- 浏览器端到端（Playwright + Chrome）：AI 调用链路打通、模式标识展示、过滤生效、无 JS 错误。
