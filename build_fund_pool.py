#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构 AI智能选基H5 基金数据池
数据源：
  1. 全部数据.xlsx   — 基金基础信息（代码/名称/风险等级/证监会分类/规模/申购费率）27290只
  2. fof_index_value_v2_test   — 绩效指标 9999只
  3. fof_fund_industry_config  — 30个中信行业配置 16191只
  4. fof_fund_multi_config_info— 估值/换手 6876只
  5. fof_multi_attr_riskmodel  — 风险归因因子 2784只
输出：fund-pool.js（可直接替换 index.html 中 MOCK_FUNDS 数组）
"""
import csv, json, re, collections, math, os

BASE = '/Users/yzreal/Desktop/ai选基'
OUT = '/Users/yzreal/WorkBuddy/2026-09-22-09-21-20/交付物/ai-fund-selection-h5-fixed'

# 30个中信一级行业中文名（来自 fof_columndict）
INDUSTRY_NAMES = {
    'CI005001':'石油石化','CI005002':'煤炭','CI005003':'有色金属','CI005004':'电力及公用事业',
    'CI005005':'钢铁','CI005006':'基础化工','CI005007':'建筑','CI005008':'建材','CI005009':'轻工制造',
    'CI005010':'机械','CI005011':'电力设备及新能源','CI005012':'国防军工','CI005013':'汽车',
    'CI005014':'商贸零售','CI005015':'消费者服务','CI005016':'家电','CI005017':'纺织服装',
    'CI005018':'医药','CI005019':'食品饮料','CI005020':'农林牧渔','CI005021':'银行',
    'CI005022':'非银行金融','CI005023':'房地产','CI005024':'交通运输','CI005025':'电子',
    'CI005026':'通信','CI005027':'计算机','CI005028':'传媒','CI005029':'综合','CI005030':'综合金融',
}

# ---------- 1. 基金基础信息（xlsx） ----------
import openpyxl
wb = openpyxl.load_workbook(os.path.join(BASE, '全部数据.xlsx'), read_only=True)
ws = wb['全部基金']
rows = list(ws.iter_rows(values_only=True))
basic = {}
for r in rows[1:]:
    code, name, risk, ftype, scale, purch_fee = r[0], r[1], r[2], r[3], r[4], r[5]
    if not code: continue
    code = str(code).strip()
    # 风险等级 R1~R5
    risk_num = None
    if risk:
        m = re.search(r'R([1-5])', str(risk))
        if m: risk_num = int(m.group(1))
    # 证监会分类 → 页面 fundTypeTag（债券型/混合型/指数型/股票型/货币型/QDII/FOF/其他）
    ft = str(ftype) if ftype else ''
    if '混合' in ft: tag = '混合型'
    elif '债券' in ft or '短期理财' in ft: tag = '债券型'
    elif '指数' in ft or ('股票' in ft and ('ETF' in str(name) or '指数' in str(name))): tag = '指数型'
    elif '股票' in ft: tag = '股票型'
    elif '货币' in ft: tag = '货币型'
    elif 'QDII' in ft: tag = 'QDII型'
    elif 'FOF' in ft or '基金中基金' in ft: tag = 'FOF型'
    else: tag = '混合型'
    # 指数型识别兜底：名称含ETF/指数
    if tag not in ('指数型','债券型','货币型') and re.search(r'ETF|指数|LOF', str(name)):
        tag = '指数型'
    basic[code] = {
        'fundCode': code,
        'fundName': str(name).strip() if name else code,
        'riskLevelNum': risk_num,
        'riskLevel': f'R{risk_num}' if risk_num else None,
        'fundTypeTag': tag,
        'fundScale': float(scale)/1e8 if isinstance(scale,(int,float)) and scale else None,  # 元→亿
        'purchaseFee': float(purch_fee) if isinstance(purch_fee,(int,float)) else None,
    }
print(f'基础信息加载: {len(basic)} 只')

# ---------- 2. 绩效表（取最新周期 010001，每只基金最后一条 TRADE_DT） ----------
perf = {}
with open(os.path.join(BASE, 'fof_index_value_v2_test_202609141659.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        code = row['J_WINDCODE']
        if code not in basic: continue
        perf[code] = {
            'RETURNRATE': float(row['RETURNRATE']) if row['RETURNRATE'] not in ('',None) else None,
            'SHARP': float(row['SHARP']) if row['SHARP'] not in ('',None) else None,
            'VOL': float(row['VOL']) if row['VOL'] not in ('',None) else None,
            'MAX_DRAWDOWN': float(row['MAX_DRAWDOWN']) if row['MAX_DRAWDOWN'] not in ('',None) else None,
            'KARMA': float(row['KARMA']) if row['KARMA'] not in ('',None) else None,
            'INFO_RATIO': float(row['INFO_RATIO']) if row['INFO_RATIO'] not in ('',None) else None,
            'ANNUALRETURN_RATE': float(row['ANNUALRETURN_RATE']) if row['ANNUALRETURN_RATE'] not in ('',None) else None,
            'MAX_DRAWDOWN_RECOVER': float(row['MAX_DRAWDOWN_RECOVER']) if row['MAX_DRAWDOWN_RECOVER'] not in ('',None) else None,
            'reportDate': row['TRADE_DT'],
            'cycle': row['HB_CYCLE'],
        }
print(f'绩效数据: {len(perf)} 只')

# ---------- 3. 行业配置表（最新报告期） ----------
ind = {}
with open(os.path.join(BASE, 'fof_fund_industry_config_202609141630.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        code = row['HB_FUND_CODE']
        if code not in basic: continue
        ic = {}
        for i in range(1, 31):
            k = f'CI005{i:03d}'
            v = row.get(k)
            if v not in ('', None):
                fv = float(v)
                if fv > 0: ic[k] = fv
        ind[code] = {'industryConfig': ic, 'topIndustry': row.get('TOP_INDUSTRY','')[:500], 'reportDate': row.get('REPORT_DATE')}
print(f'行业配置: {len(ind)} 只')

# ---------- 4. 估值表（最新HB_CYCLE 010005，取最新END_DATE） ----------
val = {}
with open(os.path.join(BASE, 'fof_fund_multi_config_info_202609141702.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        code = row['HB_FUND_CODE']
        if code not in basic: continue
        if row.get('HB_CYCLE') != '010005': continue
        val[code] = {
            'PE': float(row['PE']) if row['PE'] not in ('',None) else None,
            'PB': float(row['PB']) if row['PB'] not in ('',None) else None,
            'ROE': float(row['ROE']) if row['ROE'] not in ('',None) else None,
            'DIVIDEND': float(row['DIVIDEND']) if row['DIVIDEND'] not in ('',None) else None,
            'CHANGE_RATE': float(row['CHANGE_RATE']) if row['CHANGE_RATE'] not in ('',None) else None,
        }
print(f'估值数据: {len(val)} 只')

# ---------- 5. 风险归因表（最新HB_CYCLE 010010） ----------
risk = {}
with open(os.path.join(BASE, 'fof_multi_attr_riskmodel_202609141700.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        code = row['HB_FUND_CODE']
        if code not in basic: continue
        if row.get('HB_CYCLE') != '010010': continue
        risk[code] = {
            'BETA': float(row['BETA']) if row['BETA'] not in ('',None) else None,
            'MOMENTUM': float(row['MOMENTUM']) if row['MOMENTUM'] not in ('',None) else None,
            'VALUE': float(row['VALUE']) if row['VALUE'] not in ('',None) else None,
            'GROWTH': float(row['GROWTH']) if row['GROWTH'] not in ('',None) else None,
            'SIZE': float(row['SIZE']) if row['SIZE'] not in ('',None) else None,
            'VOLATILITY': float(row['VOLATILITY']) if row['VOLATILITY'] not in ('',None) else None,
        }
print(f'风险归因: {len(risk)} 只')

# ---------- 6. 汇总构建基金池 ----------
# 绩效为基础（必选），行业/估值/风险为可选（R1/R2 债基货基无行业披露数据，缺失置空）
pool = []
for code, b in basic.items():
    if code not in perf: continue
    p = perf[code]
    # 绩效完整性：RETURNRATE/VOL/SHARP 至少一个有效
    if p['RETURNRATE'] is None and p['VOL'] is None and p['SHARP'] is None:
        continue
    v = val.get(code, {})
    r = risk.get(code, {})
    # 行业配置：缺失则置空（债基/货基场景）
    ic = ind.get(code, {}).get('industryConfig', {})
    total = sum(ic.values())
    if total > 0 and abs(total - 1.0) > 0.05:
        ic = {k: x/total for k, x in ic.items()}
    # 行业主标签（占比最高的行业）
    top_ind = max(ic, key=ic.get) if ic else None
    # 标签：风险 + 类型 + 主行业（有行业配置才加行业标签）
    tags = [f'R{b["riskLevelNum"]}' if b['riskLevelNum'] else '风险未知', b['fundTypeTag']]
    if top_ind:
        ind_name = INDUSTRY_NAMES.get(top_ind, top_ind)
        tags.append(ind_name)
    # 绩效标签
    if p['RETURNRATE'] is not None and p['RETURNRATE'] > 0.1: tags.append('高收益')
    if p['SHARP'] is not None and p['SHARP'] > 1.0: tags.append('夏普优秀')
    if p['VOL'] is not None and p['VOL'] < 0.05: tags.append('低波动')
    if p['MAX_DRAWDOWN'] is not None and abs(p['MAX_DRAWDOWN']) < 0.05: tags.append('低回撤')
    fund = {
        'fundCode': code,
        'fundName': b['fundName'],
        'fundFullName': b['fundName'],
        'fundTypeTag': b['fundTypeTag'],
        'riskLevelNum': b['riskLevelNum'],
        'riskLevel': b['riskLevel'],
        'fundScale': b['fundScale'],
        'managementFee': b['purchaseFee'],   # 详情页"管理费率"以申购费率近似展示（真实管理费率待基础表扩充）
        'purchaseFee': b['purchaseFee'],
        'reportDate': p['reportDate'],
        'matchTags': tags,
        'performance': {
            'RETURNRATE': p['RETURNRATE'],
            'ANNUALRETURN_RATE': p['ANNUALRETURN_RATE'],
            'SHARP': p['SHARP'],
            'VOL': p['VOL'],
            'MAX_DRAWDOWN': p['MAX_DRAWDOWN'],
            'KARMA': p['KARMA'],
            'INFO_RATIO': p['INFO_RATIO'],
            'MAX_DRAWDOWN_RECOVER': p['MAX_DRAWDOWN_RECOVER'],
            'reportDate': p['reportDate'],
        },
        'industryConfig': ic,
        'topIndustry': ind.get(code, {}).get('topIndustry', ''),
        'valuation': v,
        'riskFactors': r,
        'topIndustryCode': top_ind,
    }
    pool.append(fund)

print(f'\n基金池构建: {len(pool)} 只')
if pool:
    from collections import Counter
    print('类型分布:', Counter(x['fundTypeTag'] for x in pool))
    print('风险分布:', Counter(x['riskLevelNum'] for x in pool))
    # AI 基金
    ai = [x for x in pool if re.search(r'AI|人工智能|算力|大模型', x['fundName'])]
    print(f'名称含AI/人工智能/算力/大模型: {len(ai)} 只')
    for x in ai[:10]:
        print('  ', x['fundCode'], x['fundName'], '|', x['riskLevel'], '|', x['fundTypeTag'])

# 输出 JS（精简字段，避免文件过大）
def js_val(v, nd=4):
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v): return 'null'
        return repr(round(v, nd))
    if isinstance(v, (int,)): return str(v)
    if isinstance(v, str): return json.dumps(v, ensure_ascii=False)
    raise TypeError(type(v))

lines = ['// 由 build_fund_pool.py 生成 — 基于研究所投研数据(2026-09-22导出)重构', '// 全局变量 window.FUND_POOL，供 index.html 加载后赋值给 MOCK_FUNDS', 'window.FUND_POOL = [']
for x in pool:
    perf_o = '{' + ','.join(f"{k}:{js_val(x['performance'][k])}" for k in ['RETURNRATE','SHARP','VOL','MAX_DRAWDOWN']) + '}'
    # 行业配置仅保留占比>=0.005 的行业（控制体积），阈值保留4位
    ic = {k: round(v, 4) for k, v in x['industryConfig'].items() if v >= 0.005}
    ic_o = '{' + ','.join(f"{k}:{js_val(v,4)}" for k, v in sorted(ic.items())) + '}' if ic else '{}'
    val_o = '{' + ','.join(f"{k}:{js_val(x['valuation'].get(k),2)}" for k in ['PE','PB','ROE','DIVIDEND']) + '}' if x['valuation'] else '{}'
    rf_o = '{' + ','.join(f"{k}:{js_val(x['riskFactors'].get(k),4)}" for k in ['BETA','VALUE','GROWTH','SIZE','MOMENTUM']) + '}' if x['riskFactors'] else '{}'
    tags_o = '[' + ','.join(js_val(t) for t in x['matchTags']) + ']'
    obj = '{fundCode:' + js_val(x['fundCode']) + ',fundName:' + js_val(x['fundName']) + ',fundFullName:' + js_val(x['fundFullName']) \
        + ',fundTypeTag:' + js_val(x['fundTypeTag']) + ',riskLevelNum:' + js_val(x['riskLevelNum']) + ',riskLevel:' + js_val(x['riskLevel']) \
        + ',fundScale:' + js_val(x['fundScale'],2) + ',managementFee:' + js_val(x['managementFee'],2) + ',purchaseFee:' + js_val(x['purchaseFee'],2) \
        + ',reportDate:' + js_val(x['reportDate']) + ',matchTags:' + tags_o \
        + ',performance:' + perf_o + ',industryConfig:' + ic_o + ',valuation:' + val_o + ',riskFactors:' + rf_o + ',topIndustryCode:' + js_val(x['topIndustryCode']) + '}'
    lines.append('  ' + obj + ',')
lines[-1] = lines[-1].rstrip(',')
lines.append('];')
out_js = '\n'.join(lines)
with open(os.path.join(OUT, 'fund-pool.js'), 'w', encoding='utf-8') as f:
    f.write(out_js)
print(f'\n已输出: {os.path.join(OUT, "fund-pool.js")} ({os.path.getsize(os.path.join(OUT,"fund-pool.js"))//1024}KB)')
