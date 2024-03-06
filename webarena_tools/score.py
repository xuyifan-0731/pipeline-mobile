import os, json, sys

TASKS = 812

src = sys.argv[1]
path = os.path.join(src, 'actions')

score, finish_count = 0, 0
finished = os.listdir(path)
for file in finished:
    if not file.endswith('.json'):
        continue
    with open(os.path.join(path, file), 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, dict):
        continue
    
    if data.get('task_id', 1000) >= TASKS:
        continue
    
    finish_count += 1
    score += data.get('score', 0)

finish_count = max(finish_count, 1)
pacc, acc = score / finish_count * 100, score / TASKS * 100
meta = """src file:  {}
successed: {:3} / {:4} (812)
--------
partial accuracy: {:7}
overall accuracy: {:7}
""".format(src, int(score), finish_count, round(pacc, 2), round(acc, 2))

print(meta)