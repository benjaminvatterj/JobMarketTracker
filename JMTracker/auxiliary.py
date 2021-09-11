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
