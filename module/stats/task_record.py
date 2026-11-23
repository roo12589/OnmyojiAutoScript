# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
"""任务运行记录：SQLite 持久化与统计查询。

任务子进程在每次任务结束后调用 record_task_run() 写入一条记录；
Web 服务通过 query_* 系列函数读取聚合结果。
"""
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

from module.logger import logger

RETENTION_DAYS = 180

DB_DIR = Path.cwd() / 'data'
DB_PATH = DB_DIR / 'oas_task_stats.db'

_SCHEMA = """
CREATE TABLE IF NOT EXISTS task_run (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name   TEXT NOT NULL,
    task_name     TEXT NOT NULL,
    start_time    TEXT NOT NULL,
    end_time      TEXT NOT NULL,
    day           TEXT NOT NULL,
    duration      REAL NOT NULL,
    status        TEXT NOT NULL,
    error_type    TEXT,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_task_run_config_day  ON task_run(config_name, day);
CREATE INDEX IF NOT EXISTS idx_task_run_config_task ON task_run(config_name, task_name, day);
"""

_initialized = False
_SELECT_RECORD = (
    "id, task_name, start_time, end_time, duration, status, error_type, error_message"
)


def _connect() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn


def init_db() -> None:
    """建表（幂等）。失败时只记录日志，不阻断调用方。"""
    global _initialized
    if _initialized:
        return
    try:
        conn = _connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()
        _initialized = True
    except Exception as e:
        logger.warning(f'Init task stats database failed: {e}')


def _ensure_db() -> None:
    if not _initialized:
        init_db()


def _format_error(error_type: str | None, error_message: str | None) -> str | None:
    if error_type and error_message:
        return f'{error_type}: {error_message}'
    return error_type or error_message or None


def _record_to_dict(row: sqlite3.Row) -> dict:
    return {
        'id': row['id'],
        'task_name': row['task_name'],
        'start_time': row['start_time'],
        'end_time': row['end_time'],
        'duration': round(row['duration'] or 0, 1),
        'status': row['status'],
        'error': _format_error(row['error_type'], row['error_message']),
    }


def record_task_run(
        config_name: str,
        task_name: str,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        error_type: str | None = None,
        error_message: str | None = None,
) -> None:
    """写入一条任务运行记录。任何异常都不会向上抛出。"""
    try:
        _ensure_db()
        params = (
            config_name,
            task_name,
            start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time.strftime('%Y-%m-%d %H:%M:%S'),
            start_time.strftime('%Y-%m-%d'),
            max(0.0, round((end_time - start_time).total_seconds(), 3)),
            'success' if success else 'failed',
            error_type,
            error_message[:2000] if error_message else None,
        )
        sql = (
            'INSERT INTO task_run '
            '(config_name, task_name, start_time, end_time, day, duration, status, error_type, error_message) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        )
        for attempt in range(2):
            try:
                conn = _connect()
                try:
                    with conn:
                        conn.execute(sql, params)
                finally:
                    conn.close()
                return
            except sqlite3.OperationalError as e:
                if attempt == 0 and 'locked' in str(e).lower():
                    time.sleep(0.2)
                    continue
                raise
    except Exception as e:
        logger.warning(f'Record task run failed: {e}')


def prune_old_records(keep_days: int = RETENTION_DAYS) -> int:
    """删除早于 keep_days 的记录，返回删除行数。"""
    try:
        _ensure_db()
        cutoff = (datetime.now() - timedelta(days=keep_days)).strftime('%Y-%m-%d')
        conn = _connect()
        try:
            with conn:
                cursor = conn.execute('DELETE FROM task_run WHERE day < ?', (cutoff,))
            return cursor.rowcount
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'Prune task run records failed: {e}')
        return 0


def _clamp_days(days: int) -> int:
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 7
    return max(1, min(days, 365))


def _day_range(days: int) -> tuple[str, str, list[str]]:
    today = datetime.now().date()
    start = today - timedelta(days=days - 1)
    day_list = [(start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    return start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), day_list


def _summary(config_name: str, start_day: str, end_day: str) -> dict:
    sql = """
        SELECT COUNT(*) AS runs,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
               SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS failed,
               AVG(duration) AS avg_duration,
               SUM(duration) AS total_duration
        FROM task_run
        WHERE config_name = ? AND day BETWEEN ? AND ?
    """
    conn = _connect()
    try:
        row = conn.execute(sql, (config_name, start_day, end_day)).fetchone()
    finally:
        conn.close()
    runs = row['runs'] or 0
    success = row['success'] or 0
    failed = row['failed'] or 0
    return {
        'runs': runs,
        'success': success,
        'failed': failed,
        'success_rate': round(success / runs * 100, 1) if runs else 0.0,
        'avg_duration': round(row['avg_duration'] or 0, 1),
        'total_duration': round(row['total_duration'] or 0, 1),
    }


def _daily(config_name: str, start_day: str, end_day: str, day_list: list[str],
           task_name: str | None = None) -> list[dict]:
    sql = """
        SELECT day,
               COUNT(*) AS runs,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
               SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS failed,
               AVG(duration) AS avg_duration
        FROM task_run
        WHERE config_name = ? AND day BETWEEN ? AND ?
    """
    params: list = [config_name, start_day, end_day]
    if task_name:
        sql += ' AND task_name = ?'
        params.append(task_name)
    sql += ' GROUP BY day'

    conn = _connect()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    mapping = {
        row['day']: {
            'date': row['day'],
            'runs': row['runs'] or 0,
            'success': row['success'] or 0,
            'failed': row['failed'] or 0,
            'avg_duration': round(row['avg_duration'] or 0, 1),
        }
        for row in rows
    }
    return [mapping.get(day, {
        'date': day,
        'runs': 0,
        'success': 0,
        'failed': 0,
        'avg_duration': 0.0,
    }) for day in day_list]


def _task_stats(config_name: str, start_day: str, end_day: str) -> list[dict]:
    sql = """
        SELECT t.task_name,
               COUNT(*) AS runs,
               SUM(CASE WHEN t.status = 'success' THEN 1 ELSE 0 END) AS success,
               SUM(CASE WHEN t.status = 'failed'  THEN 1 ELSE 0 END) AS failed,
               AVG(t.duration) AS avg_duration,
               MAX(t.start_time) AS last_run,
               (SELECT t2.status
                  FROM task_run t2
                 WHERE t2.config_name = t.config_name AND t2.task_name = t.task_name
                 ORDER BY t2.start_time DESC, t2.id DESC
                 LIMIT 1) AS last_status
        FROM task_run t
        WHERE t.config_name = ? AND t.day BETWEEN ? AND ?
        GROUP BY t.task_name
        ORDER BY runs DESC, t.task_name ASC
    """
    conn = _connect()
    try:
        rows = conn.execute(sql, (config_name, start_day, end_day)).fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        runs = row['runs'] or 0
        success = row['success'] or 0
        result.append({
            'task_name': row['task_name'],
            'runs': runs,
            'success': success,
            'failed': row['failed'] or 0,
            'success_rate': round(success / runs * 100, 1) if runs else 0.0,
            'avg_duration': round(row['avg_duration'] or 0, 1),
            'last_run': row['last_run'],
            'last_status': row['last_status'],
        })
    return result


def _recent(config_name: str, start_day: str, end_day: str, limit: int = 20) -> list[dict]:
    sql = (
        f'SELECT {_SELECT_RECORD} FROM task_run '
        'WHERE config_name = ? AND day BETWEEN ? AND ? '
        'ORDER BY start_time DESC, id DESC LIMIT ?'
    )
    conn = _connect()
    try:
        rows = conn.execute(sql, (config_name, start_day, end_day, limit)).fetchall()
    finally:
        conn.close()
    return [_record_to_dict(row) for row in rows]


def query_overview(config_name: str, days: int = 7) -> dict:
    _ensure_db()
    days = _clamp_days(days)
    start_day, end_day, day_list = _day_range(days)

    today = datetime.now().strftime('%Y-%m-%d')
    today_summary = _summary(config_name, today, today)
    range_summary = _summary(config_name, start_day, end_day)

    return {
        'script_name': config_name,
        'days': days,
        'today': today_summary,
        'range': range_summary,
        'daily': _daily(config_name, start_day, end_day, day_list),
        'tasks': _task_stats(config_name, start_day, end_day),
        'recent': _recent(config_name, start_day, end_day),
    }


def query_task_daily(config_name: str, task_name: str, days: int = 14) -> dict:
    _ensure_db()
    days = _clamp_days(days)
    start_day, end_day, day_list = _day_range(days)
    return {
        'task_name': task_name,
        'daily': _daily(config_name, start_day, end_day, day_list, task_name=task_name),
    }


def query_records(
        config_name: str,
        task_name: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
) -> dict:
    _ensure_db()
    try:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        limit, offset = 50, 0

    where = ['config_name = ?']
    params: list = [config_name]
    if task_name:
        where.append('task_name = ?')
        params.append(task_name)
    if status in ('success', 'failed'):
        where.append('status = ?')
        params.append(status)
    if start_date:
        where.append('day >= ?')
        params.append(start_date)
    if end_date:
        where.append('day <= ?')
        params.append(end_date)
    where_sql = ' AND '.join(where)

    conn = _connect()
    try:
        total = conn.execute(
            f'SELECT COUNT(*) AS total FROM task_run WHERE {where_sql}', params
        ).fetchone()['total']
        rows = conn.execute(
            f'SELECT {_SELECT_RECORD} FROM task_run WHERE {where_sql} '
            'ORDER BY start_time DESC, id DESC LIMIT ? OFFSET ?',
            [*params, limit, offset],
        ).fetchall()
    finally:
        conn.close()

    return {
        'total': total or 0,
        'items': [_record_to_dict(row) for row in rows],
    }
