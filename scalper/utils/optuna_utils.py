import logging
from dataclasses import dataclass
from enum import Enum

import optuna
import pandas as pd
from questionary import Choice

from utils import OptunaConfig


logger = logging.getLogger(__name__)


STUDY_NAME_FORMAT = '{Strategy}_{KrakenPair}_{YYYYMMDD-YYYYMMDD}'


class StudyDirection(str, Enum):
    ''' Optimisation direction for an Optuna study. '''
    MAXIMIZE = 'maximize'
    MINIMIZE = 'minimize'


class StudyNotFoundError(Exception):
    '''
    Raised when a study name has no corresponding record in Optuna storage.

    Distinguishes the expected "not created yet" state — e.g. the UI's
    optimistic placeholder row before the in-sample subprocess reaches
    ``create_study`` — from genuine storage errors, so callers can degrade
    quietly rather than logging a failure.
    '''

    def __init__(self, study_name: str) -> None:
        super().__init__(f'Optuna study does not exist in storage: {study_name!r}')
        self.study_name = study_name


@dataclass(frozen=True)
class ParsedStudyName:
    '''
    Decoded fields of a canonical Optuna study name.

    See :data:`STUDY_NAME_FORMAT` for the encoded shape and
    :func:`create_study_name` / :func:`parse_study_name` for the conversion.

    Attributes:
        strategy (str): Strategy class name, e.g. ``'SmaStrategy'``.
        kraken_pair (str): Kraken-format pair, e.g. ``'XXBTZGBP'``.
        start_ts (float): In-sample window start as a Unix second timestamp.
        end_ts (float): In-sample window end as a Unix second timestamp.

    Note:
        The format encodes dates at day resolution (``YYYYMMDD``), so the
        timestamps round to midnight UTC. Round-tripping a non-midnight
        timestamp through ``create_study_name`` and back loses the
        time-of-day component.
    '''
    strategy: str
    kraken_pair: str
    start_ts: float
    end_ts: float


@dataclass(frozen=True)
class StudySummary:
    '''
    Summary row for an Optuna study.

    Attributes:
        name (str): Optuna study name (unique within the storage).
        pair (str): Trading pair parsed from the study name. Empty for legacy
            or hand-renamed studies that don't match the canonical shape.
        strategy (str): Strategy class name parsed from the study name.
            Empty for non-conforming names.
        trial_count (int): Total trials recorded against the study.
        best_is (float | None): Best in-sample objective value, or ``None`` if
            the study has no completed trial yet.
        direction (StudyDirection): Optimisation direction.
    '''
    name: str
    pair: str
    strategy: str
    trial_count: int
    best_is: float | None
    direction: StudyDirection


def create_study_name(strategy_name: str, kraken_pair: str, start_ts: float, end_ts: float) -> str:
    '''
    Build the canonical Optuna study name for a backtest configuration.

    Produces a string in the :data:`STUDY_NAME_FORMAT` shape.

    :param strategy_name: Strategy class name, e.g. ``'SmaStrategy'``.
    :param kraken_pair: Kraken-format pair, e.g. ``'XXBTZGBP'``.
    :param start_ts: In-sample window start as a Unix second timestamp.
    :param end_ts: In-sample window end as a Unix second timestamp.
    '''
    start_str = pd.to_datetime(start_ts, unit='s').strftime('%Y%m%d')
    end_str = pd.to_datetime(end_ts, unit='s').strftime('%Y%m%d')
    return f'{strategy_name}_{kraken_pair}_{start_str}-{end_str}'


def parse_study_name(study_name: str) -> ParsedStudyName:
    '''
    Inverse of :func:`create_study_name`. Extracts strategy, Kraken pair, and
    the encoded date window so downstream consumers don't have to ask twice.

    :return: A :class:`ParsedStudyName` with the four encoded fields.
    :raises ValueError: If ``study_name`` doesn't match :data:`STUDY_NAME_FORMAT`.
    '''
    parts = study_name.rsplit('_', 2)
    if len(parts) != 3:
        raise ValueError(
            f'Study name does not match canonical format '
            f'{STUDY_NAME_FORMAT}: {study_name!r}'
        )
    strategy, kraken_pair, date_range = parts

    try:
        start_str, end_str = date_range.split('-', 1)
        start_ts = pd.to_datetime(start_str, format='%Y%m%d').timestamp()
        end_ts = pd.to_datetime(end_str, format='%Y%m%d').timestamp()
    except (ValueError, TypeError) as e:
        raise ValueError(
            f'Study name does not match canonical format '
            f'{STUDY_NAME_FORMAT}: {study_name!r}'
        ) from e
    return ParsedStudyName(
        strategy=strategy,
        kraken_pair=kraken_pair,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def _make_rdb_storage(application_name: str = 'scalper') -> optuna.storages.RDBStorage:
    '''
    Build an :class:`optuna.storages.RDBStorage` against the project's
    configured Optuna database.

    - Tags the Postgres connection with ``application_name`` so call sites
        remain distinguishable in ``pg_stat_activity``.
    - Enables ``keepalives`` / ``pool_pre_ping`` to survive idle/dropped
        connections under long-running UI sessions.
    '''
    return optuna.storages.RDBStorage(
        url=OptunaConfig.DB_URL,
        engine_kwargs={
            'pool_pre_ping': True,
            'connect_args': {
                'application_name': application_name,
                'keepalives_idle': 30
            }
        }
    )


def load_study(study_name: str, application_name: str = 'scalper') -> optuna.Study:
    '''
    Load an Optuna study from the project's configured RDB storage.

    :param application_name: Postgres ``application_name`` to tag the
        connection with. Defaults to ``'scalper'``.
    :raises StudyNotFoundError: If no study with ``study_name`` exists in storage.
    '''
    logger.info(f'Loading study: {study_name}')
    storage = _make_rdb_storage(application_name)
    try:
        return optuna.load_study(study_name=study_name, storage=storage)
    except KeyError as e:
        # Optuna's RDBStorage raises a bare KeyError('Record does not exist.')
        # when the study name isn't in storage. Translate to discern from real failures.
        raise StudyNotFoundError(study_name) from e


def list_studies() -> list[StudySummary]:
    '''
    Return a :class:`StudySummary` for every Optuna study in storage.

    Pair and strategy are parsed from the study name via :func:`parse_study_name`;
    studies that don't match :data:`STUDY_NAME_FORMAT` are returned with
    empty pair/strategy strings.
    '''
    storage = _make_rdb_storage()
    summaries = optuna.get_all_study_summaries(storage)
    return [_to_study_summary(summary) for summary in summaries]


def get_study_choices() -> list[Choice]:
    ''' Wrap :func:`list_studies` for interactive Questionary CLI prompts. '''
    return [
        Choice(title=f'{summary.name} {summary.trial_count}', value=summary.name)
        for summary in list_studies()
    ]


def _to_study_summary(summary: optuna.study.StudySummary) -> StudySummary:
    try:
        parsed = parse_study_name(summary.study_name)
        strategy = parsed.strategy
        pair = parsed.kraken_pair
    except ValueError:
        strategy = ''
        pair = ''

    direction = (
        StudyDirection.MAXIMIZE
        if summary.direction == optuna.study.StudyDirection.MAXIMIZE
        else StudyDirection.MINIMIZE
    )
    best_is = summary.best_trial.value if summary.best_trial is not None else None

    return StudySummary(
        name=summary.study_name,
        pair=pair,
        strategy=strategy,
        trial_count=summary.n_trials,
        best_is=best_is,
        direction=direction,
    )
