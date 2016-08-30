class WslError(Exception):
    pass

class ParseError(WslError):
    pass

class FormatError(WslError):
    pass

class IntegrityError(WslError):
    pass
