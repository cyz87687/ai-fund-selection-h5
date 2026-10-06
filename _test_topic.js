const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('index.html', 'utf8');

// 抽取真实 INDUSTRY_MAP
const imStart = html.indexOf('const INDUSTRY_MAP = {');
const imEnd = html.indexOf('};', imStart) + 2;
const imCode = html.slice(imStart, imEnd);

// 抽取真实 genericIntent 函数
const giStart = html.indexOf('function genericIntent(text) {');
const giEnd = html.indexOf('// ============ REAL AI MODEL');
const giCode = html.slice(giStart, giEnd).trim();
// 去掉尾部注释残留
const giClean = giCode.replace(/\/\/ =+.*$/, '').trim();
// 确保以 } 结尾
const lastBrace = giClean.lastIndexOf('}');
const giFinal = giClean.slice(0, lastBrace + 1);

// 加载 fund-pool
const w = {}; w.window = w; vm.createContext(w);
vm.runInContext(fs.readFileSync('fund-pool.js', 'utf8'), w);
const FUND_POOL = w.FUND_POOL;

const ctx = { INDUSTRY_MAP: null, genericIntent: null, MOCK_FUNDS: FUND_POOL, console };
vm.createContext(ctx);
vm.runInContext(imCode + '\n' + giFinal + '\nthis.INDUSTRY_MAP = INDUSTRY_MAP; this.genericIntent = genericIntent;', ctx);

const INDUSTRY_MAP = ctx.INDUSTRY_MAP;
const genericIntent = ctx.genericIntent;

console.log('INDUSTRY_MAP 行业数:', Object.keys(INDUSTRY_MAP).length);

const maxRisk = 3; // 默认 R1-R3 风险画像
const tests = ['重仓存储的基金', '重仓AI的基金', '重仓新能源的基金', '重仓半导体的基金', '重仓医药的基金', '重仓白酒的基金', '重仓电力设备的基金', '主题消费的基金'];
for (const t of tests) {
  const r = genericIntent(t);
  const n = r.filterFn(FUND_POOL, maxRisk).length;
  console.log(`[本地规则] "${t}" -> ${n} 只  (sortBy=${r.sortBy})`);
}

// 单独验证 重仓存储 的命中行业分布
const r = genericIntent('重仓存储的基金');
const hits = r.filterFn(FUND_POOL, maxRisk);
const elec = hits.filter(f => (f.industryConfig['CI005025']||0) > 0.08).length;
console.log('\n重仓存储: 命中', hits.length, '只, 其中电子占比>8%:', elec, '只');
if (hits.length) console.log('样本:', hits.slice(0,3).map(f=>f.fundName+'('+(f.industryConfig['CI005025']*100).toFixed(1)+'%电子)'));
