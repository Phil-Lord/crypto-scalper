'''
Compact an Optuna study to reduce TPE sampling cost and storage/analysis
reads on large studies.

Copies the top trials, every OOS-evaluated trial, and a uniform random sample
of the rest into a fresh study under the same name, then deletes the original.

Trial numbers restart from 0. Each kept trial records its original number in
the ``source_trial_number`` user attribute, and out-of-sample evaluation rows
in local SQLite are remapped to the new numbers automatically.
'''
import logging

from questionary import confirm, select, text

from backtesting_engine import CompactionError, execute_compaction, plan_compaction
from utils import load_env, LOG_FORMAT, get_study_choices, StudyNotFoundError

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def compact_study():
    study_choices = get_study_choices()
    if not study_choices:
        print('No studies found.')
        return

    study_name = select('Select study to compact:', choices=study_choices).ask()
    if study_name is None:
        return

    target_total = int(text('Target trial count after compaction:', default='1500').ask())
    top_fraction = float(
        text('Share of target kept from the top of the ranking:', default='0.5').ask())

    try:
        plan = plan_compaction(study_name, target_total, top_fraction)
    except (CompactionError, StudyNotFoundError, ValueError) as e:
        print(e)
        return

    kept = len(plan.kept_trials)
    print(
        f'{plan.study_name}: {plan.completed_count} completed trials -> keeping {kept} '
        f'(top {plan.top_count}, OOS-evaluated {plan.oos_count}, random {plan.random_count}).'
    )
    if plan.random_count == 0:
        print(
            'Warning: no room for a random sample — TPE loses its "bad" density coverage. '
            'Consider a larger target or smaller top fraction.'
        )
    print('Trial numbers restart from 0; OOS evaluations are remapped to the new numbers.')

    dropped = plan.completed_count - kept
    if not confirm(f'Compact {plan.study_name}? {dropped} trials are deleted permanently.').ask():
        print('Compaction cancelled.')
        return

    execute_compaction(plan)
    print(f'Study {plan.study_name} compacted: {plan.completed_count} -> {kept} trials.')


if __name__ == '__main__':
    compact_study()
