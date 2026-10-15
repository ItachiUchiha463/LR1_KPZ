from typing import Any, Dict, Tuple
TRUE = 'TRUE'
FALSE = 'FALSE'
UNKNOWN = 'UNKNOWN'

class ConditionError(Exception):
    pass

def _resolve_threshold(cond: dict, wm) -> Tuple[Any, str]:
    if 'ref_fact' in cond:
        ref = cond['ref_fact']
        if not wm.has(ref):
            return (None, f'{ref}=?')
        factor = cond.get('factor', 1.0)
        base = wm.get(ref)
        try:
            threshold = base * factor
        except TypeError:
            raise ConditionError(f"Факт '{ref}' має нечислове значення {base!r}, множення неможливе")
        return (threshold, f'{ref}({base})*{factor}={threshold:g}')
    if 'value' not in cond:
        raise ConditionError(f"В умові немає ні 'value', ні 'ref_fact': {cond}")
    return (cond['value'], repr(cond['value']))
_NUMERIC_OPS = {'<', '<=', '>', '>='}

def evaluate(cond: dict, wm) -> Tuple[str, str]:
    fact = cond.get('fact')
    op = cond.get('op', '==')
    if not fact:
        raise ConditionError(f"В умові не вказано 'fact': {cond}")
    if not wm.has(fact):
        return (UNKNOWN, f'{fact} ще не відомий')
    actual = wm.get(fact)
    if op == 'is_true':
        ok = bool(actual) is True
        return (TRUE if ok else FALSE, f'{fact}={actual}')
    if op == 'is_false':
        ok = bool(actual) is False
        return (TRUE if ok else FALSE, f'{fact}={actual}')
    if op == 'contains':
        if not isinstance(actual, (list, tuple, set)):
            raise ConditionError(f"Оператор 'contains' застосовано до не-списку: {fact}={actual!r}")
        ok = cond.get('value') in actual
        return (TRUE if ok else FALSE, f'{fact} містить {cond.get('value')!r}? {ok}')
    threshold, threshold_text = _resolve_threshold(cond, wm)
    if threshold is None:
        return (UNKNOWN, f'поріг залежить від невідомого факту ({threshold_text})')
    if op in ('in', 'not_in'):
        if not isinstance(threshold, (list, tuple, set)):
            raise ConditionError(f"Оператор '{op}' вимагає списку значень: {cond}")
        inside = actual in threshold
        ok = inside if op == 'in' else not inside
        return (TRUE if ok else FALSE, f'{fact}={actual!r} {op} {list(threshold)}')
    if op == '==':
        ok = actual == threshold
        return (TRUE if ok else FALSE, f'{fact}={actual!r} == {threshold_text}')
    if op == '!=':
        ok = actual != threshold
        return (TRUE if ok else FALSE, f'{fact}={actual!r} != {threshold_text}')
    if op in _NUMERIC_OPS:
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            raise ConditionError(f"Оператор '{op}' вимагає числа, а {fact}={actual!r}")
        if not isinstance(threshold, (int, float)):
            raise ConditionError(f"Оператор '{op}': поріг має бути числом, отримано {threshold!r}")
        ok = {'<': actual < threshold, '<=': actual <= threshold, '>': actual > threshold, '>=': actual >= threshold}[op]
        return (TRUE if ok else FALSE, f'{fact}={actual:g} {op} {threshold_text}')
    raise ConditionError(f"Невідомий оператор '{op}' в умові {cond}")

def evaluate_all(conditions, wm) -> Tuple[str, list]:
    details = []
    has_unknown = False
    for cond in conditions:
        state, explanation = evaluate(cond, wm)
        details.append({'condition': cond, 'state': state, 'explanation': explanation})
        if state == FALSE:
            return (FALSE, details)
        if state == UNKNOWN:
            has_unknown = True
    return (UNKNOWN if has_unknown else TRUE, details)
