from io import BytesIO

import pandas as pd

def convert_lineitems_to_csv(lineitems: list[dict]) -> BytesIO:

    csv = BytesIO()

    if lineitems == None or len(lineitems) == 0:
        blank_df = pd.DataFrame()
        blank_df.to_csv(csv, index=False)
        csv.seek(0)
        return csv

    column_order = [
        "Score",
        "Release",
        "Chapter Number",
        "HS Hdg", 
        "HS Code", 
        "SC Code","HS Hdg Name",
        "Prefix",
        "Description", 
        "Unit",
        "ICL/SLSI","Preferential Duty_AP",
        "Preferential Duty_AD",
        "Preferential Duty_BN","Preferential Duty_GT",
        "Preferential Duty_IN",
        "Preferential Duty_PK","Preferential Duty_SA",
        "Preferential Duty_SF",
        "Preferential Duty_SD","Preferential Duty_SG",
        "Gen Duty",
        "VAT",
        "PAL_Gen",
        "PAL_SG","Cess_GEN",
        "Cess_SG",
        "Excise SPD",
        "Surcharge on Customs Duty","SSCL","SCL"]

    df = pd.DataFrame(lineitems)
    df = df.reindex(columns=column_order)
    df.to_csv(csv, index=False)
    csv.seek(0)
    return csv

