"""Import a downloaded GoMask CSV/JSON export. Does not contact GoMask."""
import argparse
import csv
import json
from pathlib import Path
from backend.gomask import normalize_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export', type=Path)
    args = parser.parse_args()
    try:
        if args.export.stat().st_size > 10 * 1024 * 1024:
            raise ValueError('Export must be at most 10 MB.')
        with args.export.open(encoding='utf-8-sig', newline='') as file:
            rows = json.load(file) if args.export.suffix.lower() == '.json' else list(csv.DictReader(file))
        records = normalize_records(rows)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Import failed: {exc}\n')
    target = Path(__file__).resolve().parent.parent / 'backend' / 'data' / 'gomask.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    temporary.replace(target)
    print(f'Imported {len(records)} transactions for {len({r["patient_id"] for r in records})} synthetic patients. Restart the server.')


if __name__ == '__main__':
    main()
