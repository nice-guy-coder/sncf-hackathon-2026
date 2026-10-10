import argparse, sys
from pathlib import Path
from openpyxl import load_workbook
from sqlalchemy import select
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db import Base,engine,SessionLocal
from app.models import Accommodation
def clean(v): return None if v is None or str(v).strip()=="" else str(v).strip()
def num(v,kind):
    try: return kind(v) if v not in (None,"") else None
    except (TypeError,ValueError): return None
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--file",required=True); args=parser.parse_args()
    path=Path(args.file)
    if not path.exists(): raise SystemExit(f"Fichier introuvable : {path}")
    wb=load_workbook(path,data_only=True,read_only=True)
    if "Hebergements Occitanie" not in wb.sheetnames: raise SystemExit("Onglet Hebergements Occitanie absent.")
    ws=wb["Hebergements Occitanie"]; iterator=ws.iter_rows(values_only=True)
    headers=[clean(v) for v in next(iterator)]; ix={h:i for i,h in enumerate(headers) if h}
    Base.metadata.create_all(bind=engine); db=SessionLocal()
    counts={"read":0,"created":0,"updated":0,"rejected":0}
    try:
        for rownum,row in enumerate(iterator,start=2):
            if not any(v is not None for v in row): continue
            counts["read"]+=1
            def get(k): return row[ix[k]] if k in ix and ix[k]<len(row) else None
            name,commune=clean(get("Structure")),clean(get("Commune"))
            if not name or not commune: counts["rejected"]+=1; continue
            source_id=f"{path.name}:Hebergements Occitanie:{rownum}"
            obj=db.scalar(select(Accommodation).where(Accommodation.source_record_id==source_id))
            data={"source_record_id":source_id,"name":name,"commune":commune,
              "department":clean(get("Departement")),"postal_code":clean(get("CodePostal")),
              "latitude":num(get("Latitude"),float),"longitude":num(get("Longitude"),float),
              "themes_raw":clean(get("Thematiques")),"student_beds":num(get("Lits_eleves"),int),
              "supervisor_beds":num(get("Lits_encadrants"),int),"reference_tariff":clean(get("Tarif_reference_ministere")),
              "nature_label":clean(get("Label_ma_classe_nature")),"accessible_handicap":clean(get("Accessible_handicap")),
              "opening_period":clean(get("Periode_ouverture")),"classrooms":clean(get("Salles_de_classe")),
              "coach_charter":clean(get("Transport_autocar_charte")),"nearby_sites_raw":clean(get("Sites_a_proximite")),
              "website_url":clean(get("Site_internet")),"permalink":clean(get("Permalien")),
              "total_capacity":num(get("Capacite_totale"),int),"nearest_station_raw":clean(get("Gare_principale_plus_proche")),
              "straight_line_distance_km":num(get("Distance_vol_oiseau_km"),float),"source_name":path.name}
            if obj:
                for k,v in data.items(): setattr(obj,k,v)
                counts["updated"]+=1
            else: db.add(Accommodation(**data)); counts["created"]+=1
        db.commit(); print(counts)
    finally: db.close(); wb.close()
if __name__=="__main__": main()
