import optuna
import pytest

from backtesting_engine.parameter_optimisation import (
    optimise,
    optimise_parameters,
)


@pytest.mark.backtesting_engine
@pytest.mark.parameter_optimisation
class TestOptimise:
    @pytest.fixture
    def study(self, mocker):
        return mocker.Mock(spec=optuna.study.Study)

    @pytest.fixture
    def engine(self, mocker):
        engine = mocker.Mock()
        engine.start = 1609459200.0
        engine.end = 1617235200.0
        return engine

    @pytest.fixture(autouse=True)
    def _patch_objective(self, mocker):
        mocker.patch('backtesting_engine.parameter_optimisation.get_objective')

    def test_passes_n_jobs_to_study_optimize(self, study, engine):
        # When
        optimise(n_trials=5, study=study, engine=engine, windows=[], param_grid={}, n_jobs=4)

        # Then
        assert study.optimize.call_args.kwargs['n_jobs'] == 4

    def test_defaults_n_jobs_to_minus_one(self, study, engine):
        # When
        optimise(n_trials=5, study=study, engine=engine, windows=[], param_grid={})

        # Then
        assert study.optimize.call_args.kwargs['n_jobs'] == -1

    def test_passes_user_callback_to_study_optimize(self, mocker, study, engine):
        # Given
        user_cb = mocker.Mock()

        # When
        optimise(
            n_trials=5, study=study, engine=engine, windows=[], param_grid={},
            progress_callback=user_cb,
        )

        # Then
        callbacks = study.optimize.call_args.kwargs['callbacks']
        assert user_cb in callbacks

    def test_passes_no_callbacks_when_none_provided(self, study, engine):
        # When
        optimise(n_trials=5, study=study, engine=engine, windows=[], param_grid={})

        # Then
        assert study.optimize.call_args.kwargs['callbacks'] == []


@pytest.mark.backtesting_engine
@pytest.mark.parameter_optimisation
class TestOptimiseParameters:
    @pytest.fixture
    def engine(self, mocker):
        engine = mocker.Mock()
        engine.start = 1609459200.0
        engine.end = 1617235200.0
        return engine

    @pytest.fixture(autouse=True)
    def _patches(self, mocker):
        mocker.patch('backtesting_engine.parameter_optimisation.create_windows', return_value=[])
        mocker.patch('backtesting_engine.parameter_optimisation.create_storage')
        mocker.patch('backtesting_engine.parameter_optimisation.create_study')
        mocker.patch('backtesting_engine.parameter_optimisation.validate_search_space')

    def test_forwards_n_jobs_to_optimise(self, mocker, engine):
        # Given
        optimise_mock = mocker.patch('backtesting_engine.parameter_optimisation.optimise')

        # When
        optimise_parameters(engine, {}, n_trials=10, n_jobs=2)

        # Then
        assert optimise_mock.call_args.args[5] == 2 or \
            optimise_mock.call_args.kwargs.get('n_jobs') == 2

    def test_forwards_progress_callback_to_optimise(self, mocker, engine):
        # Given
        optimise_mock = mocker.patch('backtesting_engine.parameter_optimisation.optimise')
        cb = mocker.Mock()

        # When
        optimise_parameters(engine, {}, n_trials=10, progress_callback=cb)

        # Then
        passed = optimise_mock.call_args.args[6] if len(optimise_mock.call_args.args) > 6 \
            else optimise_mock.call_args.kwargs.get('progress_callback')
        assert passed is cb

    def test_default_n_jobs_is_minus_one(self, mocker, engine):
        # Given
        optimise_mock = mocker.patch('backtesting_engine.parameter_optimisation.optimise')

        # When
        optimise_parameters(engine, {}, n_trials=10)

        # Then
        passed = optimise_mock.call_args.args[5] if len(optimise_mock.call_args.args) > 5 \
            else optimise_mock.call_args.kwargs.get('n_jobs')
        assert passed == -1
