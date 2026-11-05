# vat2-simulados

Simulados da VAT2 (4º semestre de Medicina, 2026.2), um por disciplina, prontos para GitHub Pages.

- `data/<materia>.json`: banco de questões (fonte única; a plataforma `vat2-estudos` também lê daqui).
- `tools/template.html`: motor do simulado (o mesmo dos simulados da VAT1).
- `tools/build.py`: gera `<pasta>/index.html` de cada matéria e atualiza a lista em `index.html`.

Para atualizar depois de mexer nas questões: `python3 tools/build.py`.
