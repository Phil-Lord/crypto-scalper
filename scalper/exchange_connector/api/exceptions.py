class KrakenApiError(Exception):
    '''Base exception for all Kraken API errors.'''
    pass


class KrakenTooManyRequestsError(KrakenApiError):
    def __init__(self, message: str = 'Kraken API rate limit exceeded.'):
        super().__init__(message)


class KrakenApiResponseError(KrakenApiError):
    '''Raised when Kraken API returns an error response.'''
    pass


class KrakenNetworkError(KrakenApiError):
    '''Raised when network request to Kraken API fails.'''
    pass


class KrakenParseError(KrakenApiError):
    '''Raised when API response cannot be parsed as JSON.'''
    pass
