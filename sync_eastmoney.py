#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富模拟组合「翻81681」自动同步脚本
=======================================
直连东财组合详情接口（已通过 mcombindetails.js 逆向定位）：
    base = simqry2.eastmoney.com/qry_tzzh_v2?type=<TYPE>&plat=2&ver=web20&zjzh=<COMBIN_ID>
    关键接口 type:
      spo_zuhe_detail_basic  组合基本信息（账户总值/名义本金/收益率/用户/仓位）
      spo_syl_survey         收益率分档（当日/5日/20日/60日/250日/总/回撤）
      spo_hold_detail        当前持仓明细（成本/股数/现价/收益率/持仓天数）
      spo_hldchg_home        首页调仓
      spo_hldchg_detail      完整调仓记录（时间/买卖/价格/仓位变化）
用法：python3 sync_eastmoney.py [--combin ID] [--out path.json] [--snap-dir dir]
"""
import json, sys, os, datetime, argparse, urllib.request, urllib.parse

COMBIN_ID = "261944300000051189"
BASE = "https://simqry2.eastmoney.com/qry_tzzh_v2"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://group.eastmoney.com/",
    "Accept": "*/*",
}


def fetch(cid, type_, **extra):
    params = {"type": type_, "plat": "2", "ver": "web20", "zjzh": cid}
    params.update(extra)
    url = BASE + "?" + urllib.parse.urlencode(
        {k: v for k, v in params.items() if v not in (None, "")})
    req = urllib.request.Request(url, headers={
        "User-Agent": HEADERS["User-Agent"],
        "Referer": "https://group.eastmoney.com/other,%s.html" % cid,
        "Accept": HEADERS["Accept"]})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--combin", default=COMBIN_ID)
    ap.add_argument("--out", default=None, help="写完整数据到指定JSON")
    ap.add_argument("--snap-dir", default=None, help="写控制台快照到目录/live-snapshot.json")
    ap.add_argument("--print", action="store_true", help="打印简要控制台摘要")
    a = ap.parse_args()
    cid = a.combin

    basic = fetch(cid, "spo_zuhe_detail_basic")["data"]
    holds = fetch(cid, "spo_hold_detail", recIdx=1, recCnt=20)["data"]
    trades = fetch(cid, "spo_hldchg_detail", recIdx=1, recCnt=100)["data"]
    survey = {d["sylType"]: d["syl"] for d in fetch(cid, "spo_syl_survey")["data"]}

    nominal_assets = float(basic.get("zzc") or 0)
    nominal_pnl = nominal_assets - 1000000.0
    real_assets = round(50000.0 + nominal_pnl, 2)
    real_return_pct = round(nominal_pnl / 50000.0 * 100, 2)
    pos_value = round(sum(float(h["holdPos"]) * float(h["price"]) for h in holds), 2)
    real_cash = round(real_assets - pos_value, 2)
    real_pos_pct = round(pos_value / real_assets * 100, 2) if real_assets else 0.0

    zzero_zzc = "%.2f" % nominal_assets if nominal_assets else "—"

    if a.print:
        print("=" * 60)
        print(f"组合: {basic.get('zuheName')} | 管理人: {basic.get('username')}")
        print(f"账户: 名义总资产 {zzero_zzc} | 5万口径 {real_assets:,.2f} | 收益率 {real_return_pct}%")
        print(f"仓位(5万口径): {real_pos_pct}% | 成交胜率: {basic.get('dealRate')}% ({basic.get('dealWinCnt')}胜/{basic.get('dealfailCnt')}负)")
        print("-" * 60)
        if holds:
            print("当前持仓:")
            for h in holds:
                print(f"  {h['stkName']}({h['stkCode']}) {h['holdPos']}股 @成本{h['cbj']} 现{h['price']} "
                      f"收益{h['ykRate']}% 持{h['hldDays']}天")
        else:
            print("当前持仓: 空仓")
        print("-" * 60)
        print(f"调仓记录共 {len(trades)} 笔 (最近5笔):")
        for t in sorted(trades, key=lambda x: x["cjsj"], reverse=True)[:5]:
            print(f"  {t['cjsj']} {t['stkName']:<6} {t['mmbz']:<2} @{t['cjjg']:<7} 仓位{t['holdPosBef']}->{t['holdPosAft']}%")
        print("=" * 60)

    if a.out:
        full = {
            "synced_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "combin_id": cid,
            "_nominal": {
                "total_assets": zzero_zzc,
                "return_pct": basic.get("zsyl"),
                "portfRat": basic.get("portfRat"),
                "start_date": basic.get("startDate"),
                "deal_rate": basic.get("dealRate"),
                "deal_win": basic.get("dealWinCnt"),
                "deal_fail": basic.get("dealfailCnt"),
                "user": basic.get("username"),
            },
            "_real_5w": {
                "real_assets": real_assets,
                "real_return_pct": real_return_pct,
                "position_pct": real_pos_pct,
                "cash": real_cash,
                "pos_value": pos_value,
                "basis": "真实总资产=5万+(名义总资产-100万)",
            },
            "survey": survey,
            "positions": holds,
            "trade_history": trades,
            "trade_count": len(trades),
        }
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(full, f, ensure_ascii=False, indent=2)
        print(f"已写入完整数据: {a.out}")

    if a.snap_dir:
        os.makedirs(a.snap_dir, exist_ok=True)
        snap_path = os.path.join(a.snap_dir, "live-snapshot.json")
        prev_total = None
        try:
            if os.path.exists(snap_path):
                prev_total = json.load(open(snap_path, encoding="utf-8")).get("account", {}).get("total_assets")
        except Exception:
            prev_total = None
        daily_pnl = round(real_assets - float(prev_total), 2) if prev_total is not None else None
        snapshot = {
            "synced_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "combin_id": cid,
            "combin_name": basic.get("zuheName"),
            "manager": basic.get("username"),
            "account": {
                "initial_principal": 50000,
                "principal_label": "人为控制实际本金5万",
                "total_assets": real_assets,
                "total_return_pct": real_return_pct,
                "position_pct": real_pos_pct,
                "cash": real_cash,
                "pos_value": pos_value,
                "start_date": basic.get("startDate"),
                "deal_rate": float(basic.get("dealRate")) if basic.get("dealRate") is not None else None,
                "deal_win": basic.get("dealWinCnt"),
                "deal_fail": basic.get("dealfailCnt"),
                "daily_pnl": daily_pnl,
                "prev_total_assets": prev_total,
            },
            "positions": [
                {"name": h["stkName"], "code": h["stkCode"], "shares": h["holdPos"],
                 "cost": float(h["cbj"]), "price": float(h["price"]),
                 "pct": float(h.get("prcPcnt", 0)), "return_pct": float(h["ykRate"]),
                 "days": h.get("hldDays", 0)}
                for h in holds
            ],
            "recent_trades": [
                {"time": t["cjsj"], "name": t["stkName"], "mmbz": t["mmbz"], "price": t["cjjg"]}
                for t in sorted(trades, key=lambda x: x["cjsj"], reverse=True)[:6]
            ],
            "trade_count": len(trades),
        }
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"已写入控制台快照: {snap_path}")


if __name__ == "__main__":
    main()