from flask import Flask, render_template
import rdflib

app = Flask(__name__, template_folder='templates')

# Загружаем онтологию судебных дел
graph = rdflib.Graph()
graph.parse("legal.owl", format="xml")

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
    return render_template('cases.html', cases=cases)

@app.route('/predictions', methods=['GET'])
def display_predictions():
    predictions = get_all_predictions()
    return render_template('predictions.html', predictions=predictions)

@app.route('/participants', methods=['GET'])
def display_participants():
    participants = get_all_participants()
    return render_template('participants.html', participants=participants)

if __name__ == '__main__':
    app.run(debug=True, port=5001)