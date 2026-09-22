/**
 * AI智能选基 - 火山方舟 API 代理（Cloudflare Workers）
 *
 * 用途：GitHub Pages 等静态托管无法直接调用方舟 API（CORS + key 暴露），
 * 通过本 Worker 代理后，前端把 ARK_PROXY_URL 指向本 Worker 地址即可恢复 AI 功能。
 *
 * 部署方式：
 *   1. 登录 Cloudflare Dashboard → Workers & Pages → Create a Service
 *   2. 粘贴本代码，添加环境变量 ARK_API_KEY = 你的方舟 API Key
 *   3. 发布后得到 Worker URL，例如 https://ai-fund-ark-proxy.xxx.workers.dev
 *   4. 修改 index.html 中 const ARK_PROXY_URL = 'https://ai-fund-ark-proxy.xxx.workers.dev'
 *
 * 安全提示：不要把方舟 Key 写在本文件里，务必使用 Worker 环境变量。
 */

const ARK_URL = 'https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions';

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin || '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400'
  };
}

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin') || '';

    // 处理 CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
      });
    }

    const apiKey = env.ARK_API_KEY;
    if (!apiKey) {
      return new Response(JSON.stringify({ error: 'ARK_API_KEY not configured' }), {
        status: 500,
        headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
      });
    }

    try {
      const body = await request.text();
      const resp = await fetch(ARK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body
      });

      // 透传响应（保留 streaming 能力）
      const headers = new Headers(resp.headers);
      Object.entries(corsHeaders(origin)).forEach(([k, v]) => headers.set(k, v));
      return new Response(resp.body, { status: resp.status, headers });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message || 'Proxy error' }), {
        status: 502,
        headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' }
      });
    }
  }
};
