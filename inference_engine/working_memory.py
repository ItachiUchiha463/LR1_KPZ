from typing import Any, Dict, List, Optional, Tuple

class WorkingMemory:

    def __init__(self, fact_specs: Dict[str, dict]):
        self.fact_specs = fact_specs
        self._values: Dict[str, Any] = {}
        self._sources: Dict[str, List[str]] = {}
        self.conflicts: List[dict] = []
        self.fact_cf: Dict[str, float] = {}
        self.diagnosis_cf: Dict[str, float] = {}
        self._diagnosis_sources: Dict[str, List[str]] = {}

    def has(self, fact: str) -> bool:
        return fact in self._values

    def get(self, fact: str, default=None):
        return self._values.get(fact, default)

    def sources_of(self, fact: str) -> List[str]:
        return self._sources.get(fact, [])

    def snapshot(self) -> dict:
        return dict(self._values)

    def get_fact_cf(self, fact: str) -> float:
        return self.fact_cf.get(fact, 1.0)

    def aggregation_of(self, fact: str) -> str:
        spec = self.fact_specs.get(fact, {})
        return spec.get('aggregation', 'single')

    def set_raw(self, fact: str, value: Any) -> None:
        self._values[fact] = value
        self._sources.setdefault(fact, []).append('вхідні_дані')
        self.fact_cf[fact] = 1.0

    def set_default(self, fact: str, value: Any) -> None:
        if fact in self._values:
            return
        self._values[fact] = value
        self._sources.setdefault(fact, []).append('default')
        self.fact_cf[fact] = 1.0

    def assert_fact(self, fact: str, value: Any, source_rule: str, cf: float=1.0) -> bool:
        agg = self.aggregation_of(fact)
        if agg == 'collect':
            current = self._values.setdefault(fact, [])
            if value in current:
                return False
            current.append(value)
            self._sources.setdefault(fact, []).append(source_rule)
            self.fact_cf[fact] = cf
            return True
        if agg == 'max':
            current = self._values.get(fact)
            if current is not None and current >= value:
                return False
            self._values[fact] = value
            self._sources.setdefault(fact, []).append(source_rule)
            self.fact_cf[fact] = cf
            return True
        if fact in self._values:
            if self._sources.get(fact) == ['default']:
                self._values[fact] = value
                self._sources[fact] = [source_rule]
                self.fact_cf[fact] = cf
                return True
            if self._values[fact] != value:
                self.conflicts.append({'fact': fact, 'kept_value': self._values[fact], 'rejected_value': value, 'kept_by': self._sources.get(fact, ['?'])[0], 'rejected_by': source_rule})
            return False
        self._values[fact] = value
        self._sources.setdefault(fact, []).append(source_rule)
        self.fact_cf[fact] = cf
        return True

    def combine_diagnosis(self, code: str, cf: float, source_rule: str) -> Tuple[float, bool]:
        old = self.diagnosis_cf.get(code)
        new = cf if old is None else old + cf * (1 - old)
        crossed_09 = (old is None or old < 0.9) and new >= 0.9
        self.diagnosis_cf[code] = new
        self._diagnosis_sources.setdefault(code, []).append(source_rule)
        return (new, crossed_09)

    def diagnosis_sources(self, code: str) -> List[str]:
        return self._diagnosis_sources.get(code, [])

    def missing_raw_facts(self) -> List[str]:
        return sorted([name for name, spec in self.fact_specs.items() if spec.get('kind') == 'raw' and name not in self._values])

    def unknown_facts(self, provided: Dict[str, Any]) -> List[str]:
        return sorted([k for k in provided if k not in self.fact_specs])
