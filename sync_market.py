#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
两市量能同步脚本（财联社 x-quote.cls.cn 公开行情接口）
======================================================
口径：两市总成交额 + 总成交量 = 上证指数(全沪市) + 深证综指(全深市) 之和。
接口无需鉴权，带 UA 即可。输出 data/market-volume.json，供前端首页「市场量能」读卡。

用法：python3 sync_market.py [--out path.json]
"""
import json, os, sys, datetime, argparse
import urllib.request, urllib.parse

API = "https://x-quote.cls.cn/v2/quote/a/web/stocks/basic"
FIELDS = "secu_name,secu_code,last_px,change,business_amount,business_balance"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/120 Safari/537.36",
    "Referer": "https://www.cls.cn/",
}


def fetch(secu_codes):
    qs = urllib.parse.urlencode({
        "app": "CailianpressWeb",
        "fields": FIELDS,
        "os": "web",
        "secu_codes": ",".join(secu_codes),
    })
    req = urllib.request.Request(f"{API}?{qs}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    # 上证指数(全沪市) + 深证综指(全深市)
    try:
        resp = fetch(["sh000001", "sz399106"])
    except Exception as e:
        print("抓取失败:", e, file=sys.stderr)
        sys.exit(1)

    d = resp.get("data") or {}
    hs = d.get("sh000001") or {}
    sz = d.get("sz399106") or {}

    def num(v):
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    money = num(hs.get("business_balance")) + num(sz.get("business_balance"))
    vol = num(hs.get("business_amount")) + num(sz.get("business_amount"))

    now = datetime.datetime.now()
    out = {
        "synced_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "财联社 x-quote.cls.cn（公开行情接口，无需鉴权）",
        "method": "上证指数(全沪市) + 深证综指(全深市) 之和",
        "unit_note": "money: 元；vol: 股；已镜像同名 human 字段为亿级展示值",
        "index": {
            "sh000001": {"name": hs.get("secu_name"), "last_px": hs.get("last_px"), "change": hs.get("change"),
                         "amount(股)": hs.get("business_amount"), "balance(元)": hs.get("business_balance")},
            "sz399106": {"name": sz.get("secu_name"), "last_px": sz.get("last_px"), "change": sz.get("change"),
                         "amount(股)": sz.get("business_amount"), "balance(元)": sz.get("business_balance")},
        },
        "market": {
            "money_yuan": money,
            "money_yi": round(money / 1e8, 2),
            "vol_shares": vol,
            "vol_yi": round(vol / 1e8, 2),
        },
        "display": {
            "money": f"{money / 1e8:.0f} 亿",
            "vol": f"{vol / 1e8:.0f} 亿股",
        },
    }

    print("=" * 56)
    print(f"市场量能 · {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f'  上证指数: {hs.get("secu_name")} 余额 {num(hs.get("business_balance"))/1e8:,.0f} 亿')
    print(f'  深证综指: {sz.get("secu_name")} 余额 {num(sz.get("business_balance"))/1e8:,.0f} 亿')
    print(f'  两市合计成交额: {money/1e8:,.0f} 亿  成交量: {vol/1e8:,.0f} 亿股')
    print("=" * 56)

    out_path = a.out or os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                     "data", "market-volume.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"已写入: {out_path}")


if __name__ == "__main__":
    main()