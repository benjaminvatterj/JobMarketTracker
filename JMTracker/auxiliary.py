#! /bin/python3
import pandas as pd
import xlrd

"""
A collection of auxiliary methods
"""


def corrupt_excel_reader(url):
    """Reads a corrupted excel file and returns the first sheet.

    Parameters
    ----------
    url : str
        path to file to read

    Returns
    -------
    df: DataFrame
        the loaded dataframe

    """
    workbook = xlrd.open_workbook(url, ignore_workbook_corruption=True)
    df = pd.read_excel(workbook)
    return df


def validate_unique_id(df, id_col, source):
    """Validate that the id columns has no missings and no
    repeated values

    Parameters
    ----------
    df : DataFrame
        the dataframe to examine

    id_col : str
        the name of the id column

    source: str
        the name of the source we're processing

    Returns
    -------
    status: bool
        False if failed the test
    message: str
        Message to show user if caught a failure

    """


    any_missings = df[id_col].isna().any()
    if any_missings:
        message = (f"The file for {source} has missing values"
                   " in the identifier column {id_col}. This app assumes"
                   " that the identifier is never missing. If this is no longer"
                   " the case, please submit an issue.")
        return False, message

    dups = df[id_col].nunique()
    if dups != df.shape[0]:
        message = (f"The file for {source} has duplicated values "
                   "for identifier column {id_col}. This app assumes "
                   " that the identifier is unique. If this is no longer true "
                   " please submit an issue.")
        return False, message

    return True, ''


def country_state_city_aggregator(row, df):
    """Combines country, state and city to a single location

    Parameters
    ----------
    row : Series
        a row of the data
    df : DataFrame
        the old data

    Returns
    -------
    str
        the location
    """

    locations = []
    for col in ['city', 'state', 'country']:
        v = row[col]
        if type(v) is str and len(v.strip()) > 0:
            locations.append(v)

    return ", ".join(locations)
