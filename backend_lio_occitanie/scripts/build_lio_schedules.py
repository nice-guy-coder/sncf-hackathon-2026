import zipfile
import xml.etree.ElementTree as ET
import csv
import json
import re
from pathlib import Path
from collections import defaultdict

def main():
    doc_dir = Path(__file__).resolve().parents[3] # /home/mattl/Documents/Prog/Projet SNCF/Documents
    backend_dir = doc_dir / "sncf-hackathon-2026" / "backend_lio_occitanie"
    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    csv_path = doc_dir / "Data_Hackathon.csv"
    xlsx_path = doc_dir / "Détail desserte (1).xlsx"

    print("1. Lecture de Data_Hackathon.csv...")
    train_stats = defaultdict(lambda: {"regs": [], "supps": [], "emports": [], "axe": "", "od": ""})
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            t_num = r.get("N° Train", "").strip()
            if not t_num:
                continue
            train_stats[t_num]["axe"] = r.get("Axe", "").strip()
            train_stats[t_num]["od"] = r.get("Origine / Destination", "").strip()
            def clean_p(v):
                if not v:
                    return None
                try:
                    return float(v.replace("%", "").replace(",", ".").strip())
                except Exception:
                    return None
            reg = clean_p(r.get("Taux régularité du train"))
            supp = clean_p(r.get("Taux SUPP"))
            emp = clean_p(r.get("Taux de respect de l'emport"))
            if reg is not None:
                train_stats[t_num]["regs"].append(reg)
            if supp is not None:
                train_stats[t_num]["supps"].append(supp)
            if emp is not None:
                train_stats[t_num]["emports"].append(emp)

    stats_summary = {}
    all_regs, all_supps, all_emps = [], [], []
    for t_num, d in train_stats.items():
        avg_reg = round(sum(d["regs"]) / len(d["regs"]), 1) if d["regs"] else None
        avg_supp = round(sum(d["supps"]) / len(d["supps"]), 1) if d["supps"] else None
        avg_emp = round(sum(d["emports"]) / len(d["emports"]), 1) if d["emports"] else None
        if avg_reg:
            all_regs.append(avg_reg)
        if avg_supp:
            all_supps.append(avg_supp)
        if avg_emp:
            all_emps.append(avg_emp)
        stats_summary[t_num] = {
            "axe": d["axe"],
            "od": d["od"],
            "regularity_rate": avg_reg,
            "cancellation_rate": avg_supp,
            "emport_rate": avg_emp
        }

    global_avg_reg = round(sum(all_regs) / len(all_regs), 1) if all_regs else 86.4
    global_avg_supp = round(sum(all_supps) / len(all_supps), 1) if all_supps else 4.8
    global_avg_emp = round(sum(all_emps) / len(all_emps), 1) if all_emps else 91.2

    print(f"Stats prêtes pour {len(stats_summary)} trains. Moyennes liO globales: Régularité={global_avg_reg}%, Suppressions={global_avg_supp}%")

    print("2. Lecture de Détail desserte (1).xlsx...")
    with zipfile.ZipFile(xlsx_path) as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in ss_tree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                texts = [t.text for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text]
                shared_strings.append("".join(texts))

        s1_tree = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows = list(s1_tree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"))

        first_date = None
        circ_stops = defaultdict(list)
        # Traitement d'une journée type complète de circulations
        for row in rows[1:120000]:
            r_vals = []
            for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                t = c.attrib.get("t")
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                val = v.text if v is not None else ""
                if t == "s" and val.isdigit():
                    val = shared_strings[int(val)]
                r_vals.append(val)
            if len(r_vals) >= 7:
                date, circ_no, arr, dep, stop_name, code, order = r_vals[:7]
                if not first_date:
                    first_date = date
                if date == first_date:
                    circ_stops[circ_no].append({
                        "order": int(order) if order.isdigit() else 0,
                        "stop": stop_name.strip(),
                        "arr": arr.strip() if arr else "",
                        "dep": dep.strip() if dep else ""
                    })

    print(f"Circulations analysées pour la journée type ({len(circ_stops)} trains).")

    connections = []
    for circ_no, stops in circ_stops.items():
        stops = sorted(stops, key=lambda x: x["order"])
        stat = stats_summary.get(circ_no, {
            "axe": "Ligne liO Occitanie",
            "od": f"{stops[0]['stop']} - {stops[-1]['stop']}",
            "regularity_rate": global_avg_reg,
            "cancellation_rate": global_avg_supp,
            "emport_rate": global_avg_emp
        })

        for i in range(len(stops)):
            for j in range(i + 1, len(stops)):
                dep_stop = stops[i]["stop"]
                arr_stop = stops[j]["stop"]
                dep_time = stops[i]["dep"] or stops[i]["arr"]
                arr_time = stops[j]["arr"] or stops[j]["dep"]
                if not dep_time or not arr_time:
                    continue

                try:
                    dh, dm = [int(x) for x in dep_time.split(":")[:2]]
                    ah, am = [int(x) for x in arr_time.split(":")[:2]]
                    dur = (ah * 60 + am) - (dh * 60 + dm)
                    if dur < 0:
                        dur += 24 * 60
                except Exception:
                    dur = 60

                # Places déjà réservées réalistes pour la démonstration de la jauge (0 à 25 pax)
                h = sum(ord(c) for c in (circ_no + dep_stop)) % 26
                booked = h
                available = 50 - booked

                connections.append({
                    "train_number": circ_no,
                    "origin": dep_stop,
                    "destination": arr_stop,
                    "departure_time": dep_time[:5],
                    "arrival_time": arr_time[:5],
                    "duration_minutes": dur,
                    "axe": stat.get("axe", "Ligne liO Occitanie"),
                    "regularity_rate": stat.get("regularity_rate") or global_avg_reg,
                    "cancellation_rate": stat.get("cancellation_rate") or global_avg_supp,
                    "emport_rate": stat.get("emport_rate") or global_avg_emp,
                    "max_capacity": 50,
                    "booked_seats": booked,
                    "available_seats": available,
                    "group_authorized": True
                })

    print(f"Total des liaisons directes liO générées : {len(connections)}")
    out_file = data_dir / "lio_train_schedules.json"
    with open(out_file, "w", encoding="utf-8") as out:
        json.dump(connections, out, ensure_ascii=False, indent=2)
    print(f"Enregistré dans {out_file}")

if __name__ == "__main__":
    main()
