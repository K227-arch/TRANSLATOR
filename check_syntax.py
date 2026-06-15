import ast, os
files = [
    'lunyoro-translator/backend/train_marian.py',
    'lunyoro-translator/backend/train_nllb.py',
    'lunyoro-translator/backend/back_translate_lun2en.py',
    'lunyoro-translator/backend/knowledge_graph.py',
    'lunyoro-translator/backend/main.py',
    'lunyoro-translator/backend/translate.py',
    'lunyoro-translator/backend/eval_bleu.py',
    'lunyoro-translator/backend/run_full_training.py',
    'lunyoro-translator/backend/run_k227_pipeline.py',
    'lunyoro-translator/backend/language_rules_gr4.py',
    'lunyoro-translator/backend/language_rules_gr5.py',
]
all_ok = True
for f in files:
    name = os.path.basename(f)
    try:
        ast.parse(open(f, encoding='utf-8').read())
        print('OK  ' + name)
    except SyntaxError as e:
        print('ERR ' + name + ': ' + str(e))
        all_ok = False
print()
print('All OK' if all_ok else 'ERRORS FOUND - fix before pushing')
