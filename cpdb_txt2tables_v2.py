

import argparse
from pathlib import Path
import sys
import re
import importlib
import pandas as pd

def detect_sep(sample: str):
    if "\t" in sample: return "\t", False
    if sample.count(",") > 0: return ",", False
    if sample.count(";") > 0: return ";", False
    if "|" in sample: return "|", False
    return r"\s+", True

def safe_sheet_name(basename: str, used: set) -> str:
    short = basename
    REPL = [
        ("statistical_analysis_deconvoluted_percents", "deconv_percents"),
        ("statistical_analysis_deconvoluted",          "deconv"),
        ("statistical_analysis_interaction_scores",    "interact_scores"),
        ("statistical_analysis_significant_means",     "signif_means"),
        ("statistical_analysis_pvalues",               "pvalues"),
        ("statistical_analysis_means",                 "means"),
    ]
    for a, b in REPL:
        if short.startswith(a):
            short = short.replace(a, b, 1)
            break

    m = re.search(r"(_\d{2}_\d{2}_\d{4}_\d{6})$", short)
    ts = m.group(1) if m else ""
    core = short[:-len(ts)] if ts else short

    MAXLEN = 31
    base = (core[: MAXLEN - len(ts)]) + ts
    name = base[:MAXLEN]

    if name not in used:
        used.add(name)
        return name

    i = 2
    while True:
        suffix = f"_{i}"
        name2 = base[: MAXLEN - len(suffix)] + suffix
        if name2 not in used:
            used.add(name2)
            return name2
        i += 1

def try_read(path: Path, encoding: str):
    """按 encoding 读取，自动选择引擎并处理异常。"""
    with path.open("r", encoding=encoding, errors="ignore") as fh:
        head = fh.read(4096)
    sep, is_regex = detect_sep(head)

    if is_regex:
        return pd.read_csv(
            path, sep=sep, engine="python", encoding=encoding,
            on_bad_lines="skip"
        )
    else:
        try:
            return pd.read_csv(
                path, sep=sep, engine="c", encoding=encoding,
                low_memory=False
            )
        except Exception:
            return pd.read_csv(
                path, sep=sep, engine="python", encoding=encoding,
                on_bad_lines="skip"
            )

def read_table(path: Path) -> pd.DataFrame:
    try:
        return try_read(path, "utf-8")
    except Exception as e1:
        try:
            return try_read(path, "latin-1")
        except Exception as e2:
            raise RuntimeError(f"读取失败 {path.name}；utf-8 错误：{e1}；latin-1 错误：{e2}")

def pick_excel_engine():
    if importlib.util.find_spec("xlsxwriter") is not None:
        return "xlsxwriter"
    if importlib.util.find_spec("openpyxl") is not None:
        return "openpyxl"
    return None

def main():
    ap = argparse.ArgumentParser(description="Convert CPDB .txt -> CSV + Excel (multi-sheets)")
    ap.add_argument("--indir",  required=True, help="输入目录（包含 .txt）")
    ap.add_argument("--outdir", required=True, help="输出目录（将写入 CSV 和 Excel）")
    ap.add_argument("--excel",  default="cpdb_tables.xlsx", help="合并 Excel 文件名（默认 cpdb_tables.xlsx）")
    ap.add_argument("--pattern", default="*.txt", help="匹配的文件模式（默认 *.txt）")
    args = ap.parse_args()

    indir  = Path(args.indir).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    txt_paths = sorted(indir.glob(args.pattern))
    if not txt_paths:
        print(f"[Error] 在 {indir} 下未找到匹配 {args.pattern} 的文件。", file=sys.stderr)
        sys.exit(1)

    print(f"[Info] 共发现 {len(txt_paths)} 个 txt 文件。")

    engine = pick_excel_engine()
    if engine is None:
        print("[Warn] 未找到 xlsxwriter 或 openpyxl，跳过导出 Excel，仅导出 CSV。", file=sys.stderr)

    excel_path = outdir / args.excel
    writer = pd.ExcelWriter(excel_path, engine=engine) if engine else None

    used_sheet_names = set()
    for p in txt_paths:
        print(f"[Read] {p.name}")
        df = read_table(p)

        # 写 CSV（同名 .csv）
        csv_path = outdir / (p.stem + ".csv")
        df.to_csv(csv_path, index=False, encoding="utf-8")
        print(f"[OK] CSV -> {csv_path.name}  (rows={len(df)}, cols={len(df.columns)})")

        # 写 Excel（多工作表）
        if writer is not None:
            sheet = safe_sheet_name(p.stem, used_sheet_names)
            df.to_excel(writer, index=False, sheet_name=sheet)
            print(f"[OK] Excel sheet -> {sheet}")

    if writer is not None:
        writer.close()
        print(f"[Done] 合并 Excel 已写入: {excel_path}")

if __name__ == "__main__":
    main()
