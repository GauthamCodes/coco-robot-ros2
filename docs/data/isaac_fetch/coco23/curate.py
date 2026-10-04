"""Copy completed raw evidence without modifying/deleting original runtime files."""
import gzip
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
RUNTIME = Path('/home/gautham/coco23_runtime')
for backend in ('isaac', 'gazebo'):
    for seed in range(5, 10):
        name = f'{backend}_seed{seed}'
        source, dest = RUNTIME / name, ROOT / name
        if not (source / 'exits.json').exists():
            continue
        dest.mkdir(exist_ok=True)
        for path in source.iterdir():
            if path.is_file() and path.suffix in ('.json', '.yaml', '.txt'):
                shutil.copy2(path, dest / path.name)
            elif path.is_file() and (path.suffix in ('.log', '.jsonl', '.patch')):
                with path.open('rb') as src, gzip.open(dest / (path.name + '.gz'), 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        if (source / 'sim/settled_targets.json').exists():
            shutil.copy2(source / 'sim/settled_targets.json', dest / 'settled_targets.json')
        (dest / 'runtime_reference.json').write_text(json.dumps({
            'original_directory': str(source), 'images': str(source / 'images'),
            'expanded_urdf': str(source / 'robot.urdf'), 'simulator_generated_assets': str(source / 'sim'),
            'note': 'Compressed logs and ROS/physical telemetry are durable here; large generated assets/images remain at original local path.'}, indent=2) + '\n')
for name in ('matrix_exits.txt',):
    if (RUNTIME / name).exists():
        shutil.copy2(RUNTIME / name, ROOT / name)
shutil.copy2('/home/gautham/coco23_matrix.log', ROOT / 'matrix.log')
