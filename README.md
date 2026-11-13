# Sales Revenue Data Pipeline

A Python/Pandas data engineering exercise that validates sales transactions, cleans source-data issues, calculates revenue with a reusable virtual-column function, and exports total revenue by region.

The project separates **exploratory data-quality investigation** (`data_exploration.py`) from the **reproducible processing pipeline** (`pipeline.py`).

## Project structure

```text
cloudfide-data-engineer-task/
├── sales.csv
├── solution.py
├── pipeline.py
├── data_exploration.py
├── test_virtual_column.py
├── test_pipeline.py
├── revenue_by_region.csv
└── README.md
```



## Requirements and setup

- Python 3.12.5
- `pandas`

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pandas
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

Place `sales.csv` next to `pipeline.py` and `solution.py`.

## Run the pipeline

```bash
python3 pipeline.py
```

The script reads `sales.csv` from its own directory and writes `revenue_by_region.csv` to the same directory. It can be invoked from another working directory because file paths are resolved relative to `pipeline.py`.

For the provided dataset, the expected console summary is:

```text
Loaded 1507 raw records
Cleaned 1500 transactions
...
Total revenue: 2570247.03
Revenue reconciliation passed
```

The output contains two columns: `region` and `total_revenue`, sorted alphabetically by region and formatted to two decimal places.

## Virtual-column function

`solution.py` provides:

```python
def add_virtual_column(df, role, new_column):
    ...
```

The `role` expression supports two existing numeric columns separated by `+`, `-`, or `*`, for example `quantity * unit_price`. Column identifiers in expressions and the new column name may contain ASCII letters and underscores only. Invalid expressions or inputs return an empty DataFrame. Valid operations return a copy of the input DataFrame with the calculated column.

The pipeline uses the function twice:

```python
df = add_virtual_column(df, "quantity * unit_price", "gross_revenue")
df = add_virtual_column(df, "gross_revenue - discount", "revenue")
```

Therefore:

**Revenue = Quantity × Unit Price − Discount**

## Data quality assessment and cleaning decisions

The initial file contains **1,507 rows and 7 columns**. Investigations are recorded in `data_exploration.py` as numbered, runnable `# %%` cells. Counts below refer to the supplied dataset; they are not general rules for arbitrary files.

| Finding | Evidence / affected records | Decision |
|---|---|---|
| Column-name whitespace | `Quantity ` has a trailing space | Strip whitespace from column headers |
| Embedded CSV header | 1 repeated header row (original index 751) | Remove it as non-transactional data |
| Exact duplicate transactions | 5 duplicate pairs (10 occurrences; 5 redundant rows) | Keep the first occurrence of each exact row |
| Summary record | 1 `TOTAL` row | Exclude it from transaction-level analysis |
| Missing unit prices | 4 transaction rows after removing `TOTAL` | Impute using verified observed prices for the same product |
| Missing discounts | 959 transaction rows after structural cleanup | Fill with `0`, following the assignment's business rule |
| Numeric formatting | 4 quantities containing grouping spaces; 7 unit prices using decimal commas | Remove grouping spaces, replace decimal commas with dots, convert to numeric |
| Region naming inconsistencies | 17 distinct raw labels for 5 regions; 15 affected transactions | Strip surrounding whitespace and standardize capitalization |
| Product names | 8 product labels; no observed case/whitespace variants | Retain original names |
| Non-positive quantities | 6 negative-quantity transactions | Retain negative revenue; possible returns/adjustments, **not confirmed** |
| Duplicate Order IDs after cleaning | 0 among 1,500 transactions | No further deduplication |
| Invalid dates / date format | 0 invalid dates; 0 incorrect `YYYY-MM-DD` formats | Validate dates; retain their original string representation |

### Missing unit-price investigation

The four affected transactions are:

- `SO-10610` and `SO-11099` — **Printer paper**
- `SO-11350` and `SO-11477` — **Keyboard**

The remaining records showed a single observed price per affected product: **21.00** for Printer paper (194 observed prices) and **89.00** for Keyboard (205 observed prices). These values were used for imputation. This is an assumption justified by **this dataset**, not a universal product-pricing policy.

### `TOTAL` row reconciliation

The source `TOTAL` row reports quantity **37,150** and discount **65,924.67**. After removing exact duplicate transactions, the corresponding transaction sums are **37,054** and **65,793.77**. Differences of **96 units** and **130.90** in discount match the contributions of the removed duplicate records.

This is consistent with the summary having been calculated before deduplication, but its provenance cannot be established from the CSV alone. The `TOTAL` row also accounts for the apparent missing `Region`, `Product`, and `Order Date` values in the initial file profile.

### Negative quantities

Six transactions have negative quantities, with a combined gross/revenue contribution of **−913.00** (all six have zero discount). They might represent returns or adjustments, but there is no transaction-type field to confirm this. They are **retained**, not converted to positive values or silently discarded.

The same six rows are flagged by the raw check `Discount > Quantity × Unit Price`, because their gross amounts are negative; this is **not** evidence of six separate positive-sale discount violations.

### Date coverage

All retained transaction dates parse successfully as `YYYY-MM-DD`. The observed range is **2026-01-02 through 2026-09-29**.

## Pipeline stages

1. **Extract** — read the CSV.
2. **Clean** — strip headers, remove the repeated header and exact duplicates, exclude `TOTAL`, fill supported missing values, normalize numeric values and region names.
3. **Validate** — check required columns/values, unique Order IDs, integer quantities, nonnegative prices and discounts, and valid dates.
4. **Calculate** — create `gross_revenue` and `revenue` through `add_virtual_column()`; independently verify the arithmetic.
5. **Aggregate** — sum revenue by region and reconcile regional totals to transaction-level revenue (tolerance: less than 0.01).
6. **Export** — write `revenue_by_region.csv` without an index, using two decimal places.

## Validated results

| Region | Total revenue |
|---|---:|
| Central | 515,824.67 |
| East | 442,219.91 |
| North | 665,897.52 |
| South | 504,036.04 |
| West | 442,268.89 |
| **Total** | **2,570,247.03** |

- Input records: **1,507**
- Retained transactions: **1,500**
- Unique Order IDs: **1,500**
- Regions: **5**
- Products: **8**
- Remaining missing values: **0**
- Transaction-level and regional revenue totals reconcile.

No currency is specified in the input data, so monetary values are reported without a currency symbol.

## Reproduce the exploratory analysis

```bash
python3 data_exploration.py
```

Alternatively, open the file in VS Code and execute the `# %%` cells in order. The exploratory script prints intermediate evidence and checks assumptions; it does **not** write the production output CSV. Use `pipeline.py` for the final export.

## Testing

The project includes 18 automated tests implemented with `pytest`:

- **12 tests in `test_pipeline.py`** covering revenue calculation, negative quantities, missing values, duplicate removal, embedded CSV headers, region normalization, numeric formatting, invalid dates, regional aggregation, and full pipeline integration.
- **6 tests in `test_virtual_column.py`** covering addition, subtraction, multiplication, invalid column labels, invalid expressions, and extra whitespace in expressions.

Install the required dependencies:

```bash
python3 -m pip install pandas pytest
```

Run the complete test suite:

```bash
python3 -m pytest -v
```

**Latest verified result:**

```text
18 passed in 0.67s
```

The tests cover individual transformations and an integration scenario connecting data cleaning, revenue calculation, and regional aggregation.

The pipeline also performs runtime validation of data quality and revenue reconciliation. Automated tests complement these checks but do not guarantee complete code coverage.

## Assumptions and limitations

- Blank discounts mean zero, as specified by the assignment.
- Imputed unit prices rely on observed constant prices for the affected products in this source file.
- Negative quantities remain in revenue because their business meaning is unverified.
- Product spelling was checked for case/whitespace variants, but not against an authoritative product catalog.
- Source-specific record counts and expected revenue are evidence from the supplied CSV, not hard-coded requirements for other datasets.
- Financial calculations use Pandas numeric types; CSV output is formatted to two decimal places.
