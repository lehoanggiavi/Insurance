"""Independent CSV fixtures, then compare captured live DAX/metadata evidence.

python scripts/04_check_semantic_model.py prepare
python scripts/04_check_semantic_model.py verify
No personal rows are printed. This does not rebuild curated or the model.
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal
from datetime import date
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / 'Log/phase3'
TABLES = {
    'Fact_Complaint': ('complaints_curated.csv', 'ComplaintID'),
    'Fact_StatusHistory': ('status_history_curated.csv', 'EventID__int'),
    'Dim_Customer': ('customers_curated.csv', 'CustomerID'),
    'Dim_Broker': ('brokers_curated.csv', 'BrokerID'),
    'Dim_Product': ('products_curated.csv', 'ProductID'),
    'Dim_Region': ('regions_curated.csv', 'id'),
    'Dim_StateRegion': ('state_regions_curated.csv', 'State Code__source'),
    'Dim_Priority': ('priorities_curated.csv', 'ID'),
    'Dim_Category': ('categories_curated.csv', 'ID'),
    'Dim_Source': ('sources_curated.csv', 'ID'),
    'Dim_Type': ('types_curated.csv', 'ID'),
    'Dim_ComplaintStatus': ('statuses_curated.csv', 'ID'),
    'Dim_EventStatus': ('statuses_curated.csv', 'ID'),
}
LINKS = [
    ('Fact_Complaint', 'CustomerID', 'Dim_Customer', 'CustomerID'),
    ('Fact_Complaint', 'BrokerID', 'Dim_Broker', 'BrokerID'),
    ('Fact_Complaint', 'ProductID', 'Dim_Product', 'ProductID'),
    ('Fact_Complaint', 'ComplainPriorityID', 'Dim_Priority', 'ID'),
    ('Fact_Complaint', 'ComplainCategoryID', 'Dim_Category', 'ID'),
    ('Fact_Complaint', 'ComplainSourceID', 'Dim_Source', 'ID'),
    ('Fact_Complaint', 'ComplainTypeID', 'Dim_Type', 'ID'),
    ('Fact_Complaint', 'ComplainStatusID', 'Dim_ComplaintStatus', 'ID'),
    ('Fact_StatusHistory', 'ComplaintID', 'Fact_Complaint', 'ComplaintID'),
    ('Fact_StatusHistory', 'ComplaintStatusID', 'Dim_EventStatus', 'ID'),
    ('Dim_Customer', 'RegionID', 'Dim_Region', 'id'),
    ('Dim_Region', 'state_code', 'Dim_StateRegion', 'State Code__source'),
]


def read(filename):
    with (ROOT / 'data/curated' / filename).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def key(value):
    return Decimal(value) if value else None


def literal(value):
    return '"' + value.replace('"', '""') + '"'


def prepare():
    complaints = read('complaints_curated.csv')
    events = read('status_history_curated.csv')
    customers = read('customers_curated.csv')
    cases = []
    for table, (filename, column) in TABLES.items():
        rows = read(filename)
        ids = [r[column] for r in rows]
        normalized = ids if table == 'Dim_StateRegion' else [key(x) for x in ids]
        assert len(normalized) == len(set(normalized)), f'duplicate key in {table}'
        assert all(x is not None and x != '' for x in normalized), f'blank key in {table}'
        model_column = 'EventID' if table == 'Fact_StatusHistory' else column
        cases.append({'name': table, 'query': f'EVALUATE ROW("Rows", COUNTROWS(ALLNOBLANKROW(\'{table}\')), "Unique", DISTINCTCOUNT(\'{table}\'[{model_column}]))', 'expected': {'Rows': len(rows), 'Unique': len(rows)}})
    expr = {
        'CompletionBlank': 'COUNTROWS(FILTER(Fact_Complaint, ISBLANK(Fact_Complaint[CompletionDate__iso])))',
        'AdminBlank': 'COUNTROWS(FILTER(Fact_Complaint, ISBLANK(Fact_Complaint[AdministratorID])))',
        'BirthBlank': 'COUNTROWS(FILTER(Dim_Customer, ISBLANK(Dim_Customer[BirthDate__iso])))',
        'ProcessingZero': 'COUNTROWS(FILTER(Fact_Complaint, NOT ISBLANK(Fact_Complaint[processing_days]) && Fact_Complaint[processing_days] = 0))',
        'AfterCutoff': 'COUNTROWS(FILTER(Fact_StatusHistory, Fact_StatusHistory[event_after_cutoff_flag] = TRUE()))',
        'AmbiguousEvents': 'COUNTROWS(FILTER(Fact_StatusHistory, Fact_StatusHistory[complaint_latest_ambiguous_flag] = TRUE()))',
    }
    expected = {
        'CompletionBlank': sum(not r['CompletionDate__iso'] for r in complaints),
        'AdminBlank': sum(not r['AdministratorID'] for r in complaints),
        'BirthBlank': sum(not r['BirthDate__iso'] for r in customers),
        'ProcessingZero': sum(r['processing_days'] != '' and key(r['processing_days']) == 0 for r in complaints),
        'AfterCutoff': sum(r['event_after_cutoff_flag'] == 'True' for r in events),
        'AmbiguousEvents': sum(r['complaint_latest_ambiguous_flag'] == 'True' for r in events),
    }
    for field, prefix in [('ClientSatisfaction', 'Satisfaction'), ('age_bucket', 'Age')]:
        for value, count in Counter(r[field] for r in complaints).items():
            label = prefix + '_' + value
            expr[label] = f'CALCULATE(COUNTROWS(Fact_Complaint), Fact_Complaint[{field}] = {literal(value)})'
            expected[label] = count
    cases.append({'name': 'null_flags_cohorts', 'query': 'EVALUATE ROW(' + ', '.join(f'{literal(k)}, {v}' for k, v in expr.items()) + ')', 'expected': expected})
    fk_expr, fk_expected = {}, {}
    for index, (ft, fc, tt, tc) in enumerate(LINKS):
        normalize = (lambda x: x) if tt == 'Dim_StateRegion' else key
        target_keys = {normalize(r[tc]) for r in read(TABLES[tt][0])}
        label = 'FK' + str(index)
        fk_expected[label] = sum(bool(r[fc]) and normalize(r[fc]) not in target_keys for r in read(TABLES[ft][0]))
        # Khong dung RELATED() tren COT KHOA: engine nay tra loi (null) cho
        # RELATED(khoa) va RELATED('State Code__source'). Do la loi engine, khong
        # phai loi model. Cach nay giu nguyen y nghia: so dong fact co FK non-blank
        # tru voi so dong fact co FK khop khoa dimension -> orphan.
        fk_expr[label] = (
            f'COUNTROWS(FILTER(\'{ft}\', NOT ISBLANK(\'{ft}\'[{fc}])))'
            f' - COUNTROWS(CALCULATETABLE(\'{ft}\', TREATAS(VALUES(\'{tt}\'[{tc}]), \'{ft}\'[{fc}])))'
        )
    cases.append({'name': 'foreign_key_integrity', 'query': 'EVALUATE ROW(' + ', '.join(f'{literal(k)}, {v}' for k, v in fk_expr.items()) + ')', 'expected': fk_expected})
    ranges = {
        'Dim_Date_Complaint': [r[f] for r in complaints for f in ['ComplainDate__iso', 'CompletionDate__iso'] if r[f]],
        'Dim_Date_Event': [r['StatusDate__iso'] for r in events if r['StatusDate__iso']],
    }
    for table, values in ranges.items():
        lo, hi = min(values), max(values)
        days = (date.fromisoformat(hi) - date.fromisoformat(lo)).days + 1
        cases.append({'name': table, 'query': f'EVALUATE ROW("Rows", COUNTROWS({table}), "Unique", DISTINCTCOUNT({table}[Date]), "MinDate", FORMAT(MIN({table}[Date]), "yyyy-MM-dd"), "MaxDate", FORMAT(MAX({table}[Date]), "yyyy-MM-dd"))', 'expected': {'Rows': days, 'Unique': days, 'MinDate': lo, 'MaxDate': hi}})

    def filter_case(name, table, column, value, selected_ids):
        selected_ids = {key(x) for x in selected_ids}
        condition = f'TREATAS({{{literal(value)}}}, {table}[{column}])' if table in ('Dim_Customer', 'Dim_StateRegion') else f'TREATAS({{{value}}}, {table}[{column}])'
        query = f'EVALUATE CALCULATETABLE(ROW("Complaints", COUNTROWS(Fact_Complaint), "Events", COUNTROWS(Fact_StatusHistory)), {condition})'
        cases.append({'name': name, 'query': query, 'expected': {'Complaints': sum(key(r['ComplaintID']) in selected_ids for r in complaints), 'Events': sum(key(r['ComplaintID']) in selected_ids for r in events)}})
    gender = Counter(r['Gender'] for r in customers).most_common(1)[0][0]
    ids = {key(r['CustomerID']) for r in customers if r['Gender'] == gender}
    filter_case('customer_filter', 'Dim_Customer', 'Gender', gender, [r['ComplaintID'] for r in complaints if key(r['CustomerID']) in ids])
    regions = read('regions_curated.csv')
    region_states = {key(r['id']): r['state_code'] for r in regions}
    state_code = Counter(region_states[key(r['RegionID'])] for r in customers).most_common(1)[0][0]
    customer_ids = {key(r['CustomerID']) for r in customers if region_states[key(r['RegionID'])] == state_code}
    filter_case('state_region_filter', 'Dim_StateRegion', 'State Code__source', state_code, [r['ComplaintID'] for r in complaints if key(r['CustomerID']) in customer_ids])
    for fact_column, table, dim_column, name in [('ProductID', 'Dim_Product', 'ProductID', 'product_filter'), ('ComplainCategoryID', 'Dim_Category', 'ID', 'category_filter'), ('ComplainStatusID', 'Dim_ComplaintStatus', 'ID', 'complaint_status_filter')]:
        value = Counter(key(r[fact_column]) for r in complaints).most_common(1)[0][0]
        filter_case(name, table, dim_column, str(value), [r['ComplaintID'] for r in complaints if key(r[fact_column]) == value])
    day = Counter(r['ComplainDate__iso'] for r in complaints).most_common(1)[0][0]
    day_dax = 'DATE(' + ','.join(str(int(x)) for x in day.split('-')) + ')'
    ids = {key(r['ComplaintID']) for r in complaints if r['ComplainDate__iso'] == day}
    cases.append({'name': 'complaint_date_filter', 'query': f'EVALUATE CALCULATETABLE(ROW("Complaints", COUNTROWS(Fact_Complaint), "Events", COUNTROWS(Fact_StatusHistory)), TREATAS({{{day_dax}}}, Dim_Date_Complaint[Date]))', 'expected': {'Complaints': len(ids), 'Events': sum(key(r['ComplaintID']) in ids for r in events)}})
    event_day = max(r['StatusDate__iso'] for r in events if r['StatusDate__iso'])
    day_dax = 'DATE(' + ','.join(str(int(x)) for x in event_day.split('-')) + ')'
    cases.append({'name': 'event_date_filter', 'query': f'EVALUATE CALCULATETABLE(ROW("Complaints", COUNTROWS(Fact_Complaint), "Events", COUNTROWS(Fact_StatusHistory)), TREATAS({{{day_dax}}}, Dim_Date_Event[Date]))', 'expected': {'Complaints': len(complaints), 'Events': sum(r['StatusDate__iso'] == event_day for r in events)}})
    status = Counter(key(r['ComplaintStatusID']) for r in events).most_common(1)[0][0]
    cases.append({'name': 'event_status_filter', 'query': f'EVALUATE CALCULATETABLE(ROW("Complaints", COUNTROWS(Fact_Complaint), "Events", COUNTROWS(Fact_StatusHistory)), TREATAS({{{status}}}, Dim_EventStatus[ID]))', 'expected': {'Complaints': len(complaints), 'Events': sum(key(r['ComplaintStatusID']) == status for r in events)}})
    (LOG / 'qa_cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Independent fixtures prepared:', len(cases), 'queries;', sum(len(c['expected']) for c in cases), 'comparisons')


def rows_from(result):
    for item in result.get('content', []):
        if item.get('type') == 'text':
            data = json.loads(item['text'])
            if 'data' in data and isinstance(data['data'], dict):
                data = data['data']
            if 'rows' in data:
                return data['rows']
    raise AssertionError('No live row data')


def verify():
    cases = json.loads((LOG / 'qa_cases.json').read_text(encoding='utf-8'))
    live = json.loads((LOG / 'live_queries.json').read_text(encoding='utf-8'))
    comparisons = []
    for case in cases:
        result = live[case['name']]
        assert not result.get('isError'), case['name']
        rows = rows_from(result)
        assert len(rows) == 1, case['name']
        actual = {k.strip('[]'): v for k, v in rows[0].items()}
        for name, expected in case['expected'].items():
            observed = actual[name]
            comparisons.append({'case': case['name'], 'field': name, 'expected': expected, 'actual': observed, 'pass': observed == expected})
    relationships = json.loads((LOG / 'relationships.json').read_text(encoding='utf-8'))
    actual_links = {(r['fromTable'], r['fromColumn'], r['toTable'], r['toColumn']): r for r in relationships}
    required = LINKS + [
        ('Fact_Complaint', 'ComplainDate__iso', 'Dim_Date_Complaint', 'Date'),
        ('Fact_Complaint', 'CompletionDate__iso', 'Dim_Date_Complaint', 'Date'),
        ('Fact_StatusHistory', 'StatusDate__iso', 'Dim_Date_Event', 'Date'),
    ]
    for link in required:
        observed = actual_links.get(link, {})
        active = link[1] != 'CompletionDate__iso'
        ok = observed.get('isActive') == active and observed.get('fromCardinality') == 'Many' and observed.get('toCardinality') == 'One' and observed.get('crossFilteringBehavior') == 'OneDirection'
        comparisons.append({'case': 'relationship', 'link': list(link), 'pass': ok})
    for relative, expected_hash in json.loads((LOG / 'protected_hashes.json').read_text(encoding='utf-8')).items():
        actual_hash = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        comparisons.append({'case': 'protected_source', 'file': relative, 'pass': actual_hash == expected_hash})
    result = {'checks': len(comparisons), 'passed': sum(c['pass'] for c in comparisons), 'failed': sum(not c['pass'] for c in comparisons), 'comparisons': comparisons}
    (LOG / 'reconciliation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'comparisons'}))
    assert result['failed'] == 0, 'Live model mismatch; see reconciliation.json'


if __name__ == '__main__':
    assert len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'verify')
    prepare() if sys.argv[1] == 'prepare' else verify()
