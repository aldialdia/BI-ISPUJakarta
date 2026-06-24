"""
run_etl.py — Entry Point Terminal
==================================
Menjalankan proses ETL dari terminal menggunakan modul etl_core.

Penggunaan:
  python etl/run_etl.py
  python etl/run_etl.py --file data/raw/data_baru.csv
"""

import pandas as pd
import argparse
import os
import sys

# Pastikan project root ada di sys.path agar import etl_core berfungsi
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from etl_core import run_etl, validate_dataframe

DEFAULT_CSV = os.path.join(PROJECT_ROOT, 'data', 'raw', 'ispu_dki_all (2).csv')


def main():
    parser = argparse.ArgumentParser(
        description='ETL Kualitas Udara DKI Jakarta (mode APPEND)'
    )
    parser.add_argument(
        '--file', '-f',
        default=DEFAULT_CSV,
        help=f'Path ke file CSV sumber data (default: {DEFAULT_CSV})'
    )
    args = parser.parse_args()

    csv_path = args.file
    print(f"\n📂 Membaca file: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"❌ File tidak ditemukan: {csv_path}")
        sys.exit(1)

    # --- Extract ---
    try:
        df_raw = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Gagal membaca file CSV: {e}")
        sys.exit(1)

    print(f"✅ Berhasil membaca {len(df_raw)} baris dari CSV.")

    # --- Validate ---
    is_valid, errors, warnings = validate_dataframe(df_raw.copy())

    if warnings:
        for w in warnings:
            print(f"⚠️  {w}")

    if not is_valid:
        print("\n❌ Validasi gagal:")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)

    print("✅ Validasi berhasil.\n")

    # --- Run ETL ---
    result = run_etl(df_raw)

    print(f"\n{'='*50}")
    print(f"✅ ETL Berhasil!")
    print(f"   Baris diproses       : {result['baris_diproses']}")
    print(f"   Baris baru           : +{result['baris_baru']}")
    print(f"   Total di database    : {result['total_di_database']}")
    print(f"   📋 Log disimpan di   : {result['log_filepath']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
