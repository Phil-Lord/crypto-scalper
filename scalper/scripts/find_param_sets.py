from backtesting_engine import find_params


def find_param_sets():
    study_name = "PrecisionTrendStrategy_XXBTZGBP_20210101-20220101"
    find_params(study_name)


if __name__ == '__main__':
    find_param_sets()
