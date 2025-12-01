class MissingTradesFileException(Exception):
    def __init__(self, pair):
        super().__init__(f"No file exists for the pair '{
            pair}' and 'create_if_missing' is set to False.")
