from result_analizer import TemplateParser, Report

msg = ['Side 1/4 - FAIL - Expected: 305.000 mm, Detected: 299.552 mm',
       'Side 2/4 - PASS - Expected: 610.000 mm, Detected: 609.255 mm',
       'Side 3/4 - FAIL - Expected: 305.000 mm, Detected: 301.959 mm'
       ]

def parse_result(logs, template: str):
    paser = TemplateParser(template)
    for l in reversed(logs):
        result = paser.parse(l)
        if result:
            return result
    return {}
max_y0 = parse_result(msg, 'Side 3/4 - {Result} - Expected: {expected} mm, Detected: {Detected} mm').get('Detected', 100)
print(type(max_y0))