from datetime import date, timedelta
import json
import os
import urllib.parse

from dotenv import load_dotenv
import eikon as ek
from fastapi import FastAPI, HTTPException, Depends, Request
import pandas as pd


load_dotenv()

EIKON_SECRET_KEY = os.getenv('EIKON_SECRET_KEY')
MAXIMUM_NUMBER_OF_REQUESTS = 10000

app = FastAPI()

ek.set_app_key(os.getenv('EIKON_REFINITIV_API_KEY'))
previous_date = date.today() + timedelta(days=-1)
request_counter = MAXIMUM_NUMBER_OF_REQUESTS


def verify_token(req: Request):
    token = req.headers.get("Authorization")
    if token != EIKON_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    return True


def with_error(data):
    global previous_date, request_counter
    today = date.today()
    if today.day != previous_date.day:
        request_counter = 0
    previous_date = today
    error = None
    if request_counter >= MAXIMUM_NUMBER_OF_REQUESTS:
        error = {
            'code': '429',
            'message': 'Too many requests, please try again later.'
        }
    request_counter += 1
    data = json.loads(data.reset_index(level=0).to_json(orient='records')) if isinstance(
        data, pd.DataFrame) else data
    print(f'Request {request_counter} / {MAXIMUM_NUMBER_OF_REQUESTS}')
    return {'data': data, 'error': error}


@app.get('/data/{instruments}/{fields}/')
def handler_get_data(instruments, fields, parameters=None,
                     field_name: bool = False, raw_output: bool = False, debug: bool = False,
                     authorized: bool = Depends(verify_token)):
    if not authorized:
        return
    instruments = instruments.split(',')
    fields = fields.split(',')
    parameters = json.loads(urllib.parse.unquote_plus(parameters))
    try:
        data = ek.get_data(instruments=instruments, fields=fields, parameters=parameters,
                           field_name=field_name, raw_output=raw_output, debug=debug)
    except Exception as e:
        return {'data': None, 'error': {'code': -1, 'message': str(e)}}
    if data and len(data) == 2:
        data, _ = data
    return with_error(data)


@app.get('/news_headlines/')
def handler_news_headlines(query='Topic:TOPALL and Language:LEN', count: int = 10, date_from=None,
                           date_to=None, raw_output: bool = False, debug: bool = False,
                           authorized: bool = Depends(verify_token)):
    if not authorized:
        return
    try:
        data = ek.get_news_headlines(query=query, count=count, date_from=date_from,
                                     date_to=date_to, raw_output=raw_output, debug=debug)
    except Exception as e:
        return {'data': None, 'error': {'code': -1, 'message': str(e)}}
    return with_error(data)


@app.get('/news_story/{story_id}/')
def handler_news_story(story_id, raw_output: bool = False, debug: bool = False,
                       authorized: bool = Depends(verify_token)):
    if not authorized:
        return
    try:
        data = ek.get_news_story(
            story_id=story_id, raw_output=raw_output, debug=debug)
    except Exception as e:
        return {'data': None, 'error': {'code': -1, 'message': str(e)}}
    return with_error(data)


@app.get('/symbology/{symbol}/')
def handler_symbology(symbol, from_symbol_type='RIC', to_symbol_type=None, raw_output: bool = False, debug: bool = False, bestMatch: bool = True,
                      authorized: bool = Depends(verify_token)):
    if not authorized:
        return
    try:
        data = ek.get_symbology(symbol=symbol, from_symbol_type=from_symbol_type,
                                to_symbol_type=to_symbol_type, raw_output=raw_output, debug=debug, bestMatch=bestMatch)
    except Exception as e:
        return {'data': None, 'error': {'code': -1, 'message': str(e)}}
    return with_error(data)


@app.get('/timeseries/{rics}/')
def handler_timeseries(rics, fields='*', start_date=None, end_date=None,
                       interval='daily', count=None,
                       calendar=None, corax=None, normalize: bool = False, raw_output: bool = False, debug: bool = False,
                       authorized: bool = Depends(verify_token)):
    if not authorized:
        return
    fields = urllib.parse.unquote_plus(fields).split(',')
    try:
        data = ek.get_timeseries(rics=rics, fields=fields, start_date=start_date, end_date=end_date,
                                 interval=interval, count=count,
                                 calendar=calendar, corax=corax, normalize=normalize, raw_output=raw_output, debug=True)
    except Exception as e:
        return {'data': None, 'error': {'code': -1, 'message': str(e)}}
    return with_error(data)
