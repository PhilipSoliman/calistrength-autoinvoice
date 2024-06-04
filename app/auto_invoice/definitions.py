import json
from calendar import Calendar
from calendar import month_name as MONTH_NAMES
from datetime import date as Date
from pprint import pprint

import numpy as np
from deep_translator import GoogleTranslator
from viktor.core import File, Storage, UserMessage
from viktor.errors import InputViolation, UserError

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
    if data := getFinanceDataAttributeFromStorage("availableClients"):
        return data
    return []


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


def convertExcelOrdinal(excelDateNumber: int) -> int:
    """
    Convert Excel date number to human readable date
    """
    return excelDateNumber + ORDINAL_BASE_EXCEL


def convertOrdinalToDate(ordinal: int) -> str:
    """
    Convert ordinal to date
    """
    return Date.fromordinal(ordinal).strftime(r"%d/%m/%Y")


def convertDateToOrdinal(date: str) -> str:
    """
    Convert date to ordinal
    """
    d, m, y = [int(i) for i in date.split("/")]
    # y = getYearFromYearNr(y)
    return Date(y, m, d).toordinal()


def convertExcelFloat(excelFloat: np.ndarray) -> float:
    """
    convert Excel-style float to regular float
    """
    return np.char.replace(excelFloat, ",", ".").astype(np.float64)


def getFinanceDataFromStorage() -> dict:
    """
    Get finance data from storage
    """
    storage = Storage()
    if "financeData" not in storage.list(scope="entity"):
        UserMessage.warning("Could not find finance data in storage")
        return {}
    financeDataFile = storage.get("financeData", scope="entity")
    return json.loads(financeDataFile.getvalue())


def getFinanceDataAttributeFromStorage(key: str) -> dict:
    """
    Get finance data attributes from storage
    """
    financeData = getFinanceDataFromStorage()
    if (data := financeData.get(key)) is None:
        UserMessage.warning(f"Could not find {key} in finance data")
    return data


def saveFinanceDataToStorage(financeData: dict) -> None:
    """
    Save finance data to storage
    """
    storage = Storage()
    financeDataFile = File.from_data(json.dumps(financeData))
    storage.set("financeData", data=financeDataFile, scope="entity")


def getInvoiceYears(params, **kwargs) -> list[str]:
    """
    Get list of available invoice years
    """
    if (clientName := params.invoiceStep.get("clientName")) is None:
        return []
    clientData = getFinanceDataAttributeFromStorage(clientName)
    years = []
    if availableInvoiceNumbers := clientData.get("availableInvoiceNumbers"):
        for invoiceNumber in availableInvoiceNumbers:
            yearNr = invoiceNumber.split(".")[-1]
            year = getYearFromYearNr(yearNr)
            if year not in years and year is not None:
                years.append(getYearFromYearNr(yearNr))
    return years


def getInvoicePeriods(params, **kwargs) -> list[str]:
    if (year := params.invoiceStep.get("invoiceYear")) is None:
        UserMessage.info("Please specify a year to get available periods")
        return []
    periods = generateInvoicePeriods(int(year))
    return periods


def generateInvoicePeriods(year: int) -> list[str]:
    periods = []
    cal = Calendar()
    for monthNr, monthName in enumerate(MONTH_NAMES, start=1):
        monthDays = list(cal.itermonthdays(year, monthNr))
        period_eng = f"1 {monthName.lower()} - {max(monthDays)} {monthName.lower()}"
        period_nl = GoogleTranslator(source="en", target="nl").translate(period_eng)
        periods.append(period_nl)
    return periods


def getInvoiceIndices(params, **kwargs) -> list[str]:
    """
    Get list of available invoice indices for a given client, year and period
    """
    if (year := params.invoiceStep.get("invoiceYear")) is None:
        return []
    yearNr = getYearNr(year)
    if (period := params.invoiceStep.get("invoicePeriod")) is None:
        return []
    periodNr = getPeriodNr(year, params.invoiceStep.get("invoicePeriod"))
    generalErroMsg = "Cannot find invoices"
    clientData = getFinanceDataAttributeFromStorage(
        params.invoiceStep.get("clientName")
    )
    indices = []
    for invoiceNumber in clientData["availableInvoiceNumbers"]:
        elements = invoiceNumber.split(".")
        if len(elements) != 4:
            continue
        _, index, _periodNr, _yearNr = invoiceNumber.split(".")
        if (_periodNr == periodNr) and (_yearNr == yearNr) and index not in indices:
            indices.append(index)
    if indices == []:
        fields = [
            "clientName",
            "invoiceStep.invoiceYear",
            "invoiceStep.invoicePeriod",
        ]
        violation = InputViolation(
            "No indices found for given client, year and period", fields=fields
        )
        raise UserError(generalErroMsg, input_violations=violation)
    return indices


def checkInvoiceSetup(params, **kwargs) -> bool:
    """
    Check existence of invoice in database
    """
    invoiceSetup = [
        params.invoiceStep.get("clientName"),
        params.invoiceStep.get("invoiceNumber"),
        params.invoiceStep.get("invoiceYear"),
        params.invoiceStep.get("invoicePeriod"),
        params.invoiceStep.get("invoiceIndex"),
        params.invoiceStep.get("invoiceDate"),
    ]
    if None in invoiceSetup:
        UserMessage.warning("Missing invoice setup parameters")
        return False

    # check if client exists in finance data
    financeData = getFinanceDataFromStorage()
    if (clientData := financeData.get(params.invoiceStep.clientName)) is None:
        UserMessage.warning("Client not found in finance data")
        return False

    return True


def getInvoicePeriodFromNumber(invoiceNumber: int) -> tuple[str, int]:
    """
    Get invoice period from invoice number
    """
    indexNr, periodNr, yearNr = invoiceNumber.split(".")[1:]
    year = getYearFromYearNr(yearNr)
    periods = generateInvoicePeriods(year)
    return indexNr, periods[int(periodNr) - 1], year


def getInvoiceNumberFromPeriodAndIndex(
    client: str, index: str, period: str, year: int
) -> int:
    """
    Get invoice number from period and year
    """
    clientNumber = getClientNr(client)
    periodNr = getPeriodNr(year, period)
    yearNr = getYearNr(year)
    return f"{clientNumber}.{index}.{periodNr}.{yearNr}"


def getavailableInvoiceNumbers(params, **kwargs) -> list[str]:
    """
    Get list of available invoice numbers from finance data and given client
    """
    if (
        clientData := getFinanceDataAttributeFromStorage(
            params.invoiceStep.get("clientName")
        )
    ) is not None:
        return clientData["availableInvoiceNumbers"]
    return []


def getClientNr(clientName: str) -> str:
    """
    Get client number
    """
    clients = getFinanceDataAttributeFromStorage("availableClients")
    numbers = getFinanceDataAttributeFromStorage("clientNumbers")
    return numbers[clients.index(clientName)]


def getPeriodNr(year: int, period: str) -> str:
    periods = generateInvoicePeriods(year)
    periodNr = periods.index(period) + 1
    if periodNr < 10:
        periodNr = f"0{periodNr}"
    else:
        periodNr = str(periodNr)
    return periodNr


def getYearNr(year: int) -> str:
    return str(year - 2000)


def getYearFromYearNr(yearNr: int | str) -> int:
    try:
        yearNr = int(yearNr)
        return int(yearNr) + 2000
    except ValueError:
        return


def getPeriodOrdinals(period: int, year: str) -> tuple[int]:
    """
    Get ordinals for start and end of period
    """
    year = int(year)
    start = Date(year, period + 1, 1).toordinal()
    cal = Calendar()
    monthDays = list(cal.itermonthdays(year, period + 1))
    lastday = max(monthDays)
    end = Date(year, period + 1, lastday).toordinal()
    return start, end


def removeSpecialCharacters(string: str) -> str:
    """
    Remove special characters from string
    """
    return "".join(e for e in string if e.isalnum())


def generateInvoiceName(params, fn_ext: str) -> str:
    invoiceNumberStripped = params.invoiceStep.invoiceNumber.replace(".", "")
    clientName = params.invoiceStep.clientName
    clientName = removeSpecialCharacters(clientName)
    return f"Factuur_{invoiceNumberStripped}_{clientName}_CALISTRENGTH.{fn_ext}"
