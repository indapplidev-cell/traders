"""Trial-local state retaining the production causal opportunity rules."""
from threading import RLock
from app.engine_paper.scalping_opportunity_registry import ScalpingOpportunityRegistry


class ResearchOpportunityRegistry(ScalpingOpportunityRegistry):
    def __init__(self):
        self._lock = RLock()
        self._state = {}

    def _persist(self):
        pass
