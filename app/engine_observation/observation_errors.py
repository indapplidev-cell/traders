class ObservationError(RuntimeError):
    """Base observation failure."""


class ObservationDatabaseError(ObservationError):
    pass


class ObservationSchemaError(ObservationError):
    pass
