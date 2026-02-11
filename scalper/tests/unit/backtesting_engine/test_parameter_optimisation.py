import pandas as pd
import pytest

from backtesting_engine.parameter_optimisation import create_windows


@pytest.mark.backtesting_engine
@pytest.mark.parameter_optimisation
class TestCreateWindows:
    def test_basic_three_month_window(self):
        # Given
        start = pd.Timestamp('2021-01-12').timestamp()
        end = pd.Timestamp('2021-04-12').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 1
        assert windows[0] == (
            pd.Timestamp('2021-01-12 00:00:00'),
            pd.Timestamp('2021-04-11 23:59:59')
        )

    def test_multiple_windows_with_warmup(self):
        ''' Test multiple windows with warmup period from second window onward. '''
        # Given
        start = pd.Timestamp('2021-01-10').timestamp()
        end = pd.Timestamp('2021-07-10').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 4
        # First window - no warmup
        assert windows[0] == (
            pd.Timestamp('2021-01-10 00:00:00'),
            pd.Timestamp('2021-04-09 23:59:59')
        )
        # Second window - with warmup (1 day before)
        assert windows[1] == (
            pd.Timestamp('2021-02-09 00:00:00'),  # Feb 10 - 1 day
            pd.Timestamp('2021-05-09 23:59:59')
        )
        # Third window - with warmup
        assert windows[2] == (
            pd.Timestamp('2021-03-09 00:00:00'),  # Mar 10 - 1 day
            pd.Timestamp('2021-06-09 23:59:59')
        )
        # Fourth window - with warmup
        assert windows[3] == (
            pd.Timestamp('2021-04-09 00:00:00'),  # Apr 10 - 1 day
            pd.Timestamp('2021-07-09 23:59:59')
        )

    def test_incomplete_window_handling(self):
        ''' Test that incomplete windows at period end are discarded. '''
        # Given
        start = pd.Timestamp('2021-01-10').timestamp()
        end = pd.Timestamp('2021-05-20').timestamp()  # Not a full 3 months from Feb 10

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 2  # Only two complete windows possible
        assert windows[0] == (
            pd.Timestamp('2021-01-10 00:00:00'),
            pd.Timestamp('2021-04-09 23:59:59')
        )
        assert windows[1] == (
            pd.Timestamp('2021-02-09 00:00:00'),  # Feb 10 - 1 day
            pd.Timestamp('2021-05-09 23:59:59')
        )

    def test_long_period_windows(self):
        ''' Test window creation for a longer period (6+ months). '''
        # Given
        start = pd.Timestamp('2021-01-15').timestamp()
        end = pd.Timestamp('2021-09-15').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 6
        # First window - no warmup
        assert windows[0] == (
            pd.Timestamp('2021-01-15 00:00:00'),
            pd.Timestamp('2021-04-14 23:59:59')
        )
        # Subsequent windows with warmup
        assert windows[1] == (
            pd.Timestamp('2021-02-14 00:00:00'),  # Feb 15 - 1 day
            pd.Timestamp('2021-05-14 23:59:59')
        )
        assert windows[2] == (
            pd.Timestamp('2021-03-14 00:00:00'),  # Mar 15 - 1 day
            pd.Timestamp('2021-06-14 23:59:59')
        )
        assert windows[3] == (
            pd.Timestamp('2021-04-14 00:00:00'),  # Apr 15 - 1 day
            pd.Timestamp('2021-07-14 23:59:59')
        )
        assert windows[4] == (
            pd.Timestamp('2021-05-14 00:00:00'),  # May 15 - 1 day
            pd.Timestamp('2021-08-14 23:59:59')
        )
        assert windows[5] == (
            pd.Timestamp('2021-06-14 00:00:00'),  # Jun 15 - 1 day
            pd.Timestamp('2021-09-14 23:59:59')
        )

    def test_month_end_dates(self):
        ''' Test window creation starting on month boundaries with different day counts. '''
        # Given
        start = pd.Timestamp('2021-10-31 15:30:45').timestamp()
        end = pd.Timestamp('2022-07-31 15:30:45').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 7

        # First window - no warmup
        assert windows[0] == (
            pd.Timestamp('2021-10-31 15:30:45'),
            pd.Timestamp('2022-01-31 15:30:44')  # 3 months from Oct 31 = Jan 31 (-1 second)
        )

        # Second window - logical start Nov 30 (Oct 31 + 1 month = Nov 30), with warmup
        assert windows[1] == (
            pd.Timestamp('2021-11-29 15:30:45'),  # Nov 30 - 1 day warmup
            pd.Timestamp('2022-02-28 15:30:44')   # 3 months from Nov 30 = Feb 28
        )

        # Third window - logical start Dec 30 (Nov 30 + 1 month), with warmup
        assert windows[2] == (
            pd.Timestamp('2021-12-29 15:30:45'),  # Dec 30 - 1 day warmup
            pd.Timestamp('2022-03-30 15:30:44')   # 3 months from Dec 30 = Mar 30
        )

        # Fourth window - logical start Jan 30, with warmup
        assert windows[3] == (
            pd.Timestamp('2022-01-29 15:30:45'),  # Jan 30 - 1 day warmup
            pd.Timestamp('2022-04-30 15:30:44')   # 3 months from Jan 30 = Apr 30
        )

        # Fifth window - logical start Feb 28 (Jan 30 + 1 month = Feb 28), with warmup
        assert windows[4] == (
            pd.Timestamp('2022-02-27 15:30:45'),  # Feb 28 - 1 day warmup
            pd.Timestamp('2022-05-28 15:30:44')   # 3 months from Feb 28 = May 28
        )

        # Sixth window - logical start Mar 28, with warmup
        assert windows[5] == (
            pd.Timestamp('2022-03-27 15:30:45'),  # Mar 28 - 1 day warmup
            pd.Timestamp('2022-06-28 15:30:44')   # 3 months from Mar 28 = Jun 28
        )

        # Seventh window - logical start Apr 28, with warmup
        assert windows[6] == (
            pd.Timestamp('2022-04-27 15:30:45'),  # Apr 28 - 1 day warmup
            pd.Timestamp('2022-07-28 15:30:44')   # 3 months from Apr 28 = Jul 28
        )

    def test_leap_year_start_on_feb29(self):
        ''' Window starting on Feb 29 in a leap year. '''
        # Given
        start = pd.Timestamp("2024-02-29").timestamp()
        end = pd.Timestamp("2024-05-30").timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 1
        assert windows[0] == (
            pd.Timestamp("2024-02-29 00:00:00"),
            pd.Timestamp("2024-05-28 23:59:59")
        )

    def test_leap_year_handling(self):
        ''' Test window creation spanning February in a leap year. '''
        # Given
        start = pd.Timestamp('2024-01-15').timestamp()
        end = pd.Timestamp('2024-07-15').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 4
        # First window - no warmup
        assert windows[0] == (
            pd.Timestamp('2024-01-15 00:00:00'),
            pd.Timestamp('2024-04-14 23:59:59')
        )
        # Window spanning February with warmup
        assert windows[1] == (
            pd.Timestamp('2024-02-14 00:00:00'),  # Feb 15 - 1 day
            pd.Timestamp('2024-05-14 23:59:59')
        )
        # Window including end of February
        assert windows[2] == (
            pd.Timestamp('2024-03-14 00:00:00'),  # Mar 15 - 1 day
            pd.Timestamp('2024-06-14 23:59:59')
        )
        # Last window
        assert windows[3] == (
            pd.Timestamp('2024-04-14 00:00:00'),  # Apr 15 - 1 day
            pd.Timestamp('2024-07-14 23:59:59')
        )

    def test_minimum_window_size(self):
        ''' Test that periods shorter than window_months are handled correctly. '''
        # Given
        start = pd.Timestamp('2021-01-01').timestamp()
        end = pd.Timestamp('2021-02-15').timestamp()

        # When / Then
        try:
            create_windows(start, end)
            assert False, "Expected ValueError for insufficient time range"
        except ValueError as e:
            assert str(e) == 'Time range must be at least 3 months for optimisation.'

    def test_window_start_and_end_at_specific_second(self):
        ''' Test window creation with start and end timestamps at specific seconds. '''
        # Given
        start = pd.Timestamp('2022-03-05 14:22:17').timestamp()
        # End is exactly 3 months later, same second
        end = pd.Timestamp('2022-06-05 14:22:17').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 1
        # Window should start at the exact second and end at the last second of the previous day
        assert windows[0] == (
            pd.Timestamp('2022-03-05 14:22:17'),
            pd.Timestamp('2022-06-05 14:22:16')
        )

    def test_window_start_and_end_at_specific_second_multiple_windows(self):
        ''' Test window creation with start and end timestamps at specific seconds. '''
        # Given
        start = pd.Timestamp('2022-03-05 14:22:17.5').timestamp()
        end = pd.Timestamp('2022-07-05 14:22:17.5').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 2
        assert windows[0] == (
            pd.Timestamp('2022-03-05 14:22:17.5'),
            pd.Timestamp('2022-06-05 14:22:16.5')
        )
        assert windows[1] == (
            pd.Timestamp('2022-04-04 14:22:17.5'),
            pd.Timestamp('2022-07-05 14:22:16.5')
        )

    def test_window_start_and_end_at_specific_second_midnight(self):
        ''' Test window creation with start and end timestamps at midnight, with second precision. '''
        # Given
        start = pd.Timestamp('2023-11-30 00:00:01.325').timestamp()
        end = pd.Timestamp('2024-02-29 00:00:01.831').timestamp()  # Leap year

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) == 1
        assert windows[0] == (
            pd.Timestamp('2023-11-30 00:00:01.325'),
            pd.Timestamp('2024-02-29 00:00:00.325')
        )
