import ast
from pathlib import Path

APP = Path('app.py')
source = APP.read_text(encoding='utf-8')
tree = ast.parse(source)
needed = {
    '_v22_parse_ts',
    '_v23_words_from_full_json',
    '_group_words_for_caption',
    '_v22_escape_ass',
}
body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in needed]
ns = {}
exec(compile(ast.Module(body=body, type_ignores=[]), str(APP), 'exec'), ns)

payload = {
    'transcription': [{
        'timestamps': {'from': '00:00:00.00', 'to': '00:00:04.00'},
        'tokens': [
            {'text': 'Erster', 't_dtw': 0, 'timestamps': {'from': '00:00:00.00', 'to': '00:00:00.40'}},
            {'text': ' Satz.', 't_dtw': 40, 'timestamps': {'from': '00:00:00.40', 'to': '00:00:00.90'}},
            {'text': ' Zweiter', 't_dtw': 110, 'timestamps': {'from': '00:00:01.10', 'to': '00:00:01.50'}},
            {'text': ' Satz', 't_dtw': 150, 'timestamps': {'from': '00:00:01.50', 'to': '00:00:01.90'}},
            {'text': '.', 't_dtw': 190, 'timestamps': {'from': '00:00:01.90', 'to': '00:00:02.00'}},
            {'text': ' Dritter', 't_dtw': 220, 'timestamps': {'from': '00:00:02.20', 'to': '00:00:02.60'}},
            {'text': ' Satz.', 't_dtw': 260, 'timestamps': {'from': '00:00:02.60', 'to': '00:00:03.10'}},
        ],
    }]
}

words = ns['_v23_words_from_full_json'](payload)
groups = ns['_group_words_for_caption'](words)
assert len(words) == 6, words
assert len(groups) >= 3, groups
assert words[-1][1] >= 2.0, words[-1]
assert all(end > start for _, start, end in words)
assert all(groups[i][-1][2] <= groups[i+1][0][1] + 1e-9 for i in range(len(groups)-1))
print(f'Subtitle timing self-test OK: {len(words)} words, {len(groups)} groups, full timeline preserved.')
