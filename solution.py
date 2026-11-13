
import pandas as pd
import re
from pandas.api.types import is_numeric_dtype


def add_virtual_column(
    df: pd.DataFrame,
    role: str,
    new_column: str
) -> pd.DataFrame:

    
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    if not isinstance(role, str) or not isinstance(new_column, str):
        return pd.DataFrame()

    
    if not re.fullmatch(r'[A-Za-z_]+', new_column):
        return pd.DataFrame()

    
    parts = re.split(r'([+*-])', role)

    if len(parts) != 3:
        return pd.DataFrame()

    column_1, operation, column_2 = parts

    column_1 = column_1.strip()
    column_2 = column_2.strip()

    
    if not re.fullmatch(r'[A-Za-z_]+', column_1):
        return pd.DataFrame()

    if not re.fullmatch(r'[A-Za-z_]+', column_2):
        return pd.DataFrame()

    
    if column_1 not in df.columns or column_2 not in df.columns:
        return pd.DataFrame()

    
    if (
        not is_numeric_dtype(df[column_1])
        or not is_numeric_dtype(df[column_2])
    ):
        return pd.DataFrame()

    
    if operation == "+":
        result = df[column_1] + df[column_2]

    elif operation == "-":
        result = df[column_1] - df[column_2]

    elif operation == "*":
        result = df[column_1] * df[column_2]

   
    df = df.copy()
    df[new_column] = result

    return df
