from flask import Flask, render_template, request
import rdflib
from datetime import datetime

app = Flask(__name__, template_folder='templates')

# Загружаем онтологию судебных дел
graph = rdflib.Graph()
graph.parse("cyd (1).owl", format="xml")

namespaces = {"legal": "http://www.semanticweb.org/user1/ontologies/2025/8/legal-prediction#"}

def get_all_cases():
    """Получить все судебные дела"""
    qres = graph.query(
        """
        PREFIX legal: <http://www.semanticweb.org/user1/ontologies/2025/8/legal-prediction#>
        SELECT ?case ?caseId ?date ?type ?complexity ?plaintiff ?defendant
        WHERE {
            ?case a legal:Дело .
            ?case legal:идентификаторДела ?caseId .
            ?case legal:датаВозбуждения ?date .
            ?case legal:типДела ?type .
            ?case legal:сложностьДела ?complexity .
            OPTIONAL {
                ?case legal:имеетИстца ?plaintiffInd .
                ?plaintiffInd legal:ФИО ?plaintiff .
            }
            OPTIONAL {
                ?case legal:имеетОтветчика ?defendantInd .
                ?defendantInd legal:ФИО ?defendant .
            }
        }
        ORDER BY ?caseId
        """,
        initNs=namespaces
    )

    cases = []
    for row in qres:
        cases.append({
            "caseId": str(row["caseId"]),
            "date": str(row["date"]),
            "type": str(row["type"]),
            "complexity": str(row["complexity"]),
            "plaintiff": str(row["plaintiff"]) if row["plaintiff"] else "Не указан",
            "defendant": str(row["defendant"]) if row["defendant"] else "Не указан"
        })
    return cases

def get_all_predictions():
    """Получить все прогнозы исходов дел"""
    qres = graph.query(
        """
        PREFIX legal: <http://www.semanticweb.org/user1/ontologies/2025/8/legal-prediction#>
        SELECT ?caseId ?outcomeType ?probability ?court ?judge
        WHERE {
            ?case a legal:Дело .
            ?case legal:идентификаторДела ?caseId .
            ?case legal:имеетИсход ?outcome .
            ?outcome legal:вероятностьИсхода ?probability .
            ?outcome rdf:type ?outcomeType .
            
            OPTIONAL {
                ?case legal:рассматриваетсяВСуде ?courtInd .
                ?courtInd rdfs:label ?court .
            }
            
            OPTIONAL {
                ?case legal:ведетСудья ?judgeInd .
                ?judgeInd legal:ФИО ?judge .
            }
            
            FILTER(STRSTARTS(STR(?outcomeType), STR(legal:)))
        }
        """,
        initNs=namespaces
    )

    predictions = []
    for row in qres:
        outcome_type = str(row["outcomeType"])
        # Извлекаем только имя класса без префикса
        if '#' in outcome_type:
            outcome_name = outcome_type.split('#')[-1]
        else:
            outcome_name = outcome_type
        
        predictions.append({
            "caseId": str(row["caseId"]),
            "outcome": outcome_name,
            "probability": float(row["probability"]),
            "probability_percent": float(row["probability"]) * 100,
            "court": str(row["court"]) if row["court"] else "Не указан",
            "judge": str(row["judge"]) if row["judge"] else "Не указан"
        })
    return predictions

def get_all_participants():
    """Получить всех участников судебных дел"""
    qres = graph.query(
        """
        PREFIX legal: <http://www.semanticweb.org/user1/ontologies/2025/8/legal-prediction#>
        SELECT ?fio ?type ?lawyer ?caseId
        WHERE {
            ?participant a ?participantType .
            ?participant legal:ФИО ?fio .
            
            FILTER(?participantType IN (legal:Истец, legal:Ответчик, legal:Адвокат, legal:Свидетель, legal:Судья))
            
            BIND(
                IF(?participantType = legal:Истец, "Истец",
                IF(?participantType = legal:Ответчик, "Ответчик",
                IF(?participantType = legal:Адвокат, "Адвокат",
                IF(?participantType = legal:Свидетель, "Свидетель",
                IF(?participantType = legal:Судья, "Судья", "Другое")))))
                AS ?type
            )
            
            OPTIONAL {
                ?participant legal:имеетАдвоката ?lawyerInd .
                ?lawyerInd legal:ФИО ?lawyer .
            }
            
            OPTIONAL {
                ?case legal:имеетИстца|legal:имеетОтветчика|legal:ведетСудья ?participant .
                ?case legal:идентификаторДела ?caseId .
            }
        }
        ORDER BY ?type ?fio
        """,
        initNs=namespaces
    )

    participants = []
    for row in qres:
        participants.append({
            "fio": str(row["fio"]),
            "type": str(row["type"]),
            "lawyer": str(row["lawyer"]) if row["lawyer"] else "Нет",
            "caseId": str(row["caseId"]) if row["caseId"] else "Не указано"
        })
    return participants

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cases', methods=['GET'])
def display_cases():
    cases = get_all_cases()
    
    # Получаем параметры фильтрации из запроса
    filter_case_id = request.args.get('case_id', '').strip()
    filter_type = request.args.get('case_type', '').strip()
    filter_complexity = request.args.get('complexity', '').strip()
    filter_plaintiff = request.args.get('plaintiff', '').strip()
    filter_defendant = request.args.get('defendant', '').strip()
    
    # Применяем фильтрацию
    filtered_cases = cases
    if filter_case_id:
        filtered_cases = [c for c in filtered_cases if filter_case_id.lower() in c['caseId'].lower()]
    if filter_type:
        filtered_cases = [c for c in filtered_cases if filter_type.lower() in c['type'].lower()]
    if filter_complexity:
        filtered_cases = [c for c in filtered_cases if filter_complexity.lower() in c['complexity'].lower()]
    if filter_plaintiff:
        filtered_cases = [c for c in filtered_cases if filter_plaintiff.lower() in c['plaintiff'].lower()]
    if filter_defendant:
        filtered_cases = [c for c in filtered_cases if filter_defendant.lower() in c['defendant'].lower()]
    
    # Получаем параметр сортировки
    sort_by = request.args.get('sort', 'caseId')
    sort_order = request.args.get('order', 'asc')
    
    # Определяем ключ сортировки
    sort_keys = {
        'caseId': 'caseId',
        'date': 'date',
        'type': 'type',
        'complexity': 'complexity',
        'plaintiff': 'plaintiff',
        'defendant': 'defendant'
    }
    
    if sort_by in sort_keys:
        reverse = (sort_order == 'desc')
        filtered_cases.sort(key=lambda x: x[sort_keys[sort_by]], reverse=reverse)
    
    # Получаем уникальные значения для выпадающих списков
    case_types = sorted(set(c['type'] for c in cases))
    complexities = sorted(set(c['complexity'] for c in cases))
    
    return render_template('cases.html', 
                         cases=filtered_cases,
                         case_types=case_types,
                         complexities=complexities,
                         filter_case_id=filter_case_id,
                         filter_type=filter_type,
                         filter_complexity=filter_complexity,
                         filter_plaintiff=filter_plaintiff,
                         filter_defendant=filter_defendant,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/predictions', methods=['GET'])
def display_predictions():
    predictions = get_all_predictions()
    
    # Получаем параметры фильтрации
    filter_case_id = request.args.get('case_id', '').strip()
    filter_outcome = request.args.get('outcome', '').strip()
    filter_min_prob = request.args.get('min_prob', '')
    filter_max_prob = request.args.get('max_prob', '')
    filter_court = request.args.get('court', '').strip()
    filter_judge = request.args.get('judge', '').strip()
    
    # Применяем фильтрацию
    filtered_predictions = predictions
    if filter_case_id:
        filtered_predictions = [p for p in filtered_predictions if filter_case_id.lower() in p['caseId'].lower()]
    if filter_outcome:
        filtered_predictions = [p for p in filtered_predictions if filter_outcome.lower() in p['outcome'].lower()]
    if filter_min_prob:
        min_prob = float(filter_min_prob)
        filtered_predictions = [p for p in filtered_predictions if p['probability_percent'] >= min_prob]
    if filter_max_prob:
        max_prob = float(filter_max_prob)
        filtered_predictions = [p for p in filtered_predictions if p['probability_percent'] <= max_prob]
    if filter_court:
        filtered_predictions = [p for p in filtered_predictions if filter_court.lower() in p['court'].lower()]
    if filter_judge:
        filtered_predictions = [p for p in filtered_predictions if filter_judge.lower() in p['judge'].lower()]
    
    # Сортировка
    sort_by = request.args.get('sort', 'caseId')
    sort_order = request.args.get('order', 'asc')
    
    sort_keys = {
        'caseId': 'caseId',
        'outcome': 'outcome',
        'probability': 'probability',
        'court': 'court',
        'judge': 'judge'
    }
    
    if sort_by in sort_keys:
        reverse = (sort_order == 'desc')
        if sort_by == 'probability':
            filtered_predictions.sort(key=lambda x: x['probability'], reverse=reverse)
        else:
            filtered_predictions.sort(key=lambda x: x[sort_keys[sort_by]], reverse=reverse)
    
    # Уникальные значения для фильтров
    outcomes = sorted(set(p['outcome'] for p in predictions))
    courts = sorted(set(p['court'] for p in predictions))
    judges = sorted(set(p['judge'] for p in predictions))
    
    return render_template('predictions.html', 
                         predictions=filtered_predictions,
                         outcomes=outcomes,
                         courts=courts,
                         judges=judges,
                         filter_case_id=filter_case_id,
                         filter_outcome=filter_outcome,
                         filter_min_prob=filter_min_prob,
                         filter_max_prob=filter_max_prob,
                         filter_court=filter_court,
                         filter_judge=filter_judge,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/participants', methods=['GET'])
def display_participants():
    participants = get_all_participants()
    
    # Фильтрация
    filter_fio = request.args.get('fio', '').strip()
    filter_type = request.args.get('participant_type', '').strip()
    filter_lawyer = request.args.get('lawyer', '').strip()
    filter_case_id = request.args.get('case_id', '').strip()
    
    filtered_participants = participants
    if filter_fio:
        filtered_participants = [p for p in filtered_participants if filter_fio.lower() in p['fio'].lower()]
    if filter_type and filter_type != "Все":
        filtered_participants = [p for p in filtered_participants if p['type'] == filter_type]
    if filter_lawyer:
        filtered_participants = [p for p in filtered_participants if filter_lawyer.lower() in p['lawyer'].lower()]
    if filter_case_id:
        filtered_participants = [p for p in filtered_participants if filter_case_id.lower() in p['caseId'].lower()]
    
    # Сортировка
    sort_by = request.args.get('sort', 'fio')
    sort_order = request.args.get('order', 'asc')
    
    sort_keys = {
        'fio': 'fio',
        'type': 'type',
        'lawyer': 'lawyer',
        'caseId': 'caseId'
    }
    
    if sort_by in sort_keys:
        reverse = (sort_order == 'desc')
        filtered_participants.sort(key=lambda x: x[sort_keys[sort_by]], reverse=reverse)
    
    # Уникальные типы участников
    participant_types = sorted(set(p['type'] for p in participants))
    
    return render_template('participants.html', 
                         participants=filtered_participants,
                         participant_types=participant_types,
                         filter_fio=filter_fio,
                         filter_type=filter_type,
                         filter_lawyer=filter_lawyer,
                         filter_case_id=filter_case_id,
                         sort_by=sort_by,
                         sort_order=sort_order)

if __name__ == '__main__':
    app.run(debug=True, port=5001)