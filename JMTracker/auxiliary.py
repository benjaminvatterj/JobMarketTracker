#! /bin/python3
import os
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


def validate_extension(url, extension, source):
    """Validate the url has the right extension

    Parameters
    ----------
    url : str
        the url to validate
    extension : str
        extension name, without period, lower-case
    source: str
        name of the source processing

    Returns
    -------
    status: bool
        False if failed the test
    message: str
        Message to show user if caught a failure
    """

    ext = os.path.splitext(url)[1][1:].lower().strip()
    extension = extension.lower().strip()
    if ext != extension:
        status = False
        message = f"The input file for {source} has extension {ext} " +\
            f"but expected {extension}!"
        return status, message

    return True, ''


def validator_generator(validators, source, arguments=None):
    """A utility function to concatenate and generate validators.
    Takes a list of different validator functions that take
    a single first argument to validate and optional argument
    thar are fed following.

    Parameters
    ----------
    validators : list of function
        validator to concatenate

    source: str
        the source being validated

    arguments : list, optional
        if provided will process in order for each validator. If the
        list element is a list or tuple will be fed as *arg if its a
        dictionary as **kwargs

    Returns
    -------
    function
        a concatenated validator function
    """
    if type(validators) is not list:
        raise ValueError("Validators has to be a list of functions")

    if arguments is None:
        arguments = [None] * len(validators)

    def _validate(x, validators=validators, arguments=arguments, source=source):
        """The concatenated validator"""
        total_message = []
        total_status = True

        for validator, args in zip(validators, arguments):
            if args is None:
                statuts, message = validator(x)
            elif type(args) is tuple or type(args) is list:
                status, message = validator(x, *args)
            elif type(args) is dict:
                status, message = validator(x, **args)
            else:
                raise ValueError(f"argumet type {type(args)} for validator is"
                                 " not allowed.")

            total_status = total_status and status
            total_message.append(message)

        if len(total_message) > 1:
            message = f"Validation for {source} failed for multiple reasons:\n"
            for n, m in enumerate(total_message):
                message += f"{n + 1:d}) {m}\n"
        else:
            message = total_message[0]

        return total_status, message

    return _validate


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
