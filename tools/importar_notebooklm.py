"""Importa questões geradas no chat do NotebookLM para o banco de uma matéria.

O NotebookLM responde com um ou mais blocos JSON (lista de questões). Cole a resposta
inteira, do jeito que veio, num arquivo de texto e rode, na raiz do repositório:

  python3 tools/importar_notebooklm.py ARQUIVO.txt --materia genetica \
      --assunto gen-crispr --categoria "Terapia Gênica: CRISPR-Cas9" --prefixo CRISPR

O texto das questões NÃO é alterado: o script só converte os campos para o formato do
simulado, numera, marca a origem como "Gerada no NotebookLM", ignora questões repetidas
(mesmo enunciado) e regera as páginas com tools/build.py.
"""
import argparse, json, os, re, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LETRAS = 'ABCD'
DIF = {'basica': 'Básica', 'básica': 'Básica', 'intermediaria': 'Intermediária',
       'intermediária': 'Intermediária', 'avancada': 'Avançada', 'avançada': 'Avançada'}


def blocos_json(texto):
    """Encontra todas as questões (objetos com "enunciado") no texto, uma a uma.

    Aceita vários blocos colados em sequência e também respostas cortadas no meio:
    as questões completas são aproveitadas e só a última, incompleta, é descartada.
    """
    dec = json.JSONDecoder(); i = 0; achadas = []
    while True:
        i = texto.find('{', i)
        if i < 0:
            return achadas
        try:
            obj, fim = dec.raw_decode(texto, i)
            if isinstance(obj, dict) and 'enunciado' in obj:
                achadas.append(obj); i = fim
            else:
                i += 1
        except json.JSONDecodeError:
            i += 1


CITACAO = re.compile(r'\s*\[\d+(?:\s*[,\-–]\s*\d+)*\]')


def limpar(v):
    """Remove as marcas de citação do NotebookLM ("[1]", "[2, 3]", "[4-6]")."""
    if isinstance(v, str):
        return CITACAO.sub('', v).strip()
    if isinstance(v, dict):
        return {k: limpar(x) for k, x in v.items()}
    if isinstance(v, list):
        return [limpar(x) for x in v]
    return v


def converter(item):
    item = limpar(item)
    alts = item.get('alternativas') or {}
    if isinstance(alts, list):  # aceita lista ["...", "..."] também
        alts = {LETRAS[k]: v for k, v in enumerate(alts)}
    just = item.get('justificativas') or {}
    correta = str(item.get('correta', '')).strip().upper()[:1]
    if correta not in LETRAS or any(l not in alts for l in LETRAS):
        raise ValueError('questão sem 4 alternativas A-D ou sem gabarito válido')
    opts = []
    for l in LETRAS:
        r = str(just.get(l, '')).strip()
        # troca "Certa."/"Errada."/"Correta."/"Incorreta." pelo padrão do simulado
        r = re.sub(r'^\s*\(?(certa|correta|errada|incorreta|verdadeira|falsa)\)?\s*(\([^)]*\))?\s*[.:\-–—]?\s*', '', r, flags=re.I)
        r = ('CORRETA. ' if l == correta else 'Incorreta. ') + r
        opts.append({'letter': l, 'text': str(alts[l]).strip(), 'rationale': r})
    dif = DIF.get(str(item.get('dificuldade', '')).strip().lower(), 'Intermediária')
    return {
        'subcategory': str(item.get('subtema', '')).strip() or 'Geral',
        'difficulty': dif,
        'prompt': str(item.get('enunciado', '')).strip(),
        'options': opts,
        'correctLetter': correta,
        'clinicalPointers': str(item.get('ponto_chave', '')).strip(),
        'origem': 'notebooklm',
        'sourceLabel': 'Gerada no NotebookLM',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arquivo'); ap.add_argument('--materia', required=True)
    ap.add_argument('--assunto', required=True); ap.add_argument('--categoria', required=True)
    ap.add_argument('--prefixo', required=True)
    a = ap.parse_args()

    caminho = os.path.join(RAIZ, 'data', a.materia + '.json')
    banco = json.load(open(caminho, encoding='utf-8')) if os.path.exists(caminho) else []
    vistos = {q['prompt'].strip().lower() for q in banco}
    n = 1 + max([int(m.group(1)) for q in banco for m in [re.match(re.escape(a.prefixo) + r'-(\d+)$', q['code'])] if m] or [0])

    brutas = blocos_json(open(a.arquivo, encoding='utf-8').read())
    novas, erros = [], 0
    for item in brutas:
        try:
            q = converter(item)
        except Exception:
            erros += 1; continue
        if not q['prompt'] or q['prompt'].lower() in vistos:
            continue
        vistos.add(q['prompt'].lower())
        q.update({'code': f'{a.prefixo}-{n:02d}', 'assunto': a.assunto, 'category': a.categoria}); n += 1
        novas.append(q)

    # distribui o gabarito entre A-D (só troca a ordem das alternativas, não o texto)
    for i, q in enumerate(novas):
        alvo = LETRAS[(i * 3 + 2) % 4]
        o = q['options']; cor = o.pop(LETRAS.index(q['correctLetter'])); o.insert(LETRAS.index(alvo), cor)
        for j, x in enumerate(o):
            x['letter'] = LETRAS[j]
        q['correctLetter'] = alvo

    banco.extend(novas)
    ordem = ['id', 'code', 'assunto', 'category', 'subcategory', 'difficulty', 'origem', 'sourceLabel',
             'prompt', 'options', 'correctLetter', 'clinicalPointers', 'solutionSteps', 'bookContext', 'revisada']
    for i, q in enumerate(banco, 1):
        q['id'] = i
    banco = [{k: q[k] for k in ordem if k in q} for q in banco]
    json.dump(banco, open(caminho, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(brutas)} questões encontradas no arquivo, {len(novas)} importadas, '
          f'{erros} com formato inválido, {len(brutas) - len(novas) - erros} repetidas. Total no banco: {len(banco)}.')
    subprocess.run([sys.executable, '-I', os.path.join(RAIZ, 'tools', 'build.py')], check=True)


if __name__ == '__main__':
    main()
