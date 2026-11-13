# %%
from pipeline import aggregate_revenue_by_region, clean_sales_data
# %%

import pandas as pd
from pipeline import calculate_revenue


def test_calculate_revenue():
    # Arrange
    df = pd.DataFrame({
        "quantity": [5],
        "unit_price": [40],
        "discount": [15]
    })

    # Act
    result = calculate_revenue(df)

    # Assert
    assert result["revenue"].iloc[0] == 185
# %%
def test_negative_quantity():
    # Arrange
    df = pd.DataFrame({
        "quantity": [-2],
        "unit_price": [100],
        "discount": [0]
    })

    # Act
    result = calculate_revenue(df)

    # Assert
    assert result["revenue"].iloc[0] == -200
# %%
def test_missing_discount():
    # Arrange
    df = pd.DataFrame({
        "Order ID": ["SO-10001"],
        "Region": ["North"],
        "Product": ["Keyboard"],
        "Quantity": [2],
        "Unit Price": [89.0],
        "Discount": [pd.NA],
        "Order Date": ["2026-01-10"]
    })

    # Act
    result = clean_sales_data(df)

    # Assert
    assert result["Discount"].iloc[0] == 0
    assert len(result) == len(df)

#%%

def test_duplicate_rows():
    # Arrange
    df = pd.DataFrame([
        {
            "Order ID": "SO-10001",
            "Region": "North",
            "Product": "Keyboard",
            "Quantity": 2,
            "Unit Price": 89.0,
            "Discount": 0,
            "Order Date": "2026-01-10"
        },
        {
            "Order ID": "SO-10001",
            "Region": "North",
            "Product": "Keyboard",
            "Quantity": 2,
            "Unit Price": 89.0,
            "Discount": 0,
            "Order Date": "2026-01-10"
        }
    ])

    # Act
    result = clean_sales_data(df)

    # Assert
    assert len(result) == 1
    assert result["Order ID"].iloc[0] == "SO-10001"

# %%
def test_total_row_removed():
    # Arrange
    df = pd.DataFrame([
        {
            "Order ID": "TOTAL",
            "Region": "North",
            "Product": "Keyboard",
            "Quantity": 2,
            "Unit Price": 89.0,
            "Discount": 0,
            "Order Date": "2026-01-10"
        },
        {
            "Order ID": "SO-10001",
            "Region": "North",
            "Product": "Keyboard",
            "Quantity": 2,
            "Unit Price": 89.0,
            "Discount": 0,
            "Order Date": "2026-01-10"
        }
    ])

    # Act
    result = clean_sales_data(df)

    # Assert
    assert len(result) == 1
    assert result["Order ID"].iloc[0] == "SO-10001"

# %%

def test_missing_unit_price():
    # Arrange
    df = pd.DataFrame({
        "Order ID": ["SO-10001"],
        "Region": ["North"],
        "Product": ["Keyboard"],
        "Quantity": [2],
        "Unit Price": [pd.NA],
        "Discount": [0],
        "Order Date": ["2026-01-10"]
    })

    # Act
    result = clean_sales_data(df)

    # Assert
    assert len(result) == 1
    assert result["Unit Price"].iloc[0] == 89.0
    assert result["Product"].iloc[0] == "Keyboard"
    assert result["Order ID"].iloc[0] == "SO-10001"
#%%
def test_region_normalization():
    # Arrange
    df = pd.DataFrame({
    "Order ID": ["SO-10001", "SO-10002", "SO-10003"],
    "Region": ["  north  ", "NORTH", "North"],
    "Product": ["Keyboard", "Keyboard", "Keyboard"],
    "Quantity": [2, 2, 2],
    "Unit Price": [89.0, 89.0, 89.0],
    "Discount": [0, 0, 0],
    "Order Date": ["2026-01-10"] * 3
})

    # Act
    result = clean_sales_data(df)

    # Assert
    assert len(result) == 3
    assert all(region == "North" for region in result["Region"])
#%%

from pandas.api.types import is_numeric_dtype


def test_numeric_formatting():
    # Arrange
    df = pd.DataFrame({
        "Order ID": ["SO-10001", "SO-10002"],
        "Region": ["North", "North"],
        "Product": ["Keyboard", "Keyboard"],
        "Quantity": [" 1 762 ", "3"],
        "Unit Price": [" 89,00 ", " 89.00"],
        "Discount": [" 0 ", "0"],
        "Order Date": ["2026-01-10", "2026-01-11"]
    })

    # Act
    result = clean_sales_data(df)

    # Assert
    assert len(result) == 2

    # Check numeric data types
    assert is_numeric_dtype(result["Quantity"])
    assert is_numeric_dtype(result["Unit Price"])
    assert is_numeric_dtype(result["Discount"])

    # Check converted values
    assert result["Quantity"].tolist() == [1762, 3]
    assert result["Unit Price"].tolist() == [89.0, 89.0]
    assert result["Discount"].tolist() == [0.0, 0.0]

#%%
def test_repeated_header_removed():
    # Arrange
    df = pd.DataFrame([
        {
            "Order ID": "SO-10001",
            "Region": "North",
            "Product": "Keyboard",
            "Quantity": 2,
            "Unit Price": 89.0,
            "Discount": 0,
            "Order Date": "2026-01-10"
        },
        {
            "Order ID": "Order ID",
            "Region": "Region",
            "Product": "Product",
            "Quantity": "Quantity",
            "Unit Price": "Unit Price",
            "Discount": "Discount",
            "Order Date": "Order Date"
        },
        {
            "Order ID": "SO-10002",
            "Region": "North",
            "Product": "Keyboard",
            "Quantity": 3,
            "Unit Price": 89.0,
            "Discount": 0,
            "Order Date": "2026-01-11"
        }
    ])

    # Act
    result = clean_sales_data(df)

    # Assert
    assert len(result) == 2
    assert "Order ID" not in result["Order ID"].values
    assert result["Order ID"].tolist() == ["SO-10001", "SO-10002"]

#%%
import pytest

def test_invalid_order_date():
    # Arrange
    df = pd.DataFrame({
        "Order ID": ["SO-10001"],
        "Region": ["North"],
        "Product": ["Keyboard"],
        "Quantity": [2],
        "Unit Price": [89.0],
        "Discount": [0],
        "Order Date": ["2026-02-30"]
    })

    # Act & Assert
    with pytest.raises(ValueError):
        clean_sales_data(df)
#%%

def test_aggregate_revenue_by_region():
    # Arrange
    df = pd.DataFrame({
        "Region": ["North", "North", "South", "South"],
        "revenue": [100, 200, 150, 250]
    })

    # Act
    result = aggregate_revenue_by_region(df)

    # Assert
    assert len(result) == 2
    assert result.loc[result["region"] == "North", "total_revenue"].iloc[0] == 300
    assert result.loc[result["region"] == "South", "total_revenue"].iloc[0] == 400
    assert result["total_revenue"].sum() == 700

#%%

def test_full_pipeline():
    # Arrange
    df = pd.DataFrame({
        "Order ID": ["SO-10001", "SO-10002", "SO-10003"],
        "Region": ["North", "north", "South"],
        "Product": ["Keyboard", "Mouse", "Monitor"],
        "Quantity": [2, 3, 1],
        "Unit Price": [89.0, 25.0, 150.0],
        "Discount": [0, 5, 10],
        "Order Date": ["2026-01-10", "2026-01-11", "2026-01-12"]
    })

    # Act
    clean_df = clean_sales_data(df)

    clean_df = clean_df.rename(columns={
        "Quantity": "quantity",
        "Unit Price": "unit_price",
        "Discount": "discount"
    })

    revenue_df = calculate_revenue(clean_df)

    revenue_by_region = aggregate_revenue_by_region(revenue_df)

    # Assert
    # Check that all transactions are preserved
    assert len(clean_df) == 3
    assert len(revenue_df) == 3

    # Check revenue columns
    assert "gross_revenue" in revenue_df.columns
    assert "revenue" in revenue_df.columns

    # Check number of regions
    assert len(revenue_by_region) == 2

    # Check revenue for North
    assert revenue_by_region.loc[
        revenue_by_region["region"] == "North",
        "total_revenue"
    ].iloc[0] == 248

    # Check revenue for South
    assert revenue_by_region.loc[
        revenue_by_region["region"] == "South",
        "total_revenue"
    ].iloc[0] == 140

    # Check total revenue
    assert revenue_by_region["total_revenue"].sum() == 388

