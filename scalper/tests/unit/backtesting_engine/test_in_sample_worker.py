import json
from unittest.mock import patch

import pytest

from backtesting_engine.in_sample_evaluation import build_in_sample_command
from backtesting_engine._in_sample_worker import main as worker_main
from core.progress_callbacks import JsonTrialProgressCallback


@pytest.mark.backtesting_engine
@pytest.mark.in_sample_worker
class TestInSampleWorkerContract:
    def test_build_command_argv_round_trips_through_worker_main(self, capsys):
        '''
        The argv ``build_in_sample_command`` produces must parse cleanly inside
        the worker and reach ``run_in_sample_optimisation`` with the same typed
        values. If the JSON schema drifts on either side of the IPC boundary
        (a renamed field, a type change, a missing key), this test fails.

        This replaces the click-flag pinning the pre-WF14 scripts relied on.
        '''
        # Given
        cmd = build_in_sample_command(
            pair='BTCGBP',
            strategy_name='SmaStrategy',
            start=1700000000.0,
            end=1701000000.0,
            n_trials=7,
            n_jobs=1,
        )

        # When — call the worker's main with the JSON arg build_command produced.
        # The inner BE function is mocked so the test doesn't hit Optuna / SQLite.
        with patch('backtesting_engine._in_sample_worker.run_in_sample_optimisation') as mock_run:
            worker_main(cmd[-1])

        # Then — values arrived at the BE function untransformed.
        mock_run.assert_called_once()
        kwargs = mock_run.call_args.kwargs
        assert kwargs['pair'] == 'BTCGBP'
        assert kwargs['strategy_name'] == 'SmaStrategy'
        assert kwargs['start'] == 1700000000.0
        assert kwargs['end'] == 1701000000.0
        assert kwargs['n_trials'] == 7
        assert kwargs['n_jobs'] == 1
        assert isinstance(kwargs['progress_callback'], JsonTrialProgressCallback)

        # And a DONE line landed on stdout with the trial count.
        last_line = capsys.readouterr().out.strip().splitlines()[-1]
        event, payload_json = last_line.split(' ', 1)
        assert event == 'DONE'
        assert json.loads(payload_json) == {'trials': 7}

    def test_worker_rejects_payload_missing_a_required_field(self):
        '''
        :class:`InSampleArgs` is frozen and required — missing keys must raise
        at the contract boundary rather than fail deep inside the BE call.
        '''
        bad_payload = json.dumps({
            'pair': 'BTCGBP',
            'strategy_name': 'SmaStrategy',
            'start': 1.0,
            'end': 2.0,
            # n_trials and n_jobs deliberately omitted
        })
        with pytest.raises(TypeError, match='n_trials'):
            worker_main(bad_payload)
