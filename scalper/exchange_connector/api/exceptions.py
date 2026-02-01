class KrakenTooManyRequestsError(Exception):
    def __init__(self):
        super().__init__('Kraken API rate limit exceeded.')
