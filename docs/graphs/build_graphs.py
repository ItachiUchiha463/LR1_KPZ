import json
import os
with open('../../data/knowledge_base.json', encoding='utf-8') as f:
    kb = json.load(f)
FACTS = kb['facts']
RULES = kb['rules']
branch_color = {'RAM': '#9FE1CB', 'CPU': '#F0997B', 'Диск': '#F5C4B3', 'Мережа': '#B5D4F4', 'БД': '#C0DD97', 'Каскади': '#AFA9EC', 'СППР': '#E8D48A'}
branch_text = {'RAM': '#085041', 'CPU': '#712B13', 'Диск': '#712B13', 'Мережа': '#0C447C', 'БД': '#27500A', 'Каскади': '#3C3489', 'СППР': '#5C4A0A'}

def cond_ref_facts(cond):
    facts = [cond['fact']]
    if cond.get('ref_fact'):
        facts.append(cond['ref_fact'])
    return facts
by_branch = {}
for rule in RULES:
    by_branch.setdefault(rule['branch'], []).append(rule)
os.makedirs('.', exist_ok=True)
summary = []
for branch, rules in by_branch.items():
    color = branch_color.get(branch, '#eee')
    tcolor = branch_text.get(branch, '#000')
    node_facts = set()
    for r in rules:
        for c in r['conditions']:
            node_facts.update(cond_ref_facts(c))
        for c in r['conclusions']:
            node_facts.add(c['fact'])
    dot = ['digraph G {']
    dot.append('rankdir=LR; splines=true; nodesep=0.3; ranksep=0.9;')
    dot.append('node [fontname="Helvetica"];')
    dot.append('edge [fontname="Helvetica", fontsize=7, color="#888780", arrowsize=0.55];')
    for fact in node_facts:
        fc, tc = (color, tcolor)
        if fact == 'діагноз':
            fc, tc = ('#F09595', '#501313')
        elif fact == 'рівень_інциденту':
            fc, tc = ('#E88A8A', '#4A1414')
        label = fact.replace('_', ' ')
        dot.append(f'"{fact}" [shape=box, style="rounded,filled", fontsize=10, margin="0.13,0.07", fillcolor="{fc}", fontcolor="{tc}", label="{label}"];')
    for idx, r in enumerate(rules):
        rid_node = f'r_{branch}_{idx}'
        label = r['id']
        dot.append(f'"{rid_node}" [shape=diamond, style=filled, fontsize=8, fillcolor="#FFFFFF", color="#5F5E5A", fontcolor="#2C2C2A", width=0.25, height=0.25, margin="0.04,0.02", label="{label}"];')
        for c in r['conditions']:
            dot.append(f'"{c['fact']}" -> "{rid_node}" [arrowhead=none];')
            if c.get('ref_fact'):
                dot.append(f'"{c['ref_fact']}" -> "{rid_node}" [arrowhead=none, style=dashed];')
        for c in r['conclusions']:
            dot.append(f'"{rid_node}" -> "{c['fact']}";')
    dot.append('}')
    fname = f'andor_{branch}'
    with open(f'{fname}.dot', 'w', encoding='utf-8') as f:
        f.write('\n'.join(dot))
    summary.append((branch, len(rules), len(node_facts)))
print('Гілка          правил  фактів')
for b, r, f in sorted(summary, key=lambda x: -x[1]):
    print(f'{b:15s} {r:5d}   {f:5d}')
