#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构 AI智能选基H5 基金数据池（2026-09-22 更新版）

数据策略（按用户要求）：
  - 底表：全部数据.xlsx（工作表"全部基金"，657只）→ 决定基金全集与核心字段
      代码/名称/风险等级/证监会分类/规模/申购费率/近一年收益率/最大回撤/第一大重仓股
  - 其余字段（波动率/夏普/行业配置/估值/风险归因等）用旧 CSV 按代码关联补充（best-effort，缺失置空）

量纲约定（与 index.html 前端显示一致，前端对 RETURNRATE/MAX_DRAWDOWN 等 ×100 显示）：
  - 近一年收益率(%)、今年最大回撤(%)：xlsx 为百分比，需 ÷100 转小数存储
  - 波动率/夏普/估值/风险因子：沿用旧 CSV 原始尺度
"""
import csv, json, re, math, os
import openpyxl

BASE = '/Users/yzreal/Desktop/ai选基'
OUT = '/Users/yzreal/WorkBuddy/2026-09-22-09-21-20/交付物/ai-fund-selection-h5-fixed'

INDUSTRY_NAMES = {
    'CI005001':'石油石化','CI005002':'煤炭','CI005003':'有色金属','CI005004':'电力及公用事业',
    'CI005005':'钢铁','CI005006':'基础化工','CI005007':'建筑','CI005008':'建材','CI005009':'轻工制造',
    'CI005010':'机械','CI005011':'电力设备及新能源','CI005012':'国防军工','CI005013':'汽车',
    'CI005014':'商贸零售','CI005015':'消费者服务','CI005016':'家电','CI005017':'纺织服装',
    'CI005018':'医药','CI005019':'食品饮料','CI005020':'农林牧渔','CI005021':'银行',
    'CI005022':'非银行金融','CI005023':'房地产','CI005024':'交通运输','CI005025':'电子',
    'CI005026':'通信','CI005027':'计算机','CI005028':'传媒','CI005029':'综合','CI005030':'综合金融',
}

def norm(code):
    """归一化基金代码：去 .OF/.SH/.SZ 后缀，转大写，便于跨表关联"""
    return re.sub(r'\.(OF|SH|SZ)$', '', str(code).strip()).upper()

def fnum(v):
    try:
        if v in ('', None): return None
        return float(v)
    except (ValueError, TypeError):
        return None

def load_latest(csvname, code_key, date_key=None):
    """按代码读取 CSV，同一代码取日期最大的一条（无日期则取最后一条）"""
    d = {}
    with open(os.path.join(BASE, csvname), encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            code = norm(row.get(code_key))
            if not code: continue
            if code not in d:
                d[code] = row
            elif date_key and row.get(date_key) and d[code].get(date_key):
                try:
                    if str(row[date_key]) >= str(d[code][date_key]):
                        d[code] = row
                except Exception:
                    d[code] = row
            else:
                d[code] = row
    return d

# ---------- 1. 底表（xlsx 全部基金） ----------
wb = openpyxl.load_workbook(os.path.join(BASE, '全部数据.xlsx'), read_only=True, data_only=True)
ws = wb['全部基金']
rows = list(ws.iter_rows(values_only=True))
header = rows[0]
basic = {}
for r in rows[1:]:
    code = str(r[0]).strip() if r[0] else None
    if not code: continue
    name = str(r[1]).strip() if r[1] else code
    risk = str(r[2]) if r[2] is not None else ''
    ftype = str(r[3]) if r[3] else ''
    scale = fnum(r[4])           # 元
    purch = fnum(r[5])           # 最高申购费率 %
    ret1y = fnum(r[6])           # 近一年收益率 %（需 ÷100）
    mdd = fnum(r[7])             # 今年最大回撤 %（需 ÷100）
    top_hold = str(r[8]).strip() if r[8] else ''  # 第一大重仓股（名称）

    m = re.search(r'R([1-5])', risk)
    risk_num = int(m.group(1)) if m else 5  # 缺风险等级按最高保守处理

    ft = ftype
    if '混合' in ft: tag = '混合型'
    elif '债券' in ft or '短期理财' in ft: tag = '债券型'
    elif '指数' in ft or ('股票' in ft and ('ETF' in name or '指数' in name)): tag = '指数型'
    elif '股票' in ft: tag = '股票型'
    elif '货币' in ft: tag = '货币型'
    elif 'QDII' in ft: tag = 'QDII型'
    elif 'FOF' in ft or '基金中基金' in ft: tag = 'FOF型'
    else: tag = '混合型'
    if tag not in ('指数型', '债券型', '货币型') and re.search(r'ETF|指数|LOF', name):
        tag = '指数型'

    basic[code] = {
        'fundCode': code,
        'fundName': name,
        'riskLevelNum': risk_num,
        'riskLevel': f'R{risk_num}',
        'fundTypeTag': tag,
        'fundScale': (scale / 1e8) if scale is not None else None,  # 元→亿
        'purchaseFee': purch,
        'RETURNRATE': (ret1y / 100.0) if ret1y is not None else None,   # %→小数
        'MAX_DRAWDOWN': (mdd / 100.0) if mdd is not None else None,     # %→小数
        'topHoldingStock': top_hold,
    }
print(f'底表(全部基金): {len(basic)} 只')

# ---------- 2. 旧 CSV 补充（best-effort） ----------
perf = load_latest('fof_index_value_v2_test_202609141659.csv', 'J_WINDCODE', 'TRADE_DT')
ind = load_latest('fof_fund_industry_config_202609141630.csv', 'HB_FUND_CODE', 'REPORT_DATE')
val = load_latest('fof_fund_multi_config_info_202609141702.csv', 'HB_FUND_CODE', 'END_DATE')
risk = load_latest('fof_multi_attr_riskmodel_202609141700.csv', 'HB_FUND_CODE', 'END_DATE')
print(f'旧CSV可用: perf={len(perf)} ind={len(ind)} val={len(val)} risk={len(risk)}')

# ---------- 3. 汇总构建基金池（底表为全集） ----------
pool = []
miss_perf = miss_ind = miss_val = miss_risk = 0
for code, b in basic.items():
    cn = norm(code)
    p = perf.get(cn)
    ic_row = ind.get(cn)
    v_row = val.get(cn)
    r_row = risk.get(cn)

    # 绩效补充（RETURNRATE/MAX_DRAWDOWN 已由底表提供，这里补其余指标）
    perf_obj = {
        'RETURNRATE': b['RETURNRATE'],
        'MAX_DRAWDOWN': b['MAX_DRAWDOWN'],
        'ANNUALRETURN_RATE': fnum(p['ANNUALRETURN_RATE']) if p else None,
        'SHARP': fnum(p['SHARP']) if p else None,
        'VOL': fnum(p['VOL']) if p else None,
        'KARMA': fnum(p['KARMA']) if p else None,
        'INFO_RATIO': fnum(p['INFO_RATIO']) if p else None,
        'BETA': fnum(p['BETA']) if p else None,
        'SORTINO': fnum(p['SORTINO']) if p else None,
        'VAR': fnum(p['VAR']) if p else None,
        'TREYNOR': fnum(p['TREYNOR']) if p else None,
        'JASON': fnum(p['JASON']) if p else None,
        'MSQUARE': fnum(p['MSQUARE']) if p else None,
        'MAX_DRAWDOWN_RECOVER': fnum(p['MAX_DRAWDOWN_RECOVER']) if p else None,
        'reportDate': (p['TRADE_DT'] if p else None),
    }
    if p is None: miss_perf += 1

    # 行业配置
    ic = {}
    if ic_row:
        for i in range(1, 31):
            k = f'CI005{i:03d}'
            fv = fnum(ic_row.get(k))
            if fv and fv > 0: ic[k] = fv
        total = sum(ic.values())
        if total > 0 and abs(total - 1.0) > 0.05:
            ic = {k: x / total for k, x in ic.items()}
    else:
        miss_ind += 1
    top_ind = max(ic, key=ic.get) if ic else None

    # 估值
    val_obj = {}
    if v_row:
        for k in ['PE', 'PB', 'ROE', 'ROA', 'GRONP', 'GROR', 'DIVIDEND', 'MKT', 'CHANGE_RATE']:
            val_obj[k] = fnum(v_row.get(k))
    else:
        miss_val += 1

    # 风险归因
    rf_obj = {}
    if r_row:
        for k in ['BETA', 'EARNING', 'LEVERAGE', 'LIQUIDITY', 'MOMENTUM', 'VALUE', 'VOLATILITY', 'GROWTH', 'SIZE']:
            rf_obj[k] = fnum(r_row.get(k))
    else:
        miss_risk += 1

    # 标签
    tags = [b['riskLevel'], b['fundTypeTag']]
    if top_ind:
        tags.append(INDUSTRY_NAMES.get(top_ind, top_ind))
    if b['RETURNRATE'] is not None and b['RETURNRATE'] > 0.1: tags.append('高收益')
    if perf_obj['SHARP'] is not None and perf_obj['SHARP'] > 1.0: tags.append('夏普优秀')
    if perf_obj['VOL'] is not None and perf_obj['VOL'] < 0.05: tags.append('低波动')
    if b['MAX_DRAWDOWN'] is not None and abs(b['MAX_DRAWDOWN']) < 0.05: tags.append('低回撤')

    fund = {
        'fundCode': b['fundCode'],
        'fundName': b['fundName'],
        'fundFullName': b['fundName'],
        'fundTypeTag': b['fundTypeTag'],
        'riskLevelNum': b['riskLevelNum'],
        'riskLevel': b['riskLevel'],
        'fundScale': b['fundScale'],
        'managementFee': b['purchaseFee'],
        'purchaseFee': b['purchaseFee'],
        'reportDate': perf_obj['reportDate'],
        'matchTags': tags,
        'performance': perf_obj,
        'industryConfig': ic,
        'topIndustry': INDUSTRY_NAMES.get(top_ind, top_ind) if top_ind else '',
        'valuation': val_obj,
        'riskFactors': rf_obj,
        'topIndustryCode': top_ind,
        'topHoldingStock': b['topHoldingStock'],
    }
    pool.append(fund)

print(f'\n基金池构建: {len(pool)} 只（底表全集）')
print(f'补充缺失: 绩效其他指标 {miss_perf} / 行业 {miss_ind} / 估值 {miss_val} / 风险 {miss_risk}')

# ---------- 4. 输出 JS ----------
def js_val(v, nd=4):
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v): return 'null'
        return repr(round(v, nd))
    if isinstance(v, int): return str(v)
    if isinstance(v, str): return json.dumps(v, ensure_ascii=False)
    raise TypeError(type(v))

lines = ['// 由 build_fund_pool.py 生成 — 底表:全部数据.xlsx(657只) + 旧CSV补充(2026-09-22)',
         '// 全局变量 window.FUND_POOL，供 index.html 加载后赋值给 MOCK_FUNDS',
         'window.FUND_POOL = [']
for x in pool:
    perf_o = '{' + ','.join(f"{k}:{js_val(x['performance'].get(k),4)}" for k in
        ['RETURNRATE','SHARP','VOL','MAX_DRAWDOWN','ANNUALRETURN_RATE','KARMA','INFO_RATIO','BETA','SORTINO','VAR','TREYNOR','JASON','MSQUARE','MAX_DRAWDOWN_RECOVER']) + '}'
    ic = {k: round(v, 4) for k, v in x['industryConfig'].items() if v >= 0.005}
    ic_o = '{' + ','.join(f"{k}:{js_val(v,4)}" for k, v in sorted(ic.items())) + '}' if ic else '{}'
    val_o = '{' + ','.join(f"{k}:{js_val(x['valuation'].get(k),2)}" for k in
        ['PE','PB','ROE','ROA','GRONP','GROR','DIVIDEND','MKT','CHANGE_RATE']) + '}'
    rf_o = '{' + ','.join(f"{k}:{js_val(x['riskFactors'].get(k),4)}" for k in
        ['BETA','EARNING','LEVERAGE','LIQUIDITY','MOMENTUM','VALUE','VOLATILITY','GROWTH','SIZE']) + '}'
    tags_o = '[' + ','.join(js_val(t) for t in x['matchTags']) + ']'
    obj = ('{fundCode:' + js_val(x['fundCode']) + ',fundName:' + js_val(x['fundName']) + ',fundFullName:' + js_val(x['fundFullName'])
        + ',fundTypeTag:' + js_val(x['fundTypeTag']) + ',riskLevelNum:' + js_val(x['riskLevelNum']) + ',riskLevel:' + js_val(x['riskLevel'])
        + ',fundScale:' + js_val(x['fundScale'],2) + ',managementFee:' + js_val(x['managementFee'],2) + ',purchaseFee:' + js_val(x['purchaseFee'],2)
        + ',reportDate:' + js_val(x['reportDate']) + ',matchTags:' + tags_o
        + ',performance:' + perf_o + ',industryConfig:' + ic_o + ',valuation:' + val_o + ',riskFactors:' + rf_o
        + ',topIndustryCode:' + js_val(x['topIndustryCode']) + ',topHoldingStock:' + js_val(x['topHoldingStock']) + '}')
    lines.append('  ' + obj + ',')
lines[-1] = lines[-1].rstrip(',')
lines.append('];')
with open(os.path.join(OUT, 'fund-pool.js'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'已输出 fund-pool.js ({os.path.getsize(os.path.join(OUT,"fund-pool.js"))//1024}KB)')
