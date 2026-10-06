import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = join(__dirname, 'fund-pool.js');

// 在 Node 里模拟 window，执行 fund-pool.js 拿到数组
globalThis.window = {};
const code = readFileSync(src, 'utf-8');
// fund-pool.js 里只有 window.FUND_POOL = [...]; 的赋值，直接 eval 即可
eval(code.replace(/window\./g, 'globalThis.window.'));
const funds = globalThis.window.FUND_POOL;

const BASE_FIELDS = new Set([
  'fundCode','fundName','fundFullName','fundTypeTag',
  'riskLevelNum','riskLevel','fundScale','managementFee','purchaseFee',
  'reportDate','matchTags','performance','industryConfig',
  'topIndustryCode','topHoldingStock'
]);
const DETAIL_FIELDS = new Set(['valuation','riskFactors','topHoldings']);

const base = [];
const detail = {};
for (const f of funds) {
  const b = {};
  const d = {};
  for (const [k, v] of Object.entries(f)) {
    if (BASE_FIELDS.has(k)) b[k] = v;
    else if (DETAIL_FIELDS.has(k)) d[k] = v;
  }
  base.push(b);
  detail[f.fundCode] = d;
}

function save(path, comment, varName, data) {
  const json = JSON.stringify(data);
  writeFileSync(path, `// 由 split_fund_pool.mjs 生成 — ${comment}\nwindow.${varName} = ${json};\n`, 'utf-8');
}

const basePath = join(__dirname, 'fund-pool-base.js');
const detailPath = join(__dirname, 'fund-pool-detail.js');

save(basePath, '首页基础字段（含 industryConfig 供 AI 主题过滤）', 'FUND_POOL_BASE', base);
save(detailPath, '详情页按需字段（重仓股/估值/风险因子）', 'FUND_POOL_DETAIL', detail);

console.log(`源文件: ${src} (${(readFileSync(src).length / 1024).toFixed(1)} KB)`);
console.log(`base  : ${basePath} (${(readFileSync(basePath).length / 1024).toFixed(1)} KB)`);
console.log(`detail: ${detailPath} (${(readFileSync(detailPath).length / 1024).toFixed(1)} KB)`);
console.log(`基金数: ${base.length}`);
