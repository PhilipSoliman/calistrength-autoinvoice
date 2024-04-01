import datetime

INVOICE_PERIODS = [
    "1 januari - 31 januari",
    "1 februari - 28 februari",
    "1 maart - 31 maart",
    "1 april - 30 april",
    "1 mei - 31 mei",
    "1 juni - 30 juni",
    "1 juli - 31 juli",
    "1 augustus - 31 augustus",
    "1 september - 30 september",
    "1 oktober - 31 oktober",
    "1 november - 30 november",
    "1 december - 31 december",
]

INVOICE_YEARS = [str(year) for year in range(2024, 2030)]


def getAvailableClients(params, **kwargs):
    """
    Get list of available clients from finance data
    """
    return params.uploadStep.financeData["availableClients"]


def convertExcelDate(excelDateNumber: str) -> str:
    """
    Convert Excel date number to human readable date
    """
    # TODO: implement
    # baseDateExcel = datetime.datetime(1900, 1, 1)
    # delta = datetime.timedelta(days=dateNumber - 2)
    return


def convertExcelFloat(excelFloat: str) -> float:
    """
    convert Excel-style float to regular float
    """
    return float(excelFloat.replace(",", "."))
