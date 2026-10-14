"""Common checks for operator-generated trial DSTs. No machine acceptance implied."""
import hashlib
import math
from pathlib import Path

import pyembroidery as pe


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode_dst(path):
    data = Path(path).read_bytes()
    if len(data) < 515:
        raise ValueError('DST is shorter than header plus END')
    header = {}
    for item in data[:512].decode('ascii', errors='replace').split('\r'):
        if len(item) > 3 and item[2] == ':':
            header[item[:2]] = item[3:].strip().strip('\x1a')
    wx = [(0, 0, 1, 1), (1, 0, 1, 3), (0, 2, 3, 9), (1, 2, 3, 27), (2, 2, 3, 81)]
    wy = [(0, 7, 6, 1), (1, 7, 6, 3), (0, 5, 4, 9), (1, 5, 4, 27), (2, 5, 4, 81)]
    x = y = 0
    rows = []
    for offset in range(512, len(data) - 2, 3):
        b = data[offset:offset + 3]
        if b[2] & 3 != 3:
            raise ValueError('Invalid DST marker bits')
        if b[2] & 0xF3 == 0xF3:
            if b != b'\x00\x00\xf3' or data[offset + 3:] not in (b'', b'\x1a'):
                raise ValueError('Unexpected END or data after END')
            rows.append([x, y, pe.END])
            return rows, header
        if b[2] & 0xC3 == 0xC3:
            command = pe.COLOR_CHANGE
        elif b[2] & 0x43 == 0x43:
            raise ValueError('Sequin command is outside this ruleset')
        else:
            command = pe.JUMP if b[2] & 0x80 else pe.STITCH
        x += sum((((b[k] >> plus) & 1) - ((b[k] >> minus) & 1)) * w for k, plus, minus, w in wx)
        y -= sum((((b[k] >> plus) & 1) - ((b[k] >> minus) & 1)) * w for k, plus, minus, w in wy)
        rows.append([x, y, command])
    raise ValueError('Missing encoded END')


def stitch_blocks(rows):
    blocks = []
    start = None
    for i, row in enumerate(rows, 1):
        if row[2] == pe.STITCH:
            if start is None:
                start = i
        elif start is not None:
            blocks.append([start, i - 1])
            start = None
    return blocks


def validate_dst(path, order, plan, limits):
    report = {'dst_sha256': sha(path), 'status': 'needs_review', 'machine_tested': False,
              'checks': {}, 'issues': [], 'limitations': [
                  'File and declared geometry checks only; visual shape, stroke order, arc turnbacks and machine behavior still need review.',
                  'Return ranges and order confirmations are declarations supplied by the executing Codex/operator; they are not inferred automatically.']}
    try:
        rows, header = decode_dst(path)
    except ValueError as error:
        report['checks']['encoded_structure'] = False
        report['issues'].append(str(error))
        return report, []
    checks = report['checks']
    checks['encoded_structure'] = True
    try:
        independent = pe.read_dst(str(path), {'trim_at': False, 'clipping': False}).stitches
        checks['dual_decode_identical'] = len(independent) == len(rows) and all(
            abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6 and (int(a[2]) & pe.COMMAND_MASK) == b[2]
            for a, b in zip(independent, rows))
    except Exception as error:
        checks['dual_decode_identical'] = False
        report['issues'].append(f'Second decoder failed: {error}')
    xs = [0, *[row[0] for row in rows]]
    ys = [0, *[-row[1] for row in rows]]
    expected = {'ST': len(rows), 'CO': sum(row[2] == pe.COLOR_CHANGE for row in rows),
                '+X': max(xs), '-X': -min(xs), '+Y': max(ys), '-Y': -min(ys),
                'AX': rows[-1][0], 'AY': -rows[-1][1]}
    mismatches = {}
    for key, value in expected.items():
        try:
            actual = int(header[key])
        except (KeyError, ValueError):
            actual = None
        if actual != value:
            mismatches[key] = {'header': actual, 'decoded': value}
    checks['header_matches_decoded'] = not mismatches
    report['header_mismatches'] = mismatches
    checks['single_color_scope'] = expected['CO'] == 0
    stitches = [row for row in rows if row[2] == pe.STITCH]
    if not stitches:
        checks['has_stitches'] = False
        return report, rows
    checks['has_stitches'] = True
    width = (max(p[0] for p in stitches) - min(p[0] for p in stitches)) / 10
    height = (max(p[1] for p in stitches) - min(p[1] for p in stitches)) / 10
    lengths = []
    previous = [0, 0]
    for row in rows:
        if row[2] == pe.STITCH:
            lengths.append(math.dist(previous, row[:2]) / 10)
        previous = row[:2]
    nonzero = [v for v in lengths if v > 1e-9]
    report['metrics'] = {'width_mm': width, 'height_mm': height, 'stitch_commands': len(stitches),
                         'jump_commands': sum(row[2] == pe.JUMP for row in rows),
                         'min_nonzero_stitch_mm': min(nonzero) if nonzero else None,
                         'max_stitch_mm': max(lengths), 'zero_length_stitches': len(lengths) - len(nonzero),
                         'short_stitches_under_0_5mm': sum(v < .5 for v in nonzero)}
    target = order.get('design', {}).get('width_mm')
    checks['width_matches_order'] = (isinstance(target, (int, float)) and not isinstance(target, bool)
                                     and math.isfinite(target) and target > 0
                                     and abs(width - target) <= limits['width_tolerance_mm'] + 1e-9)
    checks['max_stitch_within_trial_limit'] = max(lengths) <= limits['max_stitch_mm'] + 1e-9
    blocks = stitch_blocks(rows)
    report['stitch_blocks_command_ranges_1based'] = blocks
    declarations = plan.get('returns', [])
    results = []
    valid = isinstance(declarations, list) and len(declarations) == len(blocks)
    if valid:
        for block, declaration in zip(blocks, declarations):
            result = {'block': block, 'pass': False}
            try:
                a, b = declaration['start_commands_1based']
                c, d = declaration['end_commands_1based']
                if not all(type(v) is int for v in [a, b, c, d]) or not (a == block[0] and d == block[1] and a < b < c < d):
                    raise ValueError('Return ranges must cover the block endpoints without overlapping')
                start_length = sum(math.dist(rows[i - 1][:2], rows[i][:2]) / 10 for i in range(a, b))
                end_length = sum(math.dist(rows[i - 1][:2], rows[i][:2]) / 10 for i in range(c, d))
                result.update(start_mm=start_length, end_mm=end_length)
                result['pass'] = all(abs(v - limits['return_length_mm']) <= limits['return_tolerance_mm'] + 1e-9
                                     for v in [start_length, end_length])
            except (KeyError, TypeError, ValueError, IndexError) as error:
                result['error'] = str(error)
            results.append(result)
        valid = all(v['pass'] for v in results)
    report['returns'] = results
    checks['all_stitch_blocks_have_measured_returns'] = valid
    review = order.get('field_review', {})
    design = order.get('design', {})
    checks['order_fields_confirmed'] = (all(review.get(k) is True for k in ['text', 'font', 'dimensions', 'layout'])
        and isinstance(design.get('text'), str) and bool(design['text'].strip())
        and design.get('font_id') in ['Font1', 'Font2', 'Font3']
        and isinstance(design.get('lines'), list) and bool(design['lines'])
        and all(isinstance(line, str) and line.strip() for line in design['lines'])
        and ' '.join(design['text'].split()) == ' '.join(' '.join(design['lines']).split())
        and design.get('alignment') in ['single_line', 'left', 'center', 'right'])
    checks['route_declared'] = plan.get('route') in ['exact_reuse', 'adapt_reference', 'compose', 'experimental']
    for key, passed in checks.items():
        if not passed:
            report['issues'].append(key)
    if all(checks.values()):
        report['status'] = 'file_checks_passed_pending_wilcom_and_sewout'
    return report, rows
