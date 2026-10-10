import re
THEMES={"patrimoine":["patrimoine","histoire","historique","monument"],
"nature":["nature","environnement","biodiversité","biodiversite","forêt","foret"],
"sciences":["science","scientifique","astronomie"],"art et culture":["art","culture","musée","musee"],
"mer et littoral":["mer","littoral","plage","méditerranée","mediterranee"],"sport":["sport"]}
def analyze_request(text:str)->dict:
    low=text.lower()
    x={"intent":"discover_destination","departure_station_text":None,"departure_date":None,
       "student_count":None,"supervisor_count":None,"destination_text":None,"destination_known":False,
       "themes":[],"max_train_minutes":None,"missing_fields":[],"clarification_question":None,
       "analysis_mode":"prototype_rules"}
    for theme,words in THEMES.items():
        if any(w in low for w in words): x["themes"].append(theme)
    m=re.search(r"\\b(\\d{1,3})\\s+(?:élèves|eleves|élève|eleve)\\b",low)
    if m: x["student_count"]=int(m.group(1))
    m=re.search(r"\\b(\\d{1,2})\\s+(?:accompagnateurs|accompagnateur|adultes)\\b",low)
    if m: x["supervisor_count"]=int(m.group(1))
    m=re.search(r"\\b(20\\d{2}-\\d{2}-\\d{2})\\b",text)
    if m: x["departure_date"]=m.group(1)
    m=re.search(r"(?:au départ de|depart de|depuis)\\s+([A-Za-zÀ-ÿ' -]{2,60})",text,re.I)
    if m: x["departure_station_text"]=re.split(r",| le | pour | avec ",m.group(1),flags=re.I)[0].strip()
    m=re.search(r"(?:destination|visiter|aller à|aller a|à destination de)\\s+([A-Za-zÀ-ÿ' -]{2,60})",text,re.I)
    if m:
        val=re.split(r",| le | pour | avec ",m.group(1),flags=re.I)[0].strip()
        if val: x.update(destination_text=val,destination_known=True,intent="known_destination")
    m=re.search(r"(?:moins de|maximum|max\\.?)\\s+(\\d{1,3})\\s*(?:minutes|min)",low)
    if m: x["max_train_minutes"]=int(m.group(1))
    if not x["departure_station_text"]: x["missing_fields"].append("departure_station")
    if not x["departure_date"]: x["missing_fields"].append("departure_date")
    if not x["destination_known"] and not x["themes"] and x["max_train_minutes"] is None:
        x["missing_fields"].append("destination_or_discovery_criteria")
    if x["missing_fields"]: x["clarification_question"]="Précisez la gare de départ, la date précise et/ou les critères de découverte de destination."
    return x
