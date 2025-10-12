import click

from backtesting_engine import find_params


@click.command()
@click.option('--walk_forward', '-w', is_flag=True, help='Use walk-forward evaluation.')
def find_param_sets(walk_forward: bool):
    study_name = "PrecisionTrendStrategy_XXBTZGBP_20210101-20220101"
    results = find_params(study_name, walk_forward)
    print('\n')
    for result in results:
        print(result)


if __name__ == '__main__':
    find_param_sets()
