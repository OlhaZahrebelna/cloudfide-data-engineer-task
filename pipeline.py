"""Clean sales transactions and export revenue aggregated by region.

Run from any directory: python3 pipeline.py
Input:  sales.csv (next to this file)
Output: revenue_by_region.csv (next to this file)

Detailed investigations and cleaning decisions are documented in
``data_exploration.py`` and the project README.
"""

from pathlib import Path

import pandas as pd

from solution import add_virtual_column


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_PATH = PROJECT_DIR / "sales.csv"
OUTPUT_PATH = PROJECT_DIR / "revenue_by_region.csv"

REQUIRED_COLUMNS = [
    "Order ID", "Region", "Product", "Quantity",
    "Unit Price", "Discount", "Order Date",
]

# Prices verified from other transactions of the same products in sales.csv.
VERIFIED_PRODUCT_PRICES = {"Keyboard": 89.00, "Printer paper": 21.00}


def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove non-transactional rows, normalize values, and validate sales."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    # Embedded header from a repeated CSV export.
    repeated_header = (
        df.astype("string")
        .apply(lambda col: col.str.strip())
        .eq(df.columns)
        .all(axis=1)
    )
    df = df.loc[~repeated_header].copy()

    # Exact duplicates and the non-transactional summary must not count as sales.
    df = df.drop_duplicates(keep="first").copy()
    total_mask = df["Order ID"].astype("string").str.strip().eq("TOTAL")
    df = df.loc[~total_mask].copy()

    # Only fill missing prices for products whose observed prices were verified.
    df["Unit Price"] = df["Unit Price"].fillna(
        df["Product"].map(VERIFIED_PRODUCT_PRICES)
    )
    # Business rule: a blank discount means no discount.
    df["Discount"] = df["Discount"].fillna(0)

    # Handle spaces in quantities and comma decimal separators.
    for column in ("Quantity", "Unit Price", "Discount"):
        normalized = (
            df[column]
            .astype("string")
            .str.strip()
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[column] = pd.to_numeric(normalized, errors="raise")

    df["Region"] = df["Region"].str.strip().str.title()

    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("Missing required values remain after cleaning")
    if df["Order ID"].duplicated().any():
        raise ValueError("Duplicate Order IDs remain after cleaning")
    if (df["Quantity"] % 1 != 0).any():
        raise ValueError("Non-integer quantities detected")
    if (df["Unit Price"] < 0).any() or (df["Discount"] < 0).any():
        raise ValueError("Negative unit prices or discounts detected")
    if df["Region"].eq("").any():
        raise ValueError("Empty region values detected")

    # Validate the required date format and calendar validity; keep original strings.
    valid_format = df["Order Date"].astype("string").str.fullmatch(r"\d{4}-\d{2}-\d{2}")
    if not valid_format.all():
        raise ValueError("Order Date must use YYYY-MM-DD format")
    pd.to_datetime(df["Order Date"], format="%Y-%m-%d", errors="raise")

    # Negative quantities are retained: they may represent returns/adjustments.
    return df.reset_index(drop=True)


def calculate_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Use the required virtual-column function to compute net revenue."""
    df = df.rename(columns={
        "Quantity": "quantity",
        "Unit Price": "unit_price",
        "Discount": "discount",
    }).copy()

    df = add_virtual_column(df, "quantity * unit_price", "gross_revenue")
    if df.empty:
        raise ValueError("Failed to calculate gross_revenue")

    df = add_virtual_column(df, "gross_revenue - discount", "revenue")
    if df.empty:
        raise ValueError("Failed to calculate revenue")

    expected = df["quantity"] * df["unit_price"] - df["discount"]
    pd.testing.assert_series_equal(df["revenue"], expected, check_names=False)
    if df["revenue"].isna().any():
        raise ValueError("Missing revenue values detected")
    return df


def aggregate_revenue_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Sum revenue per region and reconcile against transaction-level totals."""
    if df["Region"].isna().any():
        raise ValueError("Missing region values detected")

    result = (
        df.groupby("Region", as_index=False)["revenue"]
        .sum()
        .rename(columns={"Region": "region", "revenue": "total_revenue"})
        .sort_values("region")
        .reset_index(drop=True)
    )

    if abs(result["total_revenue"].sum() - df["revenue"].sum()) >= 0.01:
        raise ValueError("Revenue reconciliation failed")

    return result


def main() -> None:
    """Run the end-to-end sales revenue pipeline."""
    raw_df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(raw_df)} raw records")

    clean_df = clean_sales_data(raw_df)
    print(f"Cleaned {len(clean_df)} transactions")

    revenue_df = calculate_revenue(clean_df)
    revenue_by_region = aggregate_revenue_by_region(revenue_df)

    revenue_by_region.to_csv(OUTPUT_PATH, index=False, float_format="%.2f")
    print("\nRevenue by region:")
    print(revenue_by_region.to_string(index=False))
    print(f"\nTotal revenue: {revenue_df['revenue'].sum():.2f}")
    print("Revenue reconciliation passed")
    print(f"Output saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
