"""Exploratory data analysis and data-quality investigation for sales.csv.

Run: python3 data_exploration.py
VS Code: execute # %% cells from top to bottom.

This is an investigation, not the production ETL pipeline. The original
records are preserved in raw_df; cleaning is demonstrated on a separate copy.
"""

# %% 01 | Imports and source
from pathlib import Path
import pandas as pd
from solution import add_virtual_column

PROJECT_DIR = Path(__file__).resolve().parent
INPUT_PATH = PROJECT_DIR / "sales.csv"
raw_df = pd.read_csv(INPUT_PATH)

print("\n01 | INITIAL DATA PROFILE")
print("Shape:", raw_df.shape)
print("Columns:", raw_df.columns.tolist())
print("\nFirst five records:\n", raw_df.head().to_string(index=False))
print("\nData types:\n", raw_df.dtypes.to_string())
print("\nMissing values:\n", raw_df.isna().sum().to_string())
print("\nExact duplicate rows:", raw_df.duplicated().sum())
# Observed in the supplied dataset: 1,507 rows, 7 columns, 5 exact
# duplicates; 963 blank discounts, 5 blank unit prices, and one blank
# each for Region, Product and Order Date (from the TOTAL summary row).

# %% 02 | Header quality: whitespace and embedded repeated header
print("\n02 | COLUMN NAMES AND EMBEDDED HEADERS")
df = raw_df.copy()
print("Before:", df.columns.tolist())
df.columns = df.columns.str.strip()
print("After: ", df.columns.tolist())

header_mask = (
    df.astype("string")
    .apply(lambda col: col.str.strip())
    .eq(df.columns)
    .all(axis=1)
)
print("Repeated header rows:", int(header_mask.sum()))
print(df.loc[header_mask].to_string(index=True))
df = df.loc[~header_mask].copy()
print("Rows after header removal:", len(df))
# Observed: 'Quantity ' has trailing whitespace; 1 embedded header at
# original index 751. Concatenated exports are a possibility, not proven.

# %% 03 | Duplicate transactions: inspect before removal
print("\n03 | EXACT DUPLICATE RECORDS")
duplicate_rows = df.loc[df.duplicated(keep=False)].sort_values("Order ID")
print("Rows in duplicate groups:", len(duplicate_rows))
print("Redundant rows:", int(df.duplicated().sum()))
print(duplicate_rows.to_string(index=False))
df = df.drop_duplicates(keep="first").copy()
print("Rows after deduplication:", len(df))
# Observed: 5 identical pairs (10 occurrences), 5 redundant rows removed.
# IDs: SO-10305, SO-10822, SO-10966, SO-11240, SO-11405.

# %% 04 | Non-transactional TOTAL row and reconciliation
print("\n04 | TOTAL SUMMARY ROW INVESTIGATION")
total_mask = df["Order ID"].astype("string").str.strip().eq("TOTAL")
total_rows = df.loc[total_mask].copy()
sales_before_total_removal = df.loc[~total_mask].copy()
print("Summary rows:", len(total_rows))
print(total_rows.to_string(index=False))

# The source contains thousands separators as spaces and decimal commas.
qty_for_reconciliation = pd.to_numeric(
    sales_before_total_removal["Quantity"].astype("string")
    .str.replace(" ", "", regex=False), errors="coerce"
)
discount_for_reconciliation = pd.to_numeric(
    sales_before_total_removal["Discount"].astype("string")
    .str.replace(",", ".", regex=False), errors="coerce"
)
print("Transaction quantity after deduplication:", qty_for_reconciliation.sum())
print("Transaction discount after deduplication:", discount_for_reconciliation.sum())
if len(total_rows) == 1:
    reported_qty = pd.to_numeric(total_rows["Quantity"], errors="coerce").iloc[0]
    reported_discount = pd.to_numeric(total_rows["Discount"], errors="coerce").iloc[0]
    print("TOTAL reported quantity:", reported_qty)
    print("TOTAL reported discount:", reported_discount)
    print("Quantity difference:", reported_qty - qty_for_reconciliation.sum())
    print("Discount difference:", round(reported_discount - discount_for_reconciliation.sum(), 2))

df = sales_before_total_removal.copy()
print("Rows after excluding TOTAL:", len(df))
# Observed: TOTAL quantity 37,150 vs deduplicated 37,054 (difference 96);
# TOTAL discount 65,924.67 vs 65,793.77 (difference 130.90).
# These differences match the removed duplicates' quantity/discount.
# This supports, but does not prove, that TOTAL was computed before deduplication.
# The TOTAL row also explains the apparent missing Region/Product/Order Date.

# %% 05 | Missing unit prices: inspect product-level evidence
print("\n05 | MISSING UNIT PRICES")
missing_prices = df.loc[df["Unit Price"].isna()]
print("Missing unit prices:", len(missing_prices))
print(missing_prices.to_string(index=False))

price_evidence = df.loc[df["Product"].isin(["Keyboard", "Printer paper"])].copy()
price_evidence["Unit Price"] = pd.to_numeric(
    price_evidence["Unit Price"].astype("string")
    .str.replace(",", ".", regex=False), errors="coerce"
)
print("\nObserved prices for affected products:")
print(price_evidence.groupby("Product")["Unit Price"]
      .agg(["count", "nunique", "min", "max", "median"]).to_string())
# Observed: 4 missing prices: SO-10610 and SO-11099 (Printer paper),
# SO-11350 and SO-11477 (Keyboard).
# All 194 observed Printer paper prices = 21.00;
# all 205 observed Keyboard prices = 89.00.
product_prices = {"Keyboard": 89.00, "Printer paper": 21.00}
for product, price in product_prices.items():
    observed = price_evidence.loc[price_evidence["Product"].eq(product), "Unit Price"].dropna()
    assert len(observed) > 0 and observed.eq(price).all(), f"Price assumption changed: {product}"

df["Unit Price"] = df["Unit Price"].fillna(df["Product"].map(product_prices))
print("Missing unit prices after imputation:", int(df["Unit Price"].isna().sum()))
# Decision: impute these 4 prices using product-specific observed constants.
# Assumption is specific to this dataset, not a general pricing policy.

# %% 06 | Missing discounts and missingness after structural cleanup
print("\n06 | DISCOUNT MISSINGNESS")
print("Missing values before discount fill:\n", df.isna().sum().to_string())
missing_discounts = int(df["Discount"].isna().sum())
print("Missing discounts:", missing_discounts)
df["Discount"] = df["Discount"].fillna(0)
print("Missing values after fill:\n", df.isna().sum().to_string())
# Observed: 959 missing discounts after removing headers, duplicates,
# and TOTAL. Per assignment business rule, missing discount means zero.

# %% 07 | Raw numeric formatting issues and controlled conversion
print("\n07 | NUMERIC FORMATS AND TYPE CONVERSION")
numeric_columns = ["Quantity", "Unit Price", "Discount"]
for column in numeric_columns:
    original_text = df[column].astype("string")
    comma_mask = original_text.str.contains(",", regex=False, na=False)
    space_mask = original_text.str.contains(" ", regex=False, na=False)
    print(f"\n{column}: decimal-comma rows={int(comma_mask.sum())}, space-containing rows={int(space_mask.sum())}")
    print("Comma examples:", original_text.loc[comma_mask].unique().tolist())
    print("Space examples:", original_text.loc[space_mask].unique().tolist())
    cleaned_text = (original_text.str.strip()
                    .str.replace(" ", "", regex=False)
                    .str.replace(",", ".", regex=False))
    converted = pd.to_numeric(cleaned_text, errors="coerce")
    invalid_mask = converted.isna() & cleaned_text.notna()
    print("Unparseable non-null values:", int(invalid_mask.sum()))
    if invalid_mask.any():
        print(df.loc[invalid_mask, ["Order ID", column]].to_string(index=False))
    df[column] = pd.to_numeric(cleaned_text, errors="raise")
print("\nFinal numeric dtypes:\n", df[numeric_columns].dtypes.to_string())
# Observed in the original investigation: 4 space-grouped quantities
# ('1 762', '1 745', '1 371', '1 427') and 7 decimal-comma prices.
# All remaining numeric values convert without parsing errors.

# %% 08 | Numeric distributions and business-rule anomalies
print("\n08 | NUMERIC DISTRIBUTIONS AND ANOMALIES")
print(df[numeric_columns].describe().to_string())
gross = df["Quantity"] * df["Unit Price"]
nonpositive_qty = df["Quantity"] <= 0
negative_prices = df["Unit Price"] < 0
negative_discounts = df["Discount"] < 0
excessive_discount = df["Discount"] > gross
fractional_quantity = df["Quantity"] % 1 != 0
print("Non-positive quantities:", int(nonpositive_qty.sum()))
print("Negative prices:", int(negative_prices.sum()))
print("Negative discounts:", int(negative_discounts.sum()))
print("Discount > gross amount:", int(excessive_discount.sum()))
print("Fractional quantities:", int(fractional_quantity.sum()))
print("Overlap (non-positive quantity and discount > gross):", int((nonpositive_qty & excessive_discount).sum()))
suspicious = df.loc[nonpositive_qty | excessive_discount].copy()
suspicious["Gross Amount"] = suspicious["Quantity"] * suspicious["Unit Price"]
print("\nSuspicious transactions:\n", suspicious.to_string(index=False))
negative_qty = df.loc[df["Quantity"] < 0]
print("Potential return records:", len(negative_qty))
print("Potential return gross amount:", round((negative_qty["Quantity"] * negative_qty["Unit Price"]).sum(), 2))
# Observed: 6 negative-quantity rows, all with zero discount; total
# contribution -913.00. They may represent returns/adjustments, but
# this interpretation is unconfirmed. Keep their negative revenue.
# Discount > gross flags the same 6 because gross is negative;
# it is NOT evidence of 6 separate excessive positive discounts.

# %% 09 | Region consistency before normalization
print("\n09 | REGION NAME CONSISTENCY")
original_regions = df["Region"].copy()
normalized_regions = original_regions.astype("string").str.strip().str.title()
affected_regions = original_regions.ne(normalized_regions)
print("Distinct labels before:", original_regions.nunique())
print("Distinct labels after:", normalized_regions.nunique())
print("Transactions requiring normalization:", int(affected_regions.sum()))
print("\nOriginal region counts:\n", original_regions.value_counts(dropna=False).to_string())
print("\nOriginal labels with visible whitespace:")
for value in sorted(original_regions.dropna().unique()):
    print(repr(value))
print("\nAffected labels:\n", original_regions.loc[affected_regions].value_counts().to_string())
df["Region"] = normalized_regions
# Observed: 17 original region labels -> 5 canonical regions;
# 15 transactions (1% of 1,500) changed by strip/title.

# %% 10 | Product name consistency: inspect, do not rewrite
print("\n10 | PRODUCT NAME CONSISTENCY")
products = df["Product"]
normalized_products = products.astype("string").str.strip().str.casefold()
product_variants = pd.DataFrame({"original": products, "normalized": normalized_products})
variant_counts = product_variants.groupby("normalized")["original"].nunique()
print("Distinct products before:", products.nunique())
print("Distinct products after case/space normalization:", normalized_products.nunique())
print("\nProduct frequencies:\n", products.value_counts(dropna=False).to_string())
print("\nExact product labels:")
for value in sorted(products.dropna().unique()):
    print(repr(value))
print("\nGroups with multiple spellings:\n", variant_counts[variant_counts > 1].to_string())
# Observed: 8 consistent product labels, no evident formatting variants.
# No changes required. Typographical errors beyond normalization would
# need an authoritative product catalog to verify definitively.

# %% 11 | Transaction identifier quality
print("\n11 | ORDER ID UNIQUENESS")
print("Transactions:", len(df))
print("Unique Order IDs:", df["Order ID"].nunique())
print("Repeated Order IDs:", int(df["Order ID"].duplicated().sum()))
print(df.loc[df["Order ID"].duplicated(keep=False)].to_string(index=False))
# Observed: 1,500 transactions and 1,500 unique Order IDs.

# %% 12 | Date validity and date range
print("\n12 | ORDER DATE QUALITY")
parsed_dates = pd.to_datetime(df["Order Date"], format="%Y-%m-%d", errors="coerce")
invalid_dates = df.loc[parsed_dates.isna(), ["Order ID", "Order Date"]]
format_valid = df["Order Date"].astype("string").str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
print("Invalid calendar dates:", len(invalid_dates))
print("Incorrect date string formats:", int((~format_valid).sum()))
print("Earliest date:", parsed_dates.min())
print("Latest date:", parsed_dates.max())
print(invalid_dates.to_string(index=False))
# Observed: 0 invalid dates, 0 formatting issues; date range
# 2026-01-02 through 2026-09-29. Parsing is validation only.

# %% 13 | Final cleaning checks
print("\n13 | POST-CLEANING VALIDATION")
print("Cleaned shape:", df.shape)
print("Missing values:\n", df.isna().sum().to_string())
assert len(df) == 1500, "Unexpected number of transactions for this source file"
assert not df.isna().any().any(), "Missing values remain"
assert df["Order ID"].is_unique, "Duplicate Order IDs remain"
assert df["Region"].nunique() == 5, "Unexpected region count"
assert df["Product"].nunique() == 8, "Unexpected product count"
assert parsed_dates.notna().all() and format_valid.all(), "Date validation failed"
print("All source-specific cleaning checks passed")

# %% 14 | Virtual columns and independent calculation verification
print("\n14 | REVENUE CALCULATION VALIDATION")
revenue_df = df.rename(columns={
    "Quantity": "quantity", "Unit Price": "unit_price", "Discount": "discount"
}).copy()
revenue_df = add_virtual_column(revenue_df, "quantity * unit_price", "gross_revenue")
assert not revenue_df.empty, "Gross revenue expression failed"
revenue_df = add_virtual_column(revenue_df, "gross_revenue - discount", "revenue")
assert not revenue_df.empty, "Net revenue expression failed"
expected_revenue = revenue_df["quantity"] * revenue_df["unit_price"] - revenue_df["discount"]
pd.testing.assert_series_equal(revenue_df["revenue"], expected_revenue, check_names=False)
assert revenue_df["revenue"].notna().all()
print("Transactions:", len(revenue_df))
print("Total revenue:", round(revenue_df["revenue"].sum(), 2))
print(revenue_df[["Order ID", "quantity", "unit_price", "discount", "gross_revenue", "revenue"]].head().to_string(index=False))
# Observed total revenue: 2,570,247.03 (currency not specified).

# %% 15 | Regional aggregation and reconciliation
print("\n15 | REGIONAL REVENUE RECONCILIATION")
revenue_by_region = (
    revenue_df.groupby("Region", as_index=False)["revenue"].sum()
    .rename(columns={"Region": "region", "revenue": "total_revenue"})
    .sort_values("region").reset_index(drop=True)
)
print(revenue_by_region.to_string(index=False))
regional_total = revenue_by_region["total_revenue"].sum()
transaction_total = revenue_df["revenue"].sum()
print("Sum of regional revenue:", round(regional_total, 2))
print("Sum of transaction revenue:", round(transaction_total, 2))
assert abs(regional_total - transaction_total) < 0.01, "Revenue reconciliation failed"
assert abs(transaction_total - 2570247.03) < 0.01, "Unexpected revenue for this source file"
print("Regional revenue reconciled successfully")
# Expected: Central 515,824.67; East 442,219.91; North 665,897.52;
# South 504,036.04; West 442,268.89.
# This EDA intentionally does not export CSV: pipeline.py owns production output.

# %% 16 | Investigation summary
print("\n16 | INVESTIGATION SUMMARY")
print("Raw records:", len(raw_df))
print("Repeated header rows:", int(header_mask.sum()))
print("Redundant exact duplicates:", len(duplicate_rows) // 2)
print("TOTAL summary rows:", len(total_rows))
print("Clean transactions:", len(df))
print("Imputed unit prices:", len(missing_prices))
print("Zero-filled discounts:", missing_discounts)
print("Region labels standardized:", int(affected_regions.sum()))
print("Negative-quantity records retained:", len(negative_qty))
print("Final revenue:", round(transaction_total, 2))
print("EDA completed; see pipeline.py for the reproducible ETL export")

# %%
