import json
from unittest.mock import patch

import pytest

from backtesting_engine.out_of_sample_evaluation import build_out_of_sample_command
from backtesting_engine._out_of_sample_worker import main as worker_main
from core.progress_callbacks import JsonEvaluationProgressCallback


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_worker
class TestOutOfSampleWorkerContract:
    def test_build_command_argv_round_trips_through_worker_main(self, capsys):
        '''
        The argv ``build_out_of_sample_command`` produces must parse cleanly
        inside the worker and reach ``evaluate_out_of_sample`` with the same
        typed values. If the JSON schema drifts on either side of the IPC
        boundary, this test fails.
        '''
        # Given
        cmd = build_out_of_sample_command(
            study_name='SmaStrategy_XXBTZGBP_20250101-20250401',
            num_sets=5,
            start=1700000000.0,
            end=1701000000.0,
            n_workers=2,
        )

        # When — the BE function is mocked so the test doesn't hit Postgres /
        # SQLite. The callback's .count stays at 0 because the mock doesn't tick.
        with patch(
            'backtesting_engine._out_of_sample_worker.evaluate_out_of_sample'
        ) as mock_run:
            worker_main(cmd[-1])

        # Then — values arrived at the BE function untransformed.
        mock_run.assert_called_once()
        kwargs = mock_run.call_args.kwargs
        assert kwargs['study_name'] == 'SmaStrategy_XXBTZGBP_20250101-20250401'
        assert kwargs['num_sets'] == 5
        assert kwargs['start'] == 1700000000.0
        assert kwargs['end'] == 1701000000.0
        assert kwargs['n_workers'] == 2
        assert isinstance(kwargs['progress_callback'], JsonEvaluationProgressCallback)

        # A DONE line landed on stdout; count is 0 because the mock didn't tick.
        last_line = capsys.readouterr().out.strip().splitlines()[-1]
        event, payload_json = last_line.split(' ', 1)
        assert event == 'DONE'
        assert json.loads(payload_json) == {'trials': 0}

    def test_done_payload_reflects_callback_tick_count(self, capsys):
        '''
        The DONE payload's ``trials`` field is the callback's own counter — it
        must reflect how many times the BE function actually invoked it, not the
        requested ``num_sets``. Mirrors the OOS-side semantics where some param
        sets may be skipped because they were already evaluated.
        '''
        cmd = build_out_of_sample_command('s', num_sets=5, start=1.0, end=2.0, n_workers=1)

        def tick_three_times(**kwargs):
            cb = kwargs['progress_callback']
            cb()
            cb()
            cb()

        with patch(
            'backtesting_engine._out_of_sample_worker.evaluate_out_of_sample',
            side_effect=tick_three_times,
        ):
            worker_main(cmd[-1])

        last_line = capsys.readouterr().out.strip().splitlines()[-1]
        event, payload_json = last_line.split(' ', 1)
        assert event == 'DONE'
        assert json.loads(payload_json) == {'trials': 3}

    def test_worker_rejects_payload_missing_a_required_field(self):
        '''
        :class:`OutOfSampleArgs` is frozen and required — missing keys must
        raise at the contract boundary rather than fail deep inside the BE call.
        '''
        bad_payload = json.dumps({
            'study_name': 's',
            'num_sets': 5,
            'start': 1.0,
            'end': 2.0,
            # n_workers deliberately omitted
        })
        with pytest.raises(TypeError, match='n_workers'):
            worker_main(bad_payload)
