import argparse
import random
import socket
import sys
import time
from datetime import datetime, timezone
import psutil
import requests
_prev_disk_io = None
_prev_net_io = None
_prev_swap = None

def collect_real_metrics(interval_sec: float) -> dict:
    global _prev_disk_io, _prev_net_io, _prev_swap
    metrics = {}
    metrics['завантаження_CPU_%'] = psutil.cpu_percent(interval=min(interval_sec, 1.0))
    metrics['nproc'] = psutil.cpu_count(logical=True) or 1
    try:
        load1, _, _ = psutil.getloadavg()
        metrics['load_average_1хв'] = round(load1, 2)
    except (AttributeError, OSError):
        pass
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            first_sensor = next(iter(temps.values()))
            if first_sensor:
                metrics['температура_CPU'] = round(first_sensor[0].current, 1)
    except (AttributeError, OSError):
        pass
    vm = psutil.virtual_memory()
    metrics['доступна_памʼять_%'] = round(100 - vm.percent, 1)
    swap = psutil.swap_memory()
    if _prev_swap is not None:
        delta_swap = abs(swap.sin - _prev_swap.sin) + abs(swap.sout - _prev_swap.sout)
        metrics['кількість_swap_операцій'] = delta_swap
    else:
        metrics['кількість_swap_операцій'] = 0
    _prev_swap = swap
    try:
        du = psutil.disk_usage('/')
        metrics['заповненість_диска_%'] = round(du.percent, 1)
    except OSError:
        pass
    try:
        io = psutil.disk_io_counters()
        if io is not None:
            if _prev_disk_io is not None:
                delta_ops = io.read_count - _prev_disk_io.read_count + (io.write_count - _prev_disk_io.write_count)
                iops = delta_ops / max(interval_sec, 1)
                metrics['IOPS_поточні'] = round(iops, 1)
            _prev_disk_io = io
    except (AttributeError, OSError):
        pass
    try:
        net = psutil.net_io_counters()
        if _prev_net_io is not None:
            delta_bytes = net.bytes_recv - _prev_net_io.bytes_recv
            mbps = delta_bytes * 8 / (1024 * 1024) / max(interval_sec, 1)
            metrics['вхідний_трафік_Mbps'] = round(mbps, 2)
        _prev_net_io = net
    except (AttributeError, OSError):
        pass
    try:
        conns = psutil.net_connections(kind='tcp')
        metrics['_active_conn_count'] = len(conns)
    except (psutil.AccessDenied, OSError):
        pass
    return metrics
ANOMALY_PROBABILITY = 0.004
_NUMERIC_HEALTHY_RANGE = {'тривалість_симптому_хв': (0, 3), 'критичність_сервісу': (1, 5), 'активні_зʼєднання_БД': (5, 30), 'max_pool_size': (100, 100), 'cache_hit_ratio': (85, 99), 'кількість_deadlocks_10хв': (0, 0), 'затримка_мережі_ms': (10, 22), 'затримка_мережі_baseline_ms': (15, 15), 'втрата_пакетів_%': (0, 0), 'DNS_час_резолвінгу_ms': (10, 80), 'трафік_baseline_Mbps': (50, 50), 'час_відгуку_HTTP_ms': (80, 200), 'час_відгуку_HTTP_baseline_ms': (120, 120), 'частка_TIME_WAIT_CLOSE_WAIT': (0.0, 0.2), 'IOPS_базова_лінія': (900, 1100), 'кількість_деградованих_сервісів': (0, 0), 'максимальний_fan_in': (1, 2), 'кількість_реплік': (2, 3), 'температура_CPU': (40, 75), 'IOPS_базова_лінія': (30, 80)}
_STATIC_CONFIG_FACTS = {'критичність_сервісу', 'max_pool_size', 'кількість_реплік', 'наявність_fallback', 'максимальний_fan_in', 'IOPS_базова_лінія', 'трафік_baseline_Mbps', 'затримка_мережі_baseline_ms', 'час_відгуку_HTTP_baseline_ms'}
_static_cache = {}
_BOOL_HEALTHY_DEFAULT = {'traceroute_аномалії': False, 'наявність_блокувань_deadlocks': False, 'наявність_fallback': True, 'наявні_циклічні_залежності': False, 'на_критичному_шляху': False}
_ENUM_HEALTHY_OVERRIDE = {'тренд_використання_RAM': 'стабільний', 'тренд_повільних_запитів': 'стабільний', 'тренд_черги_транзакцій': 'стабільний', 'тренд_розміру_БД': 'звичний'}

def _known_enum_values(fact_name: str, rules: list) -> list:
    values = set()
    for r in rules:
        for c in r.get('conditions', []):
            if c.get('fact') == fact_name and isinstance(c.get('value'), str):
                values.add(c['value'])
            if c.get('fact') == fact_name and isinstance(c.get('value'), list):
                values.update((v for v in c['value'] if isinstance(v, str)))
        for c in r.get('conclusions', []):
            if c.get('fact') == fact_name and isinstance(c.get('value'), str):
                values.add(c['value'])
    return sorted(values)

def generate_value(fact_name: str, spec: dict, rules: list, healthy_bias: bool=True):
    ftype = spec.get('type')
    is_anomaly = random.random() < ANOMALY_PROBABILITY
    if ftype == 'bool':
        default = _BOOL_HEALTHY_DEFAULT.get(fact_name, False)
        return not default if is_anomaly and healthy_bias else default
    if ftype == 'number':
        lo, hi = _NUMERIC_HEALTHY_RANGE.get(fact_name, (0, 100))
        if lo == hi:
            return lo
        return round(random.uniform(lo, hi), 2)
    if healthy_bias and (not is_anomaly) and (fact_name in _ENUM_HEALTHY_OVERRIDE):
        return _ENUM_HEALTHY_OVERRIDE[fact_name]
    values = _known_enum_values(fact_name, rules)
    if not values:
        return _ENUM_HEALTHY_OVERRIDE.get(fact_name)
    if healthy_bias and (not is_anomaly):
        healthy_like = [v for v in values if v in ('норма', 'стабільний', 'звичний', 'ациклічна')]
        if healthy_like:
            return healthy_like[0]
    return random.choice(values)

def build_payload(api_base: str, interval_sec: float) -> dict:
    facts_resp = requests.get(f'{api_base}/facts', timeout=10).json()
    rules_resp = requests.get(f'{api_base}/rules', timeout=10).json()
    real = collect_real_metrics(interval_sec)
    real.pop('_active_conn_count', None)
    payload = {}
    for spec in facts_resp:
        if spec.get('kind') != 'raw':
            continue
        name = spec['name']
        if name in real:
            payload[name] = real[name]
        elif name in _STATIC_CONFIG_FACTS:
            if name not in _static_cache:
                _static_cache[name] = generate_value(name, spec, rules_resp)
            if _static_cache[name] is not None:
                payload[name] = _static_cache[name]
        else:
            value = generate_value(name, spec, rules_resp)
            if value is not None:
                payload[name] = value
    return payload

def run(api_base: str, interval_sec: float, save_run: bool):
    hostname = socket.gethostname()
    print(f'Агент запущено: {hostname} -> {api_base}  (цикл {interval_sec:.0f} сек)')
    while True:
        cycle_start = time.time()
        try:
            payload = build_payload(api_base, interval_sec)
            body = {'facts': payload, 'include_trace': False, 'save_run': save_run, 'label': f'agent:{hostname} {datetime.now(timezone.utc).isoformat(timespec='seconds')}'}
            resp = requests.post(f'{api_base}/diagnose', json=body, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            stamp = datetime.now().strftime('%H:%M:%S')
            diagnoses = result.get('diagnoses', [])
            severity = result.get('severity')
            if diagnoses:
                print(f'[{stamp}] ⚠ {severity or '?'}  {', '.join(diagnoses)}')
            else:
                print(f'[{stamp}] ok  (показників надіслано: {len(payload)})')
        except requests.exceptions.RequestException as exc:
            stamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{stamp}] помилка з'єднання з {api_base}: {exc}")
        elapsed = time.time() - cycle_start
        time.sleep(max(0.0, interval_sec - elapsed))
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Агент моніторингу для системи діагностики')
    parser.add_argument('--url', default='http://localhost:8000/api', help='Базова адреса API, напр. https://xxxxx.trycloudflare.com/api')
    parser.add_argument('--interval', type=float, default=30.0, help='Інтервал циклу, секунди')
    parser.add_argument('--no-save', action='store_true', help='Не зберігати прогони в MongoDB')
    args = parser.parse_args()
    try:
        run(args.url, args.interval, save_run=not args.no_save)
    except KeyboardInterrupt:
        print('\nЗупинено користувачем.')
        sys.exit(0)
