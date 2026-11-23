# This Python file uses the following encoding: utf-8
from fastapi import APIRouter, HTTPException

from module.logger import logger
from module.stats import task_record

stats_app = APIRouter(prefix='/statistics', tags=['statistics'])


def _check_days(days: int) -> None:
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail='days must be between 1 and 365')


def _check_script_name(script_name: str) -> str:
    script_name = (script_name or '').strip()
    if not script_name:
        raise HTTPException(status_code=422, detail='script_name is required')
    return script_name


@stats_app.get('/overview')
def statistics_overview(script_name: str, days: int = 7):
    script_name = _check_script_name(script_name)
    _check_days(days)
    try:
        return task_record.query_overview(script_name, days)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail='Failed to query statistics overview') from e


@stats_app.get('/tasks/daily')
def statistics_task_daily(script_name: str, task_name: str, days: int = 14):
    script_name = _check_script_name(script_name)
    if not (task_name or '').strip():
        raise HTTPException(status_code=422, detail='task_name is required')
    _check_days(days)
    try:
        return task_record.query_task_daily(script_name, task_name.strip(), days)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail='Failed to query task daily statistics') from e


@stats_app.get('/records')
def statistics_records(
        script_name: str,
        task_name: str = '',
        status: str = '',
        start_date: str = '',
        end_date: str = '',
        limit: int = 50,
        offset: int = 0,
):
    script_name = _check_script_name(script_name)
    status = (status or '').strip()
    if status and status not in ('success', 'failed'):
        raise HTTPException(status_code=422, detail='status must be success or failed')
    try:
        return task_record.query_records(
            config_name=script_name,
            task_name=task_name.strip() or None,
            status=status or None,
            start_date=start_date.strip() or None,
            end_date=end_date.strip() or None,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail='Failed to query task run records') from e
