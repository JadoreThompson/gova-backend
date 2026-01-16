class MaxEmailVerificationAttemptsException(Exception):
    def __init__(self, msg: str, timeout: int):
        super().__init__(msg)
        self.timeout = timeout
