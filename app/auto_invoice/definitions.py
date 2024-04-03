import datetime
import json

from viktor.core import File, Storage, UserMessage
from viktor.errors import UserError

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
    financeData = getFinanceDataFromStorage()
    if (availableClients := financeData.get("availableClients")) is None:
        raise UserError("Could not find available clients in finance data")
    return availableClients

def getAvailableDates(params, **kwargs):
    """
    Get list of available dates from finance data and given client
    """
    if (client := params.get("clientName")) is None:
        UserMessage.info("Please specify a client to get available dates")
        dates = []
    else:
        financeData = getFinanceDataFromStorage()
        if (clientData := financeData.get(client)) is None:
            raise UserError(f"Could not find data for client {client} in finance data")
        dates = list(clientData.keys())
    return dates

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


def getFinanceDataFromStorage() -> dict:
    """
    Get finance data from storage
    """
    storage = Storage()
    if "financeData" not in storage.list(scope="entity"):
        raise UserError("Could not find finance data in storage")
    financeDataFile = storage.get("financeData", scope="entity")
    return json.loads(financeDataFile.getvalue())


def saveFinanceDataToStorage(financeData: dict) -> None:
    """
    Save finance data to storage
    """
    storage = Storage()
    financeDataFile = File.from_data(json.dumps(financeData))
    storage.set("financeData", data=financeDataFile, scope="entity")
