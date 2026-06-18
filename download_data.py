"""
历史数据下载脚本 —— 使用 AKShare 免费下载期货日线数据
支持所有主流期货品种，无需 API token
"""
import akshare as ak
import pandas as pd
import os
import json
from datetime import datetime

# 常用期货品种映射
FUTURES_MAP = {
    "CU": "沪铜", "RB": "螺纹钢", "I": "铁矿石", "SC": "原油",
    "M": "豆粕", "MA": "甲醇", "TA": "PTA", "FU": "燃油",
    "RU": "橡胶", "AU": "沪金", "AG": "沪银", "CF": "棉花",
    "SR": "白糖", "Y": "豆油", "P": "棕榈油", "ZN": "沪锌",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def download_futures(symbol, name):
    """下载单个期货品种的历史日线数据"""
    print(f"  下载 {symbol} ({name})...")
    try:
        df = ak.futures_zh_daily_sina(symbol=f"{symbol}0")
        if df is None or len(df) == 0:
            print(f"    -> 无数据")
            return None
        df = df.rename(columns={
            "date": "date", "open": "open", "high": "high",
            "low": "low", "close": "close", "volume": "volume"
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        # 只保留最近 3 年
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=3)
        df = df[df["date"] >= cutoff]

        filepath = os.path.join(DATA_DIR, f"{symbol}.csv")
        df.to_csv(filepath, index=False)
        print(f"    -> {len(df)} 条 ({df['date'].min().date()} ~ {df['date'].max().date()})")
        return df
    except Exception as e:
        print(f"    -> 失败: {e}")
        return None


def download_all():
    """批量下载所有配置的期货品种"""
    print("=" * 50)
    print("  期货历史数据下载 (AKShare 免费)")
    print("=" * 50)

    results = {}
    for symbol, name in FUTURES_MAP.items():
        df = download_futures(symbol, name)
        if df is not None:
            results[symbol] = {
                "name": name,
                "count": len(df),
                "start": str(df["date"].min().date()),
                "end": str(df["date"].max().date()),
                "file": f"{symbol}.csv"
            }

    # 保存索引
    index_path = os.path.join(DATA_DIR, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print()
    print(f"完成！{len(results)}/{len(FUTURES_MAP)} 个品种下载成功")
    print(f"数据保存在: {DATA_DIR}")


if __name__ == "__main__":
    download_all()
