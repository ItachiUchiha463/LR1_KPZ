from typing import Any, Dict, List, Optional
from .condition_evaluator import TRUE, FALSE, UNKNOWN, evaluate_all, ConditionError
from .working_memory import WorkingMemory
MAX_ITERATIONS = 100
DIAGNOSIS_CONFIRMED_THRESHOLD = 0.9
DIAGNOSIS_VISIBLE_THRESHOLD = 0.5

class InferenceResult:

    def __init__(self):
        self.facts: Dict[str, Any] = {}
        self.fired_rules: List[dict] = []
        self.trace: List[dict] = []
        self.conflicts: List[dict] = []
        self.errors: List[dict] = []
        self.iterations: int = 0
        self.missing_raw_facts: List[str] = []
        self.unknown_input_facts: List[str] = []
        self.diagnosis_details: List[dict] = []

    def diagnoses(self) -> List[str]:
        return [d['code'] for d in self.diagnosis_details]

    def severity(self) -> Optional[str]:
        return self.facts.get('рівень_інциденту')

    def to_dict(self) -> dict:
        return {'facts': self.facts, 'diagnoses': self.diagnoses(), 'diagnoses_detail': self.diagnosis_details, 'severity': self.severity(), 'problem_criticality': self.facts.get('критичність_проблеми'), 'fired_rules': self.fired_rules, 'trace': self.trace, 'conflicts': self.conflicts, 'errors': self.errors, 'iterations': self.iterations, 'missing_raw_facts': self.missing_raw_facts, 'unknown_input_facts': self.unknown_input_facts}

def _facts_used_in_conditions(conditions: List[dict]) -> List[str]:
    used = []
    for c in conditions:
        if c.get('fact'):
            used.append(c['fact'])
        if c.get('ref_fact'):
            used.append(c['ref_fact'])
    return used

class InferenceEngine:

    def __init__(self, knowledge_base: dict):
        self.facts_spec = knowledge_base.get('facts', {})
        self.diagnoses = knowledge_base.get('diagnoses', {})
        self.rules = [r for r in knowledge_base.get('rules', []) if r.get('enabled', True)]
        self.rules.sort(key=lambda r: (r.get('layer', 1), r.get('id', '')))

    def run(self, input_facts: Dict[str, Any]) -> InferenceResult:
        result = InferenceResult()
        wm = WorkingMemory(self.facts_spec)
        result.unknown_input_facts = wm.unknown_facts(input_facts)
        for name, value in input_facts.items():
            if name in self.facts_spec:
                wm.set_raw(name, value)
        for name, spec in self.facts_spec.items():
            if 'default' in spec:
                wm.set_default(name, spec['default'])
        already_fired = set()
        for iteration in range(1, MAX_ITERATIONS + 1):
            result.iterations = iteration
            changed = False
            for rule in self.rules:
                rid = rule['id']
                if rid in already_fired:
                    continue
                try:
                    state, details = evaluate_all(rule.get('conditions', []), wm)
                except ConditionError as exc:
                    result.errors.append({'where': f'правило {rid}', 'error': str(exc)})
                    already_fired.add(rid)
                    continue
                if state != TRUE:
                    continue
                condition_cf = 1.0
                used = _facts_used_in_conditions(rule.get('conditions', []))
                if used:
                    condition_cf = min((wm.get_fact_cf(f) for f in used))
                rule_cf = rule.get('cf', 1.0) * condition_cf
                rule_type = rule.get('rule_type', 'intermediate')
                if rule_type == 'diagnostic':
                    conclusion = rule['conclusions'][0]
                    code = conclusion['value']
                    new_cf, crossed = wm.combine_diagnosis(code, rule_cf, rid)
                    changed = True
                    already_fired.add(rid)
                    produced = [{'fact': 'діагноз', 'value': code, 'cf': round(rule_cf, 3)}]
                    if crossed:
                        diag_spec = self.diagnoses.get(code, {})
                        crit = diag_spec.get('criticality')
                        if crit is not None:
                            wm.assert_fact('критичність_проблеми', crit, rid)
                    result.fired_rules.append({'id': rid, 'branch': rule.get('branch'), 'layer': rule.get('layer'), 'text': rule.get('text', ''), 'iteration': iteration, 'produced': produced})
                    result.trace.append({'iteration': iteration, 'type': 'diagnostic', 'id': rid, 'layer': rule.get('layer'), 'branch': rule.get('branch'), 'text': rule.get('text', ''), 'conditions': details, 'produced': produced, 'rule_cf': round(rule_cf, 3), 'combined_cf': round(new_cf, 3)})
                    continue
                produced = []
                for conclusion in rule.get('conclusions', []):
                    fact, value = (conclusion['fact'], conclusion['value'])
                    if wm.assert_fact(fact, value, rid, cf=rule_cf):
                        produced.append({'fact': fact, 'value': value, 'cf': round(rule_cf, 3)})
                        changed = True
                already_fired.add(rid)
                if produced:
                    result.fired_rules.append({'id': rid, 'branch': rule.get('branch'), 'layer': rule.get('layer'), 'text': rule.get('text', ''), 'iteration': iteration, 'produced': produced})
                    result.trace.append({'iteration': iteration, 'type': 'rule', 'id': rid, 'layer': rule.get('layer'), 'branch': rule.get('branch'), 'text': rule.get('text', ''), 'conditions': details, 'produced': produced})
            if not changed:
                break
        result.facts = wm.snapshot()
        result.conflicts = wm.conflicts
        result.missing_raw_facts = wm.missing_raw_facts()
        result.diagnosis_details = self._build_diagnosis_details(wm)
        return result

    def _build_diagnosis_details(self, wm: WorkingMemory) -> List[dict]:
        items = []
        for code, cf in wm.diagnosis_cf.items():
            if cf < DIAGNOSIS_VISIBLE_THRESHOLD:
                continue
            spec = self.diagnoses.get(code, {})
            tier = 'проблема' if cf >= DIAGNOSIS_CONFIRMED_THRESHOLD else 'можлива'
            items.append({'code': code, 'name': spec.get('name', code), 'criticality': spec.get('criticality'), 'description': spec.get('description', ''), 'recommendation': spec.get('recommendation', ''), 'cf': round(cf, 3), 'tier': tier, 'sources': wm.diagnosis_sources(code)})
        items.sort(key=lambda d: d['cf'], reverse=True)
        return items

    def explain(self, result: InferenceResult, target_fact: str='діагноз') -> List[dict]:
        produced_by: Dict[str, List[dict]] = {}
        for entry in result.trace:
            for p in entry.get('produced', []):
                produced_by.setdefault(p['fact'], []).append(entry)
        chain: List[dict] = []
        visited = set()

        def walk(fact: str, depth: int=0):
            if fact in visited or depth > 10:
                return
            visited.add(fact)
            for entry in produced_by.get(fact, []):
                chain.append({'depth': depth, 'rule_id': entry['id'], 'type': entry['type'], 'text': entry.get('text') or entry.get('explanation', ''), 'produced': entry.get('produced', [])})
                for cond_detail in entry.get('conditions', []):
                    upstream = cond_detail['condition'].get('fact')
                    if upstream:
                        walk(upstream, depth + 1)
        walk(target_fact)
        return chain

    def validate_knowledge_base(self) -> dict:
        problems = {'unknown_facts_in_conditions': [], 'unknown_facts_in_conclusions': [], 'duplicate_rule_ids': [], 'unreachable_facts': [], 'rules_without_conditions': [], 'bad_operators': [], 'unknown_diagnosis_codes': [], 'bad_rule_types': []}
        valid_ops = {'<', '<=', '>', '>=', '==', '!=', 'in', 'not_in', 'is_true', 'is_false', 'contains'}
        valid_rule_types = {'intermediate', 'diagnostic'}
        seen_ids = set()
        produced_facts = set()
        used_facts = set()
        for rule in self.rules:
            rid = rule.get('id', '?')
            if rid in seen_ids:
                problems['duplicate_rule_ids'].append(rid)
            seen_ids.add(rid)
            if not rule.get('conditions'):
                problems['rules_without_conditions'].append(rid)
            rule_type = rule.get('rule_type', 'intermediate')
            if rule_type not in valid_rule_types:
                problems['bad_rule_types'].append({'rule': rid, 'rule_type': rule_type})
            for cond in rule.get('conditions', []):
                fact = cond.get('fact')
                used_facts.add(fact)
                if fact not in self.facts_spec:
                    problems['unknown_facts_in_conditions'].append({'rule': rid, 'fact': fact})
                if cond.get('op', '==') not in valid_ops:
                    problems['bad_operators'].append({'rule': rid, 'op': cond.get('op')})
                ref = cond.get('ref_fact')
                if ref:
                    used_facts.add(ref)
                    if ref not in self.facts_spec:
                        problems['unknown_facts_in_conditions'].append({'rule': rid, 'fact': ref})
            for conclusion in rule.get('conclusions', []):
                fact = conclusion.get('fact')
                produced_facts.add(fact)
                if fact not in self.facts_spec:
                    problems['unknown_facts_in_conclusions'].append({'rule': rid, 'fact': fact})
                if rule_type == 'diagnostic' and fact == 'діагноз':
                    code = conclusion.get('value')
                    if code not in self.diagnoses:
                        problems['unknown_diagnosis_codes'].append({'rule': rid, 'code': code})
                    produced_facts.add('критичність_проблеми')
        for fact in sorted(used_facts):
            spec = self.facts_spec.get(fact, {})
            if not spec:
                continue
            if spec.get('kind') == 'derived' and fact not in produced_facts:
                problems['unreachable_facts'].append(fact)
        problems['summary'] = {'rules': len(self.rules), 'facts_declared': len(self.facts_spec), 'diagnoses_declared': len(self.diagnoses), 'facts_used': len(used_facts), 'facts_produced': len(produced_facts), 'total_problems': sum((len(v) for k, v in problems.items() if isinstance(v, list)))}
        return problems
