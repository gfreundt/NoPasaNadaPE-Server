import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="seleniumwire")

from pprint import pprint
import random


from src.test.test_data import get_test_data
from src.test import (
    brevete_manual,
    calmul_manual,
    satimp_manual,
    satmul_manual,
    soat_manual,
    recvehic_manual,
    revtec_manual,
    sutran_manual,
)


def run_all_manual_tests():
    sample_size = [1, 1, 1, 1, 1, 1, 1, 1, 1]
    c = get_test_data(sample_size=sample_size)
    pprint(c)

    tests = [
        {
            "name": "Brevete Manual Test",
            "fn": brevete_manual.gather,
            "data": c["DataMtcBrevetes"],
        },
        {
            "name": "Calmúl Manual Test",
            "fn": calmul_manual.gather,
            "data": c["DataCallaoMultas"],
        },
        {
            "name": "SAT Impuesto Manual Test",
            "fn": satimp_manual.gather,
            "data": c["DataSatImpuestos"],
        },
        {
            "name": "SAT Multas Manual Test",
            "fn": satmul_manual.gather,
            "data": c["DataSatMultas"],
        },
        {
            "name": "SOAT Manual Test",
            "fn": soat_manual.gather,
            "data": c["DataApesegSoats"],
        },
        {
            "name": "Record Vehicular Manual Test",
            "fn": recvehic_manual.gather,
            "data": c["DataMtcRecordsConductores"],
        },
        {
            "name": "Revisión Técnica Manual Test",
            "fn": revtec_manual.gather,
            "data": c["DataMtcRevisionesTecnicas"],
        },
        {
            "name": "SUTRAN Manual Test",
            "fn": sutran_manual.gather,
            "data": c["DataSutranMultas"],
        },
    ]

    random.shuffle(tests)

    for k, test in enumerate(tests, start=1):
        print(f"\nRunning {k}/{len(tests)} -- {test['name']}")
        try:
            test["fn"](test["data"])
            print("✅ Success!")
        except Exception as e:
            print(f"❌ {test['name']} failed: {e}")


if __name__ == "__main__":
    run_all_manual_tests()
