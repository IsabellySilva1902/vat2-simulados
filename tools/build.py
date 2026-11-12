"""Gera a página de cada simulado a partir de data/<id>.json e tools/template.html.

Uso (na raiz do repositório):  python3 tools/build.py
Também atualiza a lista de matérias e o número de questões em index.html.
"""
import json, os, html

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl = open(os.path.join(RAIZ, 'tools', 'template.html'), encoding='utf-8').read()
materias = json.load(open(os.path.join(RAIZ, 'tools', 'materias.json'), encoding='utf-8'))

cartoes = []
for m in materias:
    caminho = os.path.join(RAIZ, 'data', m['id'] + '.json')
    if not os.path.exists(caminho):
        cartoes.append(f'<div class="card off"><span>{m["emoji"]}</span><div><b>{html.escape(m["nome"])}</b><small>em preparação</small></div></div>')
        continue
    banco = json.load(open(caminho, encoding='utf-8'))
    # fichas do caderno de erros ficam em data/fichas/<id>.json (por code), separadas do banco, para o importador não apagá-las
    arq_f = os.path.join(RAIZ, 'data', 'fichas', m['id'] + '.json')
    if os.path.exists(arq_f):
        fichas = json.load(open(arq_f, encoding='utf-8'))
        for q in banco:
            if q.get('code') in fichas: q['ficha'] = fichas[q['code']]
    pagina = (tpl.replace('{{NOME}}', m['nome'] + ' · VAT2')
                 .replace('{{STORAGE}}', m['storage'])
                 .replace('{{BANCO}}', json.dumps(banco, ensure_ascii=False, indent=1)))
    os.makedirs(os.path.join(RAIZ, m['pasta']), exist_ok=True)
    open(os.path.join(RAIZ, m['pasta'], 'index.html'), 'w', encoding='utf-8').write(pagina)
    assuntos = sorted({q['category'] for q in banco if not q.get('lista')})
    listas = sorted({q['lista'] for q in banco if q.get('lista')})
    extra = (f' · {len(listas)} lista de aula' if len(listas) == 1 else f' · {len(listas)} listas de aula') if listas else ''
    cartoes.append(f'<a class="card" href="{m["pasta"]}/"><span>{m["emoji"]}</span><div><b>{html.escape(m["nome"])}</b>'
                   f'<small>{len(banco)} questões · {len(assuntos)} assuntos{extra}</small></div><i>→</i></a>')
    print(f'{m["pasta"]}/index.html: {len(banco)} questões')

idx = os.path.join(RAIZ, 'index.html')
s = open(idx, encoding='utf-8').read()
ini, fim = s.index('<!--MATERIAS-->') + len('<!--MATERIAS-->'), s.index('<!--/MATERIAS-->')
open(idx, 'w', encoding='utf-8').write(s[:ini] + '\n' + '\n'.join(cartoes) + '\n' + s[fim:])
