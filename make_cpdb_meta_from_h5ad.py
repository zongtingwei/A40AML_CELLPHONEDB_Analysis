#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, pandas as pd, anndata as ad

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5ad", required=True)
    ap.add_argument("--cluster-col", required=True)
    ap.add_argument("--out", default="meta.txt")
    args = ap.parse_args()

    adata = ad.read_h5ad(args.h5ad)
    if args.cluster_col not in adata.obs.columns:
        raise SystemExit(f"obs 没有列: {args.cluster_col}")
    meta = pd.DataFrame({
        "Cell": adata.obs_names.astype(str),
        "cell_type": adata.obs[args.cluster_col].astype(str)
    })
    meta.to_csv(args.out, sep="\t", index=False)
    print(f"[OK] wrote {args.out} (n={meta.shape[0]})")

if __name__ == "__main__":
    main()
