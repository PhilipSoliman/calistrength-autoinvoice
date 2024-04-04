import json
from calendar import Calendar
from calendar import month_name as MONTH_NAMES
from datetime import date as Date

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

MONTH_NAMES = MONTH_NAMES[1:]  # month_names starts with empty string

START_YEAR = 2024

CURRENT_YEAR = Date.today().year

MAX_YEARS = 10

INVOICE_YEARS = [str(year) for year in range(START_YEAR, START_YEAR + MAX_YEARS)]

ORDINAL_BASE_EXCEL = Date(1900, 1, 1).toordinal() - 2


def getAvailableClients(params, **kwargs):
    """
    Get list of available clients from finance data
    """
    return getFinanceDataAttributeFromStorage("availableClients")


def getAvailableDates(params, **kwargs):
    """
    Get list of available dates from finance data and given client
    """
    if (client := params.invoiceStep.get("clientName")) is None:
        UserMessage.info("Please specify a client to get available dates")
        dates = []
    else:
        clientData = getFinanceDataAttributeFromStorage(client)
        dates = [date for date in clientData]
    return dates


def getAvailablePeriods(params, **kwargs):
    """
    Get list of available periods from finance data and given client
    """
    if (client := params.invoiceStep.get("clientName")) is None:
        UserMessage.info("Please specify a client to get available periods")
        periods = []
    else:
        ordinals = getFinanceDataAttributeFromStorage(client).keys()
        list(map(int, ordinals))
    return periods


def convertExcelOrdinal(excelDateNumber: str) -> str:
    """
    Convert Excel date number to human readable date
    """
    excelOrdinal = int(excelDateNumber)
    return str(excelOrdinal + ORDINAL_BASE_EXCEL)


def convertOrdinalToDate(ordinal: str) -> str:
    """
    Convert ordinal to date
    """
    return Date.fromordinal(int(ordinal)).strftime(r"%d/%m/%y")


def convertDateToOrdinal(date: str) -> str:
    """
    Convert date to ordinal
    """
    d, m, y = [int(i) for i in date.split("/")]
    return Date(d, m, y).toordinal()


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


def getFinanceDataAttributeFromStorage(key: str) -> dict:
    """
    Get finance data attributes from storage
    """
    financeData = getFinanceDataFromStorage()
    if (data := financeData.get(key)) is None:
        raise UserError(f"Could not find {key} in finance data")
    return data


def saveFinanceDataToStorage(financeData: dict) -> None:
    """
    Save finance data to storage
    """
    storage = Storage()
    financeDataFile = File.from_data(json.dumps(financeData))
    storage.set("financeData", data=financeDataFile, scope="entity")


def getInvoicePeriods(params, **kwargs) -> list[str]:
    if (year := params.invoiceStep.get("invoiceYear")) is None:
        UserMessage.info("Please specify a year to get available periods")
    periods = generateInvoicePeriods(int(year))
    return periods


def generateInvoicePeriods(year: int) -> list[str]:
    periods = []
    cal = Calendar()
    for monthNr, monthName in enumerate(MONTH_NAMES, start=1):
        monthDays = list(cal.itermonthdays(year, monthNr))
        periods.append(f"1 {monthName.lower()} - {max(monthDays)} {monthName.lower()}")
    return periods


def checkInvoiceSetup(params, **kwargs) -> bool:
    """
    Check existence of invoice in database
    """
    invoiceSetup = [
        params.invoiceStep.get("clientName"),
        params.invoiceStep.get("invoiceDate"),
        params.invoiceStep.get("invoicePeriod"),
        params.invoiceStep.get("expirationDate"),
    ]
    if None in invoiceSetup:
        UserMessage.warning("Missing invoice setup parameters")
        return False

    # check if client exists in finance data
    financeData = getFinanceDataFromStorage()
    if (clientData := financeData.get(params.invoiceStep.clientName)) is None:
        UserMessage.warning("Client not found in finance data")
        return False

    # check if invoice exists in finance data
    if clientData.get(params.invoiceStep.invoiceDate) is None:
        UserMessage.warning("Invoice not found in finance data")
        return False

    # if all of the above checks pass, return True
    return True


def getInvoiceNumber(client: str, invoiceDate: str) -> str:
    """
    Get invoice number
    """
    # TODO: implement
    return "some invoice number"
