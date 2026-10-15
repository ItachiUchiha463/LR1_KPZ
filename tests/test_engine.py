import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from inference_engine.engine import InferenceEngine
KB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'knowledge_base.json')
PASSED = []
FAILED = []

def check(name, condition, detail=''):
    if condition:
        PASSED.append(name)
        print(f'  [OK]   {name}')
    else:
        FAILED.append((name, detail))
        print(f'  [FAIL] {name}  {detail}')

def load_kb():
    with open(KB_PATH, encoding='utf-8') as f:
        return json.load(f)
HEALTHY = {'доступна_памʼять_%': 55, 'кількість_swap_операцій': 0, 'тренд_використання_RAM': 'стабільний', 'load_average_1хв': 1.0, 'nproc': 4, 'завантаження_CPU_%': 25, 'тренд_кількості_процесів': 'стабільно', 'тренд_кількості_потоків': 'стабільно', 'температура_CPU': 52, 'заповненість_диска_%': 40, 'IOPS_поточні': 900, 'IOPS_базова_лінія': 1000, 'тренд_росту_файлів': 'органічний', 'затримка_мережі_ms': 20, 'затримка_мережі_baseline_ms': 18, 'втрата_пакетів_%': 0, 'тренд_активних_зʼєднань': 'стабільний', 'частка_TIME_WAIT_CLOSE_WAIT': 0.1, 'DNS_час_резолвінгу_ms': 40, 'traceroute_аномалії': False, 'вхідний_трафік_Mbps': 100, 'трафік_baseline_Mbps': 90, 'час_відгуку_HTTP_ms': 120, 'час_відгуку_HTTP_baseline_ms': 110, 'активні_зʼєднання_БД': 20, 'max_pool_size': 100, 'тренд_повільних_запитів': 'стабільний', 'тренд_черги_транзакцій': 'стабільний', 'cache_hit_ratio': 95, 'наявність_блокувань_deadlocks': False, 'кількість_deadlocks_10хв': 0, 'тренд_розміру_БД': 'звичний', 'кількість_деградованих_сервісів': 0, 'максимальний_fan_in': 1, 'наявність_fallback': True, 'кількість_реплік': 3, 'наявні_циклічні_залежності': False, 'на_критичному_шляху': False, 'тривалість_симптому_хв': 2, 'критичність_сервісу': 3}

def scenario(**overrides):
    data = dict(HEALTHY)
    data.update(overrides)
    return data

def test_kb_validation(engine):
    print('\n--- Статична перевірка бази знань ---')
    problems = engine.validate_knowledge_base()
    summary = problems['summary']
    print(f'  правил: {summary['rules']}, фактів оголошено: {summary['facts_declared']}')
    check('немає невідомих фактів в умовах', not problems['unknown_facts_in_conditions'], str(problems['unknown_facts_in_conditions'][:5]))
    check('немає невідомих фактів у висновках', not problems['unknown_facts_in_conclusions'], str(problems['unknown_facts_in_conclusions'][:5]))
    check('немає дублікатів id правил', not problems['duplicate_rule_ids'], str(problems['duplicate_rule_ids']))
    check('немає правил без умов', not problems['rules_without_conditions'], str(problems['rules_without_conditions']))
    check('немає невідомих операторів', not problems['bad_operators'], str(problems['bad_operators']))
    check('немає недосяжних derived-фактів', not problems['unreachable_facts'], str(problems['unreachable_facts']))
    check('правил не менше 50 (вимога методички)', summary['rules'] >= 50, f'лише {summary['rules']}')
    check('правил не більше 150', summary['rules'] <= 150, f'аж {summary['rules']}')

def test_healthy(engine):
    print('\n--- Сценарій 1: усе в нормі ---')
    result = engine.run(HEALTHY)
    print(f'  ітерацій: {result.iterations}, спрацювало правил: {len(result.fired_rules)}')
    print(f'  діагнози: {result.diagnoses()}')
    check('немає діагнозів на здоровій системі', result.diagnoses() == [], str(result.diagnoses()))
    check('немає конфліктів', not result.conflicts, str(result.conflicts[:3]))
    check('немає помилок виконання', not result.errors, str(result.errors[:3]))
    check('усі вхідні факти розпізнані', not result.unknown_input_facts, str(result.unknown_input_facts))
    check('немає неподаних raw-фактів', not result.missing_raw_facts, str(result.missing_raw_facts))

def test_memory_leak(engine):
    print('\n--- Сценарій 2: критичний витік памʼяті ---')
    result = engine.run(scenario(**{'доступна_памʼять_%': 6, 'кількість_swap_операцій': 1500, 'тренд_використання_RAM': 'монотонно_зростає', 'тривалість_симптому_хв': 45, 'критичність_сервісу': 5}))
    print(f'  діагнози: {result.diagnoses()}')
    print(f'  критичність: {result.facts.get('критичність_проблеми')}')
    print(f'  рівень інциденту: {result.severity()}')
    check('виявлено memory_leak_critical', 'memory_leak_critical' in result.diagnoses(), str(result.diagnoses()))
    check('критичність проблеми = 4', result.facts.get('критичність_проблеми') == 4, str(result.facts.get('критичність_проблеми')))
    check('рівень інциденту SEV1', result.severity() == 'SEV1', str(result.severity()))
    check('тиск_на_памʼять = критичний', result.facts.get('тиск_на_памʼять') == 'критичний', str(result.facts.get('тиск_на_памʼять')))
    check('немає конфліктів', not result.conflicts, str(result.conflicts[:3]))
    layers = sorted({r['layer'] for r in result.fired_rules})
    print(f'  задіяні шари: {layers}')
    check('задіяно щонайменше 4 шари виводу', len(layers) >= 4, str(layers))
    order = [r['layer'] for r in result.fired_rules]
    first_layer2 = next((i for i, l in enumerate(order) if l == 2), None)
    layer1_before = [l for l in order[:first_layer2] if l == 1] if first_layer2 else []
    check('шар 1 спрацював раніше за шар 2 у трасуванні', first_layer2 is not None and len(layer1_before) > 0, f'порядок шарів: {order[:8]}')
    diag_rule = next((r for r in result.fired_rules if r['id'] == 'Діаг-01'), None)
    check('діагноз шару 2 спирається на виведений проміжний факт', diag_rule is not None and result.facts.get('тиск_на_памʼять') is not None and ('тиск_на_памʼять' not in HEALTHY), 'проміжний факт мусить бути виведеним, а не вхідним')

def test_multiple_diagnoses(engine):
    print('\n--- Сценарій 3: кілька незалежних проблем одночасно ---')
    result = engine.run(scenario(**{'доступна_памʼять_%': 8, 'кількість_swap_операцій': 400, 'тренд_використання_RAM': 'монотонно_зростає', 'заповненість_диска_%': 93, 'IOPS_поточні': 200, 'IOPS_базова_лінія': 1000, 'тренд_росту_файлів': 'швидкий', 'наявність_блокувань_deadlocks': True, 'кількість_deadlocks_10хв': 7, 'тренд_черги_транзакцій': 'монотонно_зростає', 'тривалість_симптому_хв': 30, 'критичність_сервісу': 4}))
    diags = result.diagnoses()
    print(f'  діагнозів знайдено: {len(diags)}')
    for d in diags:
        print(f'    - {d}')
    check('знайдено кілька діагнозів одночасно', len(diags) >= 3, f'лише {len(diags)}')
    check('серед них memory_leak_critical', 'memory_leak_critical' in diags)
    check('серед них проблема диска', any(('диск' in d for d in diags)), str(diags))
    check('серед них deadlock', any(('deadlock' in d for d in diags)), str(diags))
    check('критичність = максимум із проблем', result.facts.get('критичність_проблеми') == 4, str(result.facts.get('критичність_проблеми')))
    check('немає конфліктів', not result.conflicts, str(result.conflicts[:3]))

def test_cross_branch(engine):
    print('\n--- Сценарій 4: міжгрупове правило (CPU спирається на диск) ---')
    result = engine.run(scenario(**{'load_average_1хв': 12, 'nproc': 4, 'завантаження_CPU_%': 30, 'IOPS_поточні': 100, 'IOPS_базова_лінія': 1000}))
    print(f'  тиск_на_CPU: {result.facts.get('тиск_на_CPU')}')
    print(f'  стан_швидкодії_диска: {result.facts.get('стан_швидкодії_диска')}')
    print(f'  діагнози: {result.diagnoses()}')
    check('тиск_на_CPU = підозра_на_io_wait', result.facts.get('тиск_на_CPU') == 'підозра_на_io_wait', str(result.facts.get('тиск_на_CPU')))
    check('io_wait підтверджено через факт із гілки диска', 'io_wait_підтверджено_проблема_диска' in result.diagnoses(), str(result.diagnoses()))

def test_explanation(engine):
    print('\n--- Сценарій 5: пояснюваність (чому такий висновок) ---')
    result = engine.run(scenario(**{'доступна_памʼять_%': 6, 'кількість_swap_операцій': 900, 'тренд_використання_RAM': 'монотонно_зростає', 'тривалість_симптому_хв': 60, 'критичність_сервісу': 5}))
    chain = engine.explain(result, 'діагноз')
    print(f'  ланцюжок пояснення ({len(chain)} кроків):')
    for step in chain[:6]:
        indent = '    ' + '  ' * step['depth']
        print(f'{indent}{step['rule_id']}: {step['text'][:70]}')
    check('ланцюжок пояснення не порожній', len(chain) > 0)
    check('у ланцюжку є діагностичне правило', any((s['rule_id'].startswith('Діаг') for s in chain)))
    check('у ланцюжку є правило шару 1', any((s['rule_id'].startswith('Пр-') for s in chain)))
    first_rule = next((t for t in result.trace if t['type'] == 'rule'), None)
    has_numbers = first_rule and any(('=' in c['explanation'] for c in first_rule.get('conditions', [])))
    check('трасування містить фактичні значення умов', bool(has_numbers))

def test_severity_escalation(engine):
    print('\n--- Сценарій 6: ескалація рівня за тривалістю (шар 4) ---')
    base = {'стан_пулу_зʼєднань_dummy': None, 'активні_зʼєднання_БД': 95, 'max_pool_size': 100, 'тренд_повільних_запитів': 'стабільний', 'критичність_сервісу': 1}
    base.pop('стан_пулу_зʼєднань_dummy')
    fresh = engine.run(scenario(**base, **{'тривалість_симптому_хв': 3}))
    persistent = engine.run(scenario(**base, **{'тривалість_симптому_хв': 120}))
    print(f'  свіжий симптом:  базовий={fresh.facts.get('базовий_рівень')}, фінальний={fresh.severity()}')
    print(f'  стійкий симптом: базовий={persistent.facts.get('базовий_рівень')}, фінальний={persistent.severity()}')
    check('свіжий симптом: рівень не ескалюється', fresh.severity() == fresh.facts.get('базовий_рівень'), f'{fresh.severity()} vs {fresh.facts.get('базовий_рівень')}')
    check('стійкий симптом: рівень підвищено', persistent.severity() != persistent.facts.get('базовий_рівень') or persistent.facts.get('базовий_рівень') == 'SEV1', f'{persistent.severity()} vs {persistent.facts.get('базовий_рівень')}')

def test_unknown_input(engine):
    print('\n--- Сценарій 7: некоректні вхідні дані ---')
    result = engine.run({'доступна_памʼять_%': 10, 'кількість_swap_операцій': 5, 'тренд_використання_RAM': 'монотонно_зростає', 'вигаданий_факт_якого_немає': 42})
    print(f'  нерозпізнані вхідні факти: {result.unknown_input_facts}')
    print(f'  непоказані raw-факти: {len(result.missing_raw_facts)}')
    print(f'  діагнози: {result.diagnoses()}')
    check('нерозпізнаний факт виявлено', 'вигаданий_факт_якого_немає' in result.unknown_input_facts)
    check('система не впала на неповних даних', not result.errors, str(result.errors[:3]))
    check('гілка RAM усе одно дала діагноз', 'memory_leak_critical' in result.diagnoses(), str(result.diagnoses()))
    check('відсутні raw-факти зафіксовано', len(result.missing_raw_facts) > 0)

def test_determinism(engine):
    print('\n--- Сценарій 8: детермінованість (той самий вхід -> той самий вихід) ---')
    data = scenario(**{'доступна_памʼять_%': 7, 'кількість_swap_операцій': 100, 'тренд_використання_RAM': 'монотонно_зростає', 'заповненість_диска_%': 95, 'тренд_росту_файлів': 'швидкий'})
    r1 = engine.run(data)
    r2 = engine.run(data)
    check('діагнози однакові', sorted(r1.diagnoses()) == sorted(r2.diagnoses()))
    check('рівень інциденту однаковий', r1.severity() == r2.severity())
    check('кількість спрацювань однакова', len(r1.fired_rules) == len(r2.fired_rules))
    check('прогін не мутує базу знань', len(engine.rules) > 0 and all(('id' in r for r in engine.rules)))

def test_confidence_combination():
    print('\n--- Сценарій 9: комбінування впевненості (CF, формула MYCIN) ---')
    from inference_engine.working_memory import WorkingMemory
    wm = WorkingMemory({})
    cf1, crossed1 = wm.combine_diagnosis('тест_код', 0.6, 'Пр-А')
    check('одне правило (0.6) не перетинає поріг 0.9', not crossed1 and abs(cf1 - 0.6) < 1e-09, f'cf1={cf1}')
    cf2, crossed2 = wm.combine_diagnosis('тест_код', 0.6, 'Пр-Б')
    expected = 0.6 + 0.6 * (1 - 0.6)
    check('два незалежні підтвердження дають вищу сумарну впевненість', cf2 > cf1, f'cf1={cf1} cf2={cf2}')
    check('формула комбінування точна (CF1 + CF2*(1-CF1))', abs(cf2 - expected) < 1e-09, f'очікували {expected}, отримали {cf2}')
    check('двох по 0.6 (=0.84) ще НЕ досить для порогу підтвердження 0.9', not crossed2 and cf2 < 0.9, f'cf2={cf2}')
    cf3rd, crossed3rd = wm.combine_diagnosis('тест_код', 0.6, 'Пр-Г')
    check('три незалежні підтвердження перетинають поріг 0.9', crossed3rd and cf3rd >= 0.9, f'cf3rd={cf3rd}')
    cf3, _ = wm.combine_diagnosis('інший_код', 0.9, 'Пр-В')
    check('різні коди діагнозів комбінуються незалежно', abs(wm.diagnosis_cf['тест_код'] - cf3rd) < 1e-09 and wm.diagnosis_cf['інший_код'] == 0.9)

def test_diagnosis_catalog(engine):
    print('\n--- Сценарій 10: довідник діагнозів ---')
    report = engine.validate_knowledge_base()
    check('немає діагностичних правил з кодом поза довідником', not report['unknown_diagnosis_codes'], report['unknown_diagnosis_codes'])
    check('немає правил з некоректним rule_type', not report['bad_rule_types'], report['bad_rule_types'])
    diagnostic_rules = [r for r in engine.rules if r.get('rule_type') == 'diagnostic']
    check('є хоч одне діагностичне правило', len(diagnostic_rules) > 0)
    check('кожне діагностичне правило має код у довіднику engine.diagnoses', all((r['conclusions'][0]['value'] in engine.diagnoses for r in diagnostic_rules)))
    check('кожен запис довідника має назву, критичність і рекомендацію', all(('name' in d and 'criticality' in d and ('recommendation' in d) for d in engine.diagnoses.values())))

def test_diagnosis_tiers(engine):
    print('\n--- Сценарій 11: рівні відображення діагнозу (tiers) ---')
    result = engine.run(scenario(**{'доступна_памʼять_%': 6, 'кількість_swap_операцій': 500, 'тренд_використання_RAM': 'монотонно_зростає'}))
    memory_diag = next((d for d in result.diagnosis_details if d['code'] == 'memory_leak_critical'), None)
    check("двофакторний діагноз має tier 'проблема'", memory_diag is not None and memory_diag['tier'] == 'проблема', memory_diag)
    check('двофакторний діагноз впливає на критичність_проблеми', result.facts.get('критичність_проблеми') is not None)
    result2 = engine.run(scenario(**{'вхідний_трафік_Mbps': 900, 'трафік_baseline_Mbps': 90}))
    ddos_diag = next((d for d in result2.diagnosis_details if d['code'] == 'підозра_на_ddos_або_легітимний_пік'), None)
    check("однофакторний діагноз має tier 'можлива', не 'проблема'", ddos_diag is not None and ddos_diag['tier'] == 'можлива', ddos_diag)
    check('однофакторний діагноз (cf=0.6) НЕ впливає на критичність_проблеми', result2.facts.get('критичність_проблеми') is None)

def main():
    kb = load_kb()
    engine = InferenceEngine(kb)
    print('=' * 66)
    print('ТЕСТУВАННЯ МАШИНИ ВИВОДУ')
    print('=' * 66)
    test_kb_validation(engine)
    test_healthy(engine)
    test_memory_leak(engine)
    test_multiple_diagnoses(engine)
    test_cross_branch(engine)
    test_explanation(engine)
    test_severity_escalation(engine)
    test_unknown_input(engine)
    test_determinism(engine)
    test_confidence_combination()
    test_diagnosis_catalog(engine)
    test_diagnosis_tiers(engine)
    print('\n' + '=' * 66)
    print(f'ПРОЙДЕНО: {len(PASSED)}   ПРОВАЛЕНО: {len(FAILED)}')
    if FAILED:
        print('\nПровалені перевірки:')
        for name, detail in FAILED:
            print(f'  - {name}: {detail}')
        return 1
    print('Усі перевірки пройдено.')
    return 0
if __name__ == '__main__':
    sys.exit(main())
