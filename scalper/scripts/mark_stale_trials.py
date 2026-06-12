'''
Mark stale RUNNING/WAITING trials as FAIL so a study can be optimised,
analysed, or compacted again.

Trials are left RUNNING forever when optimisation workers are killed without
telling Optuna. Marking them FAIL keeps their row history and is ignored by
both TPE and study compaction — safer than deleting the rows by hand, which
trips over Optuna's child tables.

Only run this while no optimisation is active: a genuinely running trial is
indistinguishable from a stale one here.
'''
import logging

from optuna.trial import TrialState
from questionary import confirm, select

from utils import load_env, LOG_FORMAT, get_study_choices, load_study, make_rdb_storage

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def mark_stale_trials():
    study_choices = get_study_choices()
    if not study_choices:
        print('No studies found.')
        return

    study_name = select('Select study:', choices=study_choices).ask()
    if study_name is None:
        return

    storage = make_rdb_storage('mark_stale_trials')
    study = load_study(study_name, storage=storage)
    stale = [
        trial for trial in study.get_trials(deepcopy=False)
        if trial.state in (TrialState.RUNNING, TrialState.WAITING)
    ]
    if not stale:
        print(f'{study_name}: no RUNNING/WAITING trials — nothing to do.')
        return

    for trial in stale:
        print(f'  trial {trial.number} ({trial.state.name}, started {trial.datetime_start})')
    if not confirm(f'Mark {len(stale)} trial(s) in {study_name} as FAIL?').ask():
        print('Cancelled.')
        return

    for trial in stale:
        storage.set_trial_state_values(trial._trial_id, state=TrialState.FAIL)
    print(f'{study_name}: {len(stale)} trial(s) marked FAIL.')


if __name__ == '__main__':
    mark_stale_trials()
