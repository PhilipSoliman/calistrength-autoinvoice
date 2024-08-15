import base64
from datetime import date as Date
from io import BytesIO
from json import dumps, loads

import numpy as np
from viktor.api_v1 import FileResource
from viktor.core import File, UserMessage
from viktor.errors import UserError
from viktor.external.spreadsheet import (
    SpreadsheetCalculation,
    SpreadsheetCalculationInput,
)
from viktor.utils import memoize

ORDINAL_BASE_EXCEL = Date(1900, 1, 1).toordinal() - 2


class ExcelReader:

    def readFinanceSheet(financeSheet: FileResource) -> dict:
        """
        Read finance sheet and return it as a base64 encoded string
        """
        financeFile = ExcelReader._obtainFileFromResource(financeSheet)
        financeFile_s = ExcelReader._serialize(financeFile)
        financeData_s = ExcelReader._getFinanceData(financeFile_s)
        return loads(financeData_s)

    @memoize
    def _getFinanceData(financeFile_s: str) -> str:
        """
        Load finance data from uploaded excel file. Optionally pass any inputs from user
        (Not implemented yet)
        """
        print("Reading finance sheet...")
        # financeFile = File.from_data(ExcelReader._deserialize(financeFile_s))
        financeFile = ExcelReader._deserialize(financeFile_s)
        financeSheet = SpreadsheetCalculation(
            financeFile, [SpreadsheetCalculationInput("clientName", "")]
        )
        financeData = financeSheet.evaluate(include_filled_file=False).values
        for itemKey, dataString in financeData.items():
            if isinstance(dataString, str):
                values = dataString.split(";")
                valueArray = np.array(values)
                empty = valueArray == ""
                valueArray[empty] = "NA"
            else:
                raise UserError("Data values in finance sheet should be strings")
            if itemKey in [
                "clients",
                "availableClients",
                "clientNumbers",
                "invoiceNumbers",
                "description",
                "clientLegalContact",
                "clientStreetAndNumber",
                "clientPostalCode",
                "clientCity",
                "clientEmail",
            ]:  # data is a list of strings
                financeData[itemKey] = valueArray.tolist()
            elif itemKey in [
                "pricesIncl",
                "pricesExcl",
                "quantity",
            ]:  # data is a list of floats
                floats = valueArray[~empty]
                valueArray[~empty] = ExcelReader._convertExcelFloat(floats).tolist()
                financeData[itemKey] = valueArray
            elif itemKey == "invoiceDates":  # data is a list of dates
                values = valueArray.tolist()
                financeData[itemKey] = []
                for value in values:
                    if value != "NA":
                        financeData[itemKey] += [
                            ExcelReader._convertOrdinalToDate(
                                ExcelReader._convertExcelOrdinal(int(value))
                            )
                        ]
                    else:
                        financeData[itemKey] += [value]

            else:  # unknown key
                raise UserError(f"Unknown key {itemKey} in finance data sheet")
        financeData = ExcelReader._sortFinanceData(financeData)
        return dumps(financeData)

    @staticmethod
    def _obtainFileFromResource(fileResource: FileResource) -> File:
        """
        Obtain file from params
        """
        file = None
        try:
            file = fileResource.file
        except AttributeError:
            raise UserError(f"No finance (*.xlsx) file found.")
        return file

    @staticmethod
    def _sortFinanceData(financeData: dict) -> dict:
        """
        sort by clients first then by date. This is also the structure of database
        """
        sortedFinanceData = {}
        for client in financeData["availableClients"]:
            sortedFinanceData[client] = {"availableInvoiceNumbers": []}
        for i, client in enumerate(financeData["clients"]):
            if client not in financeData["availableClients"]:
                continue
            date = financeData["invoiceDates"][i]
            invoiceNumber = financeData["invoiceNumbers"][i]
            sortedFinanceData[client][date] = {
                "priceIncl": financeData["pricesIncl"][i],
                "priceExcl": financeData["pricesExcl"][i],
                "invoiceNumber": invoiceNumber,
                "quantity": financeData["quantity"][i],
                "description": financeData["description"][i],
            }
            if (
                invoiceNumber
                not in sortedFinanceData[client]["availableInvoiceNumbers"]
            ):
                sortedFinanceData[client]["availableInvoiceNumbers"].append(
                    financeData["invoiceNumbers"][i]
                )
        clients = np.array(financeData["availableClients"])
        sortedFinanceData["availableClients"] = clients[clients != "NA"].tolist()
        clientNumbers = np.array(financeData["clientNumbers"])
        sortedFinanceData["clientNumbers"] = clientNumbers[
            clientNumbers != "NA"
        ].tolist()

        clientLegalContact = np.array(financeData["clientLegalContact"])
        clientLegalContact = clientLegalContact[clientLegalContact != "NA"].tolist()
        clientStreetAndNumber = np.array(financeData["clientStreetAndNumber"])
        clientStreetAndNumber = clientStreetAndNumber[
            clientStreetAndNumber != "NA"
        ].tolist()
        clientPostalCode = np.array(financeData["clientPostalCode"])
        clientPostalCode = clientPostalCode[clientPostalCode != "NA"].tolist()
        clientCity = np.array(financeData["clientCity"])
        clientCity = clientCity[clientCity != "NA"].tolist()
        clientEmail = np.array(financeData["clientEmail"])
        clientEmail = clientEmail[clientEmail != "NA"].tolist()

        clients = clients.tolist()
        for client in sortedFinanceData["availableClients"]:
            clientIndex = clients.index(client)
            try:
                sortedFinanceData[client]["legalContact"] = clientLegalContact[
                    clientIndex
                ]
                sortedFinanceData[client]["streetAndNumber"] = clientStreetAndNumber[
                    clientIndex
                ]
                sortedFinanceData[client]["postalCode"] = clientPostalCode[clientIndex]
                sortedFinanceData[client]["city"] = clientCity[clientIndex]
                sortedFinanceData[client]["email"] = clientEmail[clientIndex]
            except IndexError:
                UserMessage.warning(f"Client {client} is missing contact information")

        return sortedFinanceData

    def _serialize(file: File) -> str:
        """
        Encodes a File object to a base64-encoded string.
        """
        return base64.b64encode(file.getvalue_binary()).decode(encoding="utf-8")

    def _deserialize(s: str) -> File:
        """
        Decodes a base64-encoded string to a File object.
        """
        return File.from_data(base64.b64decode(s.encode(encoding="utf-8")))

    def _convertExcelFloat(excelFloat: np.ndarray) -> float:
        """
        convert Excel-style float to regular float
        """
        return np.char.replace(excelFloat, ",", ".").astype(np.float64)

    def _convertExcelOrdinal(excelDateNumber: int) -> int:
        """
        Convert Excel date number to human readable date
        """
        return excelDateNumber + ORDINAL_BASE_EXCEL

    def _convertOrdinalToDate(ordinal: int) -> str:
        """
        Convert ordinal to date
        """
        return Date.fromordinal(ordinal).strftime(r"%d/%m/%Y")
