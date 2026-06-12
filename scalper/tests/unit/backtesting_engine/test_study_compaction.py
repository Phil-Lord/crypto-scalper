import optuna
import pytest

import backtesting_engine.study_compaction as study_compaction
from backtesting_engine.study_compaction import (
    COMPACTING_SUFFIX,
    CompactionError,
    SOURCE_TRIAL_ATTR,
    execute_compaction,
    plan_compaction,
)
from data_system.models.oos_window_aggregate_model import OosWindowAggregate
from data_system.models.out_of_sample_evaluation_model import OutOfSampleEvaluation
from data_system.repositories.out_of_sample_evaluation.out_of_sample_evaluation_repository import (
    OutOfSampleEvaluationRepository,
)
from utils.optuna_utils import load_study, StudyNotFoundError


STUDY_NAME = 'SmaStrategy_XXBTZGBP_20250101-20250401'


class FakeOosRepository(OutOfSampleEvaluationRepository):
    ''' In-memory stand-in recording remap calls; only compaction-facing methods are live. '''

    def __init__(self, trial_numbers: set[int] | None = None) -> None:
        self.trial_numbers = trial_numbers or set()
        self.remap_calls: list[tuple[str, dict[int, int]]] = []

    def add(self, evaluations: list[OutOfSampleEvaluation]) -> None:
        raise NotImplementedError

    def get_evaluated_trial_numbers(self, study_name: str, start: float, end: float) -> set[int]:
        raise NotImplementedError

    def get_trial_numbers(self, study_name: str) -> set[int]:
        return self.trial_numbers

    def remap_trial_numbers(self, study_name: str, mapping: dict[int, int]) -> None:
        self.remap_calls.append((study_name, mapping))

    def get(self, study_name: str, start: float, end: float) -> list[OutOfSampleEvaluation]:
        raise NotImplementedError

    def aggregate_windows(
        self, study_name: str, floor: float, drawdown_limit: float
    ) -> list[OosWindowAggregate]:
        raise NotImplementedError


def _seed_study(
    tmp_path,
    values: list[float],
    name: str = STUDY_NAME,
    direction: str = 'maximize',
    n_failed: int = 0,
) -> tuple[optuna.storages.RDBStorage, optuna.Study]:
    '''
    Build a real SQLite-backed study with one COMPLETE trial per value (trial
    numbers follow insertion order), each carrying a per-window ``trades_*``
    user attribute like the production objective writes. ``n_failed`` extra
    FAIL trials are appended after the completed ones.
    '''
    storage = optuna.storages.RDBStorage(url=f'sqlite:///{tmp_path}/optuna.db')
    study = optuna.create_study(study_name=name, storage=storage, direction=direction)
    for i, value in enumerate(values):
        study.add_trial(
            optuna.trial.create_trial(
                params={'sma_period': 100 + i},
                distributions={'sma_period': optuna.distributions.IntDistribution(1, 10_000)},
                value=value,
                state=optuna.trial.TrialState.COMPLETE,
                user_attrs={'trades_2025-01-01_2025-03-31': i},
            )
        )
    for _ in range(n_failed):
        study.add_trial(optuna.trial.create_trial(state=optuna.trial.TrialState.FAIL))
    return storage, study


def _wire_dependencies(
    mocker,
    storage: optuna.storages.RDBStorage,
    oos_repository: OutOfSampleEvaluationRepository,
) -> None:
    '''
    Point the module's default (production) dependencies at the test doubles:
    every storage build resolves to the SQLite-backed ``storage``, and the
    OOS repository constructor returns ``oos_repository``.
    '''
    mocker.patch.object(
        study_compaction, 'load_study',
        side_effect=lambda name, *args, **kwargs: load_study(name, storage=storage),
    )
    mocker.patch.object(study_compaction, 'make_rdb_storage', return_value=storage)
    mocker.patch.object(study_compaction, 'SQLAlchemyClient')
    mocker.patch.object(
        study_compaction, 'SQLAlchemyOutOfSampleEvaluationRepository',
        return_value=oos_repository,
    )


@pytest.mark.backtesting_engine
@pytest.mark.study_compaction
@pytest.mark.plan_compaction
class TestPlanCompaction:
    def test_raises_when_study_not_found(self, tmp_path, mocker):
        storage, _ = _seed_study(tmp_path, [1.0])
        _wire_dependencies(mocker, storage, FakeOosRepository())

        with pytest.raises(StudyNotFoundError):
            plan_compaction('missing_study')

    def test_raises_when_top_fraction_out_of_range(self, tmp_path, mocker):
        storage, _ = _seed_study(tmp_path, [1.0])
        _wire_dependencies(mocker, storage, FakeOosRepository())

        with pytest.raises(ValueError):
            plan_compaction(STUDY_NAME, top_fraction=1.0)

    def test_raises_when_running_trials_exist(self, tmp_path, mocker):
        storage, study = _seed_study(tmp_path, [float(i) for i in range(10)])
        study.ask()
        _wire_dependencies(mocker, storage, FakeOosRepository())

        with pytest.raises(CompactionError, match='running/waiting'):
            plan_compaction(STUDY_NAME, target_total=5)

    def test_raises_when_at_or_below_target(self, tmp_path, mocker):
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(10)])
        _wire_dependencies(mocker, storage, FakeOosRepository())

        with pytest.raises(CompactionError, match='nothing to compact'):
            plan_compaction(STUDY_NAME, target_total=10)

    def test_keeps_top_trials_for_maximise_direction(self, tmp_path, mocker):
        # Given values equal trial numbers, so the two highest are trials 8 and 9
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(10)])
        _wire_dependencies(mocker, storage, FakeOosRepository())

        # When keeping a 0.4 share of the target-5 budget from the top
        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.4)

        kept_numbers = {t.number for t in plan.kept_trials}
        assert plan.top_count == 2
        assert {8, 9} <= kept_numbers

    def test_keeps_top_trials_for_minimise_direction(self, tmp_path, mocker):
        storage, _ = _seed_study(
            tmp_path, [float(i) for i in range(10)], direction='minimize'
        )
        _wire_dependencies(mocker, storage, FakeOosRepository())

        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.4)

        kept_numbers = {t.number for t in plan.kept_trials}
        assert {0, 1} <= kept_numbers

    def test_force_keeps_oos_evaluated_trials_outside_top(self, tmp_path, mocker):
        # Given trial 0 is the worst trial but has an OOS evaluation
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(10)])
        _wire_dependencies(mocker, storage, FakeOosRepository(trial_numbers={0}))

        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.2)

        assert plan.oos_count == 1
        assert 0 in {t.number for t in plan.kept_trials}

    def test_oos_trials_already_in_top_are_not_double_counted(self, tmp_path, mocker):
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(10)])
        _wire_dependencies(mocker, storage, FakeOosRepository(trial_numbers={9}))

        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.2)

        assert plan.oos_count == 0
        assert plan.top_oos_count == 1
        assert len(plan.kept_trials) == 5

    def test_oos_trials_counted_separately_inside_and_outside_top(self, tmp_path, mocker):
        # Given trial 9 (best, lands in the top) and trial 0 (worst) both have OOS evaluations
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(10)])
        _wire_dependencies(mocker, storage, FakeOosRepository(trial_numbers={9, 0}))

        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.2)

        assert plan.top_oos_count == 1
        assert plan.oos_count == 1
        assert {9, 0} <= {t.number for t in plan.kept_trials}

    def test_random_sample_fills_to_target(self, tmp_path, mocker):
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(20)])
        _wire_dependencies(mocker, storage, FakeOosRepository())

        plan = plan_compaction(STUDY_NAME, target_total=10, top_fraction=0.2)

        assert len(plan.kept_trials) == 10
        assert plan.top_count + plan.oos_count + plan.random_count == 10

    def test_top_count_scales_with_target_not_study_size(self, tmp_path, mocker):
        # Given a study much larger than the target (the compaction use case),
        # the top share must not consume the whole budget — the random sample
        # is what preserves TPE's "bad" density.
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(50)])
        _wire_dependencies(mocker, storage, FakeOosRepository())

        plan = plan_compaction(STUDY_NAME, target_total=10, top_fraction=0.5)

        assert plan.top_count == 5
        assert plan.random_count == 5
        assert len(plan.kept_trials) == 10

    def test_excludes_failed_trials(self, tmp_path, mocker):
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(10)], n_failed=5)
        _wire_dependencies(mocker, storage, FakeOosRepository())

        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.2)

        assert plan.completed_count == 10
        assert plan.total_count == 15
        failed_numbers = set(range(10, 15))
        assert failed_numbers.isdisjoint({t.number for t in plan.kept_trials})

    def test_kept_trials_sorted_by_original_number(self, tmp_path, mocker):
        storage, _ = _seed_study(tmp_path, [float(9 - i) for i in range(10)])
        _wire_dependencies(mocker, storage, FakeOosRepository())

        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.2)

        numbers = [t.number for t in plan.kept_trials]
        assert numbers == sorted(numbers)


@pytest.mark.backtesting_engine
@pytest.mark.study_compaction
@pytest.mark.execute_compaction
class TestExecuteCompaction:
    @pytest.fixture
    def compacted(self, tmp_path, mocker) -> tuple[optuna.storages.RDBStorage, FakeOosRepository]:
        ''' Seed 10 trials, compact to 5, return (storage, fake OOS repo). '''
        storage, study = _seed_study(tmp_path, [float(i) for i in range(10)])
        study.set_user_attr('note', 'original study attr')
        oos_repository = FakeOosRepository(trial_numbers={0})
        _wire_dependencies(mocker, storage, oos_repository)
        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.4)
        execute_compaction(plan)
        return storage, oos_repository

    def test_compacted_study_keeps_name_and_trial_count(self, compacted):
        storage, _ = compacted

        study = optuna.load_study(study_name=STUDY_NAME, storage=storage)

        assert len(study.trials) == 5
        assert study.direction == optuna.study.StudyDirection.MAXIMIZE

    def test_no_leftover_studies_in_storage(self, compacted):
        storage, _ = compacted

        names = {s.study_name for s in optuna.get_all_study_summaries(storage)}

        assert names == {STUDY_NAME}

    def test_trials_renumbered_from_zero_and_tagged_with_source(self, compacted):
        storage, _ = compacted

        trials = optuna.load_study(study_name=STUDY_NAME, storage=storage).trials

        assert [t.number for t in trials] == [0, 1, 2, 3, 4]
        sources = [t.user_attrs[SOURCE_TRIAL_ATTR] for t in trials]
        assert sources == sorted(sources)
        assert {8, 9, 0} <= set(sources)  # Top two plus the OOS-forced trial.

    def test_per_window_user_attrs_dropped(self, compacted):
        storage, _ = compacted

        trials = optuna.load_study(study_name=STUDY_NAME, storage=storage).trials

        for trial in trials:
            assert set(trial.user_attrs) == {SOURCE_TRIAL_ATTR}

    def test_values_params_and_distributions_preserved(self, compacted):
        storage, _ = compacted

        trials = optuna.load_study(study_name=STUDY_NAME, storage=storage).trials

        for trial in trials:
            source = trial.user_attrs[SOURCE_TRIAL_ATTR]
            assert trial.value == float(source)  # Seeded value == original number.
            assert trial.params == {'sma_period': 100 + source}
            assert trial.distributions['sma_period'].high == 10_000

    def test_oos_rows_remapped_with_old_to_new_numbers(self, compacted):
        storage, oos_repository = compacted

        trials = optuna.load_study(study_name=STUDY_NAME, storage=storage).trials
        expected = {t.user_attrs[SOURCE_TRIAL_ATTR]: t.number for t in trials}

        assert oos_repository.remap_calls == [(STUDY_NAME, expected)]

    def test_study_user_attrs_copied(self, compacted):
        storage, _ = compacted

        study = optuna.load_study(study_name=STUDY_NAME, storage=storage)

        assert study.user_attrs == {'note': 'original study attr'}

    def test_stale_tmp_study_from_crashed_run_is_replaced(self, tmp_path, mocker):
        # Given a leftover __compacting study from a previous crashed run
        storage, _ = _seed_study(tmp_path, [float(i) for i in range(10)])
        optuna.create_study(study_name=STUDY_NAME + COMPACTING_SUFFIX, storage=storage)
        _wire_dependencies(mocker, storage, FakeOosRepository())
        plan = plan_compaction(STUDY_NAME, target_total=5, top_fraction=0.2)

        # When
        execute_compaction(plan)

        # Then
        names = {s.study_name for s in optuna.get_all_study_summaries(storage)}
        assert names == {STUDY_NAME}
        assert len(optuna.load_study(study_name=STUDY_NAME, storage=storage).trials) == 5
