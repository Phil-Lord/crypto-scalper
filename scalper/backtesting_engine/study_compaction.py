import copy
import logging
import random
from dataclasses import dataclass

import optuna
from optuna.storages._rdb.models import StudyModel
from optuna.trial import FrozenTrial, TrialState
from sqlalchemy import update
from sqlalchemy.orm import Session

from data_system import SQLAlchemyClient, SQLAlchemyOutOfSampleEvaluationRepository
from utils import load_study, make_rdb_storage

from .objective import WINDOW_TRADES_ATTR

logger = logging.getLogger(__name__)


LEGACY_TRADES_PREFIX = 'trades_'
'''
Prefix of the retired per-window trade-count user attributes (one attribute
per window per trial). Compaction folds them into a single
:data:`~backtesting_engine.objective.WINDOW_TRADES_ATTR` dict.
'''

SOURCE_TRIAL_ATTR = 'source_trial_number'
'''
User attribute written to every copied trial, holding its trial number in the
original study. Survives in the compacted study permanently, so the old→new
mapping is always recoverable even if a compaction run dies before remapping
the out-of-sample evaluation rows.
'''

COMPACTING_SUFFIX = '__compacting'
PRECOMPACT_SUFFIX = '__precompact'


class CompactionError(Exception):
    ''' Raised when a study cannot be compacted in its current state. '''


@dataclass(frozen=True)
class CompactionPlan:
    '''
    Selection of trials to survive a study compaction.

    Built by :func:`plan_compaction`; pass to :func:`execute_compaction` to
    apply. Holding the selection separately lets entry points show a summary
    and confirm before anything is mutated.

    Attributes:
        study_name (str): Optuna study to compact.
        total_count (int): All trials in the study before compaction,
            regardless of state (completed plus pruned/failed).
        completed_count (int): COMPLETE trials in the study before compaction.
        top_count (int): Trials kept from the top of the objective ranking
            (the ``top_fraction`` share of the target).
        top_oos_count (int): How many of the top trials have out-of-sample evaluations.
            Informational — they are kept via the top share either way.
        oos_count (int): Trials outside the top force-kept because they have
            out-of-sample evaluations.
        random_count (int): Uniform random sample kept from the remainder —
            TPE needs poor trials for its "bad" density, so these preserve
            coverage of already-explored dead regions.
        kept_trials (list[FrozenTrial]): The trials to copy, in original
            trial-number order.
    '''
    study_name: str
    total_count: int
    completed_count: int
    top_count: int
    top_oos_count: int
    oos_count: int
    random_count: int
    kept_trials: list[FrozenTrial]


def plan_compaction(
    study_name: str,
    target_total: int = 1500,
    top_fraction: float = 0.2,
) -> CompactionPlan:
    '''
    Select the trials a compaction of ``study_name`` would keep.

    Splits the ``target_total`` budget between the best trials by objective
    value (a ``top_fraction`` share) and a uniform random sample of the rest —
    TPE needs poor trials for its "bad" density, so the sample preserves
    coverage of already-explored regions regardless of how large the study
    has grown. Trials with an out-of-sample evaluation are always kept, drawn
    from the random share of the budget. Pruned and failed trials never are —
    in this project pruning marks invalid parameter combinations rejected
    before any backtest runs, so they are cheap to re-explore.

    :param target_total: Trial count to aim for after compaction. OOS-evaluated
        trials are always kept, even if they alone exceed the budget.
    :param top_fraction: Share of ``target_total`` kept from the top of the
        ranking, in ``(0, 1)``. The default is deliberately small: TPE's
        "good" density only ever uses the top 25 trials (Optuna's default
        gamma cap), so the top share exists for ranking/OOS analysis depth,
        and a large one skews the "bad" density toward elite regions.
    :raises StudyNotFoundError: If no study named ``study_name`` exists.
    :raises CompactionError: If the study has running/waiting trials or is
        already at or below ``target_total`` completed trials.
    '''
    if not 0 < top_fraction < 1:
        raise ValueError(f'top_fraction must be in (0, 1), got {top_fraction}')

    oos_repository = SQLAlchemyOutOfSampleEvaluationRepository(SQLAlchemyClient())

    study = load_study(study_name, application_name='compact_study')
    trials = study.get_trials(deepcopy=False)

    completed: list[FrozenTrial] = []
    for trial in trials:
        if trial.state == TrialState.COMPLETE:
            completed.append(trial)
        elif trial.state in (TrialState.RUNNING, TrialState.WAITING):
            raise CompactionError(
                f'Study {study_name!r} has running/waiting trial(s) — '
                f'finish or stop the optimisation before compacting.'
            )

    if len(completed) <= target_total:
        raise CompactionError(
            f'Study {study_name!r} has {len(completed)} completed trials, already at or '
            f'below the target of {target_total} — nothing to compact.'
        )

    maximises = study.direction == optuna.study.StudyDirection.MAXIMIZE
    ranked = sorted(completed, key=lambda t: t.value, reverse=maximises)

    top_count = max(1, round(target_total * top_fraction))
    top = ranked[:top_count]

    oos_evaluated_numbers = oos_repository.get_trial_numbers(study_name)
    oos_evaluated: list[FrozenTrial] = []
    sample_pool: list[FrozenTrial] = []
    for trial in ranked[top_count:]:
        (oos_evaluated if trial.number in oos_evaluated_numbers else sample_pool).append(trial)

    sample_size = min(max(0, target_total - top_count - len(oos_evaluated)), len(sample_pool))
    random_sample = random.sample(sample_pool, sample_size)

    kept = sorted(top + oos_evaluated + random_sample, key=lambda t: t.number)
    return CompactionPlan(
        study_name=study_name,
        total_count=len(trials),
        completed_count=len(completed),
        top_count=top_count,
        top_oos_count=sum(1 for trial in top if trial.number in oos_evaluated_numbers),
        oos_count=len(oos_evaluated),
        random_count=sample_size,
        kept_trials=kept,
    )


def execute_compaction(plan: CompactionPlan) -> None:
    '''
    Apply a :class:`CompactionPlan`: copy the kept trials into a fresh study
    under the same name and drop everything else.

    The copy reduces each trial's user attributes to :data:`SOURCE_TRIAL_ATTR`
    plus a single window-trade-counts dict (legacy per-window ``trades_*``
    attributes are folded into it), renumbers trials from 0, and remaps the
    out-of-sample evaluation rows in local SQLite to the new numbers (rows for
    dropped trials are deleted, so stale evaluations can't join against
    unrelated trials that reuse a number).

    Sequence: the kept trials are copied into a ``__compacting`` study first,
    then the original is renamed aside to ``__precompact`` and the copy
    promoted to the canonical name in one transaction, and only then is the
    original deleted — at no point does the data exist solely in memory. A
    crash mid-run leaves a suffixed study behind for manual recovery via
    ``scripts/delete_study.py``.

    :raises StudyNotFoundError: If the planned study no longer exists.
    '''
    storage = make_rdb_storage('compact_study')
    oos_repository = SQLAlchemyOutOfSampleEvaluationRepository(SQLAlchemyClient())

    tmp_name = plan.study_name + COMPACTING_SUFFIX
    old_name = plan.study_name + PRECOMPACT_SUFFIX

    original = load_study(plan.study_name, storage=storage)
    _delete_if_exists(storage, tmp_name)
    _delete_if_exists(storage, old_name)

    logger.info(f'Copying {len(plan.kept_trials)} trials into {tmp_name}...')
    tmp_study = optuna.create_study(
        study_name=tmp_name, storage=storage, directions=original.directions
    )
    for key, value in original.user_attrs.items():
        tmp_study.set_user_attr(key, value)
    tmp_study.add_trials(_strip_user_attrs(plan.kept_trials))

    mapping = _source_number_mapping(tmp_study)

    _swap_study_names(storage, plan.study_name, tmp_name, old_name)
    oos_repository.remap_trial_numbers(plan.study_name, mapping)

    logger.info(
        f'Deleting original study ({plan.total_count} trials, '
        f'{plan.completed_count} completed)...'
    )
    optuna.delete_study(study_name=old_name, storage=storage)
    logger.info(
        f'Compacted {plan.study_name}: {plan.total_count} -> {len(plan.kept_trials)} trials.'
    )


def _delete_if_exists(storage: optuna.storages.RDBStorage, study_name: str) -> None:
    try:
        optuna.delete_study(study_name=study_name, storage=storage)
        logger.warning(f'Deleted leftover study from a previous compaction: {study_name}')
    except KeyError:
        pass


def _strip_user_attrs(trials: list[FrozenTrial]) -> list[FrozenTrial]:
    '''
    Copy ``trials``, reducing each trial's user attributes to a
    :data:`SOURCE_TRIAL_ATTR` recording its original trial number, plus its
    window trade counts as a single dict attribute. Legacy per-window
    ``trades_*`` attributes — the format whose row-per-window bloat motivated
    compaction — are folded into the dict rather than dropped.
    '''
    stripped = []
    for trial in trials:
        clone = copy.deepcopy(trial)
        attrs: dict[str, int | dict[str, int]] = {SOURCE_TRIAL_ATTR: trial.number}
        counts = _window_trade_counts(trial)
        if counts:
            attrs[WINDOW_TRADES_ATTR] = counts
        clone.user_attrs = attrs
        stripped.append(clone)
    return stripped


def _window_trade_counts(trial: FrozenTrial) -> dict[str, int]:
    ''' The trial's window-trade-counts dict, merged with any legacy per-window attrs. '''
    legacy = {
        key.removeprefix(LEGACY_TRADES_PREFIX): value
        for key, value in trial.user_attrs.items()
        if key.startswith(LEGACY_TRADES_PREFIX)
    }
    return legacy | trial.user_attrs.get(WINDOW_TRADES_ATTR, {})


def _source_number_mapping(study: optuna.Study) -> dict[int, int]:
    ''' Original trial number → renumbered trial number, read back from storage. '''
    return {
        trial.user_attrs[SOURCE_TRIAL_ATTR]: trial.number
        for trial in study.get_trials(deepcopy=False)
    }


def _swap_study_names(
    storage: optuna.storages.RDBStorage,
    canonical: str,
    tmp_name: str,
    old_name: str,
) -> None:
    '''
    Retire the study named ``canonical`` to ``old_name`` and promote
    ``tmp_name`` to ``canonical``, in one transaction so a crash can't leave
    the canonical name dangling. Optuna has no rename API, so this updates the
    study rows directly. The compacted study must keep the exact original name
    because ``parse_study_name`` and the OOS evaluation rows key on it.
    '''
    with Session(storage.engine) as session:
        session.execute(
            update(StudyModel)
            .where(StudyModel.study_name == canonical)
            .values(study_name=old_name)
        )
        session.execute(
            update(StudyModel)
            .where(StudyModel.study_name == tmp_name)
            .values(study_name=canonical)
        )
        session.commit()
