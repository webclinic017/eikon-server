"""
Eikon server
"""
from datetime import date, timedelta
import json
import os
import urllib.parse

from dotenv import load_dotenv
import eikon as ek
from fastapi import FastAPI, HTTPException, Depends, Request
import pandas as pd


load_dotenv()

app = FastAPI()

ek.set_app_key(os.getenv("EIKON_REFINITIV_API_KEY"))

MAXIMUM_NUMBER_OF_REQUESTS = 10000
PREVIOUS_DATE = date.today() + timedelta(days=-1)
REQUEST_COUNTER = MAXIMUM_NUMBER_OF_REQUESTS


def verify_token(req: Request):
    """
    Checks the Authorization header contains the Eikon secret key.

    Parameters
    ----------
        req: a request

    Returns
    -------
        bool
            True is the Authorization header and the Eikon secret key match.
    """
    token = req.headers.get("Authorization")
    if token != os.getenv("EIKON_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


def with_error(data):
    """
    Adds an error of too many Eikon requests.

    Parameters
    ----------
    data: dict or list

    Returns
    -------
        dict
            A structure containing the data and the error.
    """
    global PREVIOUS_DATE, REQUEST_COUNTER  # pylint: disable=global-statement
    today = date.today()
    if today.day != PREVIOUS_DATE.day:
        REQUEST_COUNTER = 0
    PREVIOUS_DATE = today
    error = None
    if REQUEST_COUNTER >= MAXIMUM_NUMBER_OF_REQUESTS:
        error = {"code": "429", "message": "Too many requests, please try again later."}
    REQUEST_COUNTER += 1
    data = (
        json.loads(data.reset_index(level=0).to_json(orient="records"))
        if isinstance(data, pd.DataFrame)
        else data
    )
    print(f"Request {REQUEST_COUNTER} / {MAXIMUM_NUMBER_OF_REQUESTS}")
    return {"data": data, "error": error}


@app.get("/data/{instruments}/{fields}/")
def handler_get_data(  # pylint: disable=too-many-arguments
    instruments,
    fields,
    parameters=None,
    field_name: bool = False,
    raw_output: bool = False,
    debug: bool = False,
    authorized: bool = Depends(verify_token),
):
    """
    Returns a json with fields in columns and instruments as row index

    Parameters
    ----------
    instruments: string or list
        Single instrument or list of instruments to request.

    fields: string, dictionary or list of strings and/or dictionaries.
        List of fields to request.

    parameters: string or dictionary, optional
        Single global parameter key=value or dictionary of global parameters to request.

        Default: None

    field_name: boolean, optional
        Define if column headers are filled with field name or display names.

        If True value, field names will ube used as column headers. Otherwise, the full display name will be used.

        Default: False

    raw_output: boolean, optional
        By default the output is a pandas.DataFrame.

        Set raw_output=True to get data in Json format.

        Default: False

    debug: boolean, optional
        When set to True, the json request and response are printed. Default value is False

    Returns
    -------
        json
            With error and data fields. Data contains fields in columns and instruments as row index.
    """
    if not authorized:
        return {"data": None, "error": "Not autorized"}
    instruments = instruments.split(",")
    fields = fields.split(",")
    parameters = json.loads(urllib.parse.unquote_plus(parameters))
    try:
        data = ek.get_data(
            instruments=instruments,
            fields=fields,
            parameters=parameters,
            field_name=field_name,
            raw_output=raw_output,
            debug=debug,
        )
    except Exception as error:  # pylint: disable=broad-except
        return {"data": None, "error": {"code": -1, "message": str(error)}}
    if data and len(data) == 2:
        data, _ = data
    return with_error(data)


@app.get("/news_headlines/")
def handler_news_headlines(  # pylint: disable=too-many-arguments
    query="Topic:TOPALL and Language:LEN",
    count: int = 10,
    date_from=None,
    date_to=None,
    raw_output: bool = False,
    debug: bool = False,
    authorized: bool = Depends(verify_token),
):
    """
    Returns a list of news headlines

    Parameters
    ----------
    query: string, optional
        News headlines search criteria.
        The text can contain RIC codes, company names, country names and
        operators (AND, OR, NOT, IN, parentheses and quotes for explicit search…).

        Tip: Append 'R:' in front of RIC names to improve performance.

        Default: Top News written in English

    count: int, optional
        Max number of headlines retrieved.

        Value Range: [1-100].

        Default: 10

    date_from: string or datetime, optional
        Beginning of date range.

        String format is: '%Y-%m-%dT%H:%M:%S'. e.g. '2016-01-20T15:04:05'.

    date_to: string or datetime, optional
        End of date range.

        String format is: '%Y-%m-%dT%H:%M:%S'. e.g. '2016-01-20T15:04:05'.

    raw_output: boolean, optional
        Set this parameter to True to get the data in json format
        if set to False, the function will return a data frame.

        Default: False

    debug: bool, optional
        When set to True, the json request and response are printed.

        Default: False

    Returns
    -------
        json
            With error and data fields. Data contains news headlines with the following columns:

            - Index               : Timestamp of the publication time
            - version_created     : Date of the latest update on the news
            - text                : Text of the Headline
            - story_id            : Identifier to be used to retrieve the full story using the get_news_story function
            - source_code         : Second news identifier
    """
    if not authorized:
        return {"data": None, "error": "Not autorized"}
    try:
        data = ek.get_news_headlines(
            query=query,
            count=count,
            date_from=date_from,
            date_to=date_to,
            raw_output=raw_output,
            debug=debug,
        )
    except Exception as error:  # pylint: disable=broad-except
        return {"data": None, "error": {"code": -1, "message": str(error)}}
    return with_error(data)


@app.get("/news_story/{story_id}/")
def handler_news_story(
    story_id,
    raw_output: bool = False,
    debug: bool = False,
    authorized: bool = Depends(verify_token),
):
    """
    Return a single news story corresponding to the identifier provided in story_id

    Parameters
    ----------
    story_id: string
        The story id is a field you will find in every headline you retrieved with the function get_news_headlines.

    raw_output: boolean
        Set this parameter to True to get the data in json format
        if set to False, the function will return returns the story content.

        The default value is False.

    debug: boolean, optional
        When set to True, the json request and response are printed.
        Default: False
    """
    if not authorized:
        return {"data": None, "error": "Not autorized"}
    try:
        data = ek.get_news_story(story_id=story_id, raw_output=raw_output, debug=debug)
    except Exception as error:  # pylint: disable=broad-except
        return {"data": None, "error": {"code": -1, "message": str(error)}}
    return with_error(data)


@app.get("/symbology/{symbol}/")
def handler_symbology(  # pylint: disable=too-many-arguments
    symbol,
    from_symbol_type="RIC",
    to_symbol_type=None,
    raw_output: bool = False,
    debug: bool = False,
    best_match: bool = True,
    authorized: bool = Depends(verify_token),
):
    """
    Returns a list of instrument names converted into another instrument code.
    For example: convert SEDOL instrument names to RIC names

    Parameters
    ----------
    symbol: string or list of strings
        Single instrument or list of instruments to convert.

    from_symbol_type: string
        Instrument code to convert from.
        Possible values: 'CUSIP', 'ISIN', 'SEDOL', 'RIC', 'ticker', 'lipperID', 'IMO'
        Default: 'RIC'

    to_symbol_type: string or list
        Instrument code to convert to.
        Possible values: 'CUSIP', 'ISIN', 'SEDOL', 'RIC', 'ticker', 'lipperID', 'IMO', 'OAPermID'
        Default: None  (means all symbol types are requested)

    raw_output: boolean, optional
        Set this parameter to True to get the data in json format
        if set to False, the function will return a data frame
        Default: False

    debug: boolean, optional
        When set to True, the json request and response are printed.
        Default: False

    best_match: boolean, optional
        When set to True, only primary symbol is requested.
        When set to false, all symbols are requested
        Default: True

    Returns
    -------
        If raw_output is set to True, the data will be returned in the json format.
        If raw_output is False (default value) the data will be returned as a list of dict. Content:
            - columns : Symbol types
            - rows : Symbol requested
            - cells : the symbols (None if not found)
            - symbol : The requested symbol
    """
    if not authorized:
        return {"data": None, "error": "Not autorized"}
    try:
        data = ek.get_symbology(
            symbol=symbol,
            from_symbol_type=from_symbol_type,
            to_symbol_type=to_symbol_type,
            raw_output=raw_output,
            debug=debug,
            best_match=best_match,
        )
    except Exception as error:  # pylint: disable=broad-except
        return {"data": None, "error": {"code": -1, "message": str(error)}}
    return with_error(data)


@app.get("/timeseries/{rics}/")
def handler_timeseries(  # pylint: disable=too-many-arguments
    rics,
    fields="*",
    start_date=None,
    end_date=None,
    interval="daily",
    count=None,
    calendar=None,
    corax=None,
    normalize: bool = False,
    raw_output: bool = False,
    debug: bool = False,
    authorized: bool = Depends(verify_token),
):
    """
    Returns historical data on one or several RICs

    Parameters
    ----------
    rics: string or list of strings
        Single RIC or List of RICs to retrieve historical data for

    start_date: string or datetime.datetime or datetime.timedelta
        Starting date and time of the historical range.
        string format is: '%Y-%m-%dT%H:%M:%S'. e.g. '2016-01-20T15:04:05'.
        datetime.timedelta is negative number of day relative to datetime.now().
        Default: datetime.now() + timedelta(-100)
        You can use the helper function get_date_from_today, please see the usage in the examples section

    end_date: string or datetime.datetime or datetime.timedelta
        End date and time of the historical range.

        string format could be
            - '%Y-%m-%d' (e.g. '2017-01-20')
            - '%Y-%m-%dT%H:%M:%S' (e.g. '2017-01-20T15:04:05')
        datetime.timedelta is negative number of day relative to datetime.now().

        Default: datetime.now()

        You can use the helper function get_date_from_today, please see the usage in the examples section

    interval: string
        Data interval.
        Possible values: 'tick', 'minute', 'hour', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly' (Default 'daily')
        Default: 'daily'

    fields: string or list of strings
        Use this parameter to filter the returned fields set.
        Available fields: 'TIMESTAMP', 'VALUE', 'VOLUME', 'HIGH', 'LOW', 'OPEN', 'CLOSE', 'COUNT'
        By default all fields are returned.

    count: int, optional
        Max number of data points retrieved.

    calendar: string, optional
        Possible values: 'native', 'tradingdays', 'calendardays'.

    corax: string, optional
        Possible values: 'adjusted', 'unadjusted'

    normalize: boolean, optional
        If set to True, the function will return a normalized data frame with the following columns 'Date','Security','Field'.

        If the value of this parameter is False the returned data frame shape will depend on the number of rics and the number of fields in the response.

        There are three different shapes:
            - One ric and many fields
            - Many rics and one field
            - Many rics and many fields

        Default: False

        Remark: This parameter has a less precedence than the parameter rawOutput i.e. if rawOutput is set to True, the returned data will be the raw data and this parameter will be ignored

    raw_output: boolean, optional
        Set this parameter to True to get the data in json format
        if set to False, the function will return a data frame which shape is defined by the parameter normalize
        Default: False

    debug: boolean, optional
        When set to True, the json request and response are printed.
        Default: False
    """
    if not authorized:
        return {"data": None, "error": "Not autorized"}
    fields = urllib.parse.unquote_plus(fields).split(",")
    try:
        data = ek.get_timeseries(
            rics=rics,
            fields=fields,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            count=count,
            calendar=calendar,
            corax=corax,
            normalize=normalize,
            raw_output=raw_output,
            debug=debug,
        )
    except Exception as error:  # pylint: disable=broad-except
        return {"data": None, "error": {"code": -1, "message": str(error)}}
    return with_error(data)
