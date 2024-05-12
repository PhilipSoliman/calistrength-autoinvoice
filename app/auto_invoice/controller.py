from pprint import pprint

import numpy as np
from munch import Munch, unmunchify
from viktor import ViktorController
from viktor.api_v1 import FileResource
from viktor.core import File, Storage, UserMessage
from viktor.errors import UserError
from viktor.external.spreadsheet import (
    SpreadsheetCalculation,
    SpreadsheetCalculationInput,
    SpreadsheetResult,
)
from viktor.external.word import WordFileTag, render_word_file
from viktor.result import DownloadResult, SetParamsResult
from viktor.utils import convert_word_to_pdf
from viktor.views import DataGroup, DataItem, DataResult, DataView, PDFResult, PDFView

from app.auto_invoice.definitions import (
    checkInvoiceSetup,
    convertDateToOrdinal,
    convertExcelFloat,
    convertExcelOrdinal,
    convertOrdinalToDate,
    generateInvoiceName,
    getFinanceDataAttributeFromStorage,
    getFinanceDataFromStorage,
    getInvoiceNumberFromPeriodAndIndex,
    getInvoicePeriodFromNumber,
    getInvoicePeriods,
    getPeriodOrdinals,
    removeSpecialCharacters,
    saveFinanceDataToStorage,
)
from app.auto_invoice.parametrization import Parametrization
from app.helper import pyutils


class Controller(ViktorController):
    label = "autoInvoice"
    parametrization = Parametrization

    def updateFinanceData(self, params, **kwargs) -> None:
        """
        Update finance data in storage
        """
        oldFinanceData = {}
        financeData = self.getFinanceDataExcel(params)
        storage = Storage()
        if "financeData" in storage.list(scope="entity"):
            oldFinanceData = getFinanceDataFromStorage()

        # compare old and new data
        if financeData == oldFinanceData:
            UserMessage.info("No changes detected in finance data")
            return
        else:
            UserMessage.info("New clients data detected")

        # update finance data
        UserMessage.info("Updating finance data")
        newFinanceData = dict(oldFinanceData)
        for client in financeData["availableClients"]:
            if client not in newFinanceData:
                newFinanceData[client] = financeData[client]
            else:
                newFinanceData[client].update(financeData[client])

        newFinanceData["availableClients"] = financeData["availableClients"]
        newFinanceData["clientNumbers"] = financeData["clientNumbers"]

        # save new finance data
        saveFinanceDataToStorage(newFinanceData)
        UserMessage.success("Finance data updated")

    @DataView("Finance data", duration_guess=1)
    def viewFinanceData(self, params, **kwargs) -> SpreadsheetResult:
        """
        View finance data
        """
        financeData = getFinanceDataFromStorage()
        return DataResult(Controller.unpackDataIntoDataItems(financeData))

    def setupInvoice(self, params, **kwargs) -> SetParamsResult:
        """
        Search for invoice in finance data. The goal of this function
        is to make sure that invoice number, date & period (+year) are set.
        such that downstream functions can find all the relevant assignments
        and payment data.
        """
        params.invoiceStep.foundInvoice = False
        invoiceParams = params.invoiceStep
        if invoiceParams.searchMethod == "Factuurperiode":
            clientName = params.invoiceStep.clientName
            period = params.invoiceStep.invoicePeriod
            year = params.invoiceStep.invoiceYear
            index = params.invoiceStep.invoiceIndex
            invoiceParams.invoiceNumber = getInvoiceNumberFromPeriodAndIndex(
                clientName, index, period, year
            )
        if invoiceParams.searchMethod == "Factuurnummer":
            index, period, year = getInvoicePeriodFromNumber(
                params.invoiceStep.invoiceNumber
            )
            invoiceParams.invoiceIndex = index
            invoiceParams.invoicePeriod = period
            invoiceParams.invoiceYear = year

        UserMessage.success("Factuur samengesteld!")
        return SetParamsResult({"invoiceStep": unmunchify(invoiceParams)})

    @PDFView("PDF viewer", duration_guess=5)
    def viewInvoice(self, params, **kwargs):
        if checkInvoiceSetup(params):
            wordFile = self.renderInvoiceWordFile(params)
            with wordFile.open_binary() as f1:
                pdf_file = convert_word_to_pdf(f1)
            return PDFResult(file=pdf_file)
        else:
            raise UserError("Stel eerst de factuur op voordat je deze kunt bekijken")

    def loadInvoice(self, params) -> File:
        """
        Load invoice from storage
        """
        key = generateInvoiceName(params)
        if key not in Storage().list(scope="entity"):
            raise UserError(f"No invoice {key} found in storage")
        return Storage().get(key, scope="entity")

    def saveInvoice(self, params, **kwargs) -> None:
        """
        Save rendered invoice to storage
        """
        wordFile = self.renderInvoiceWordFile(params)
        key = generateInvoiceName(params)
        Storage().set(key, data=wordFile, scope="entity")

    def downloadInvoicePDF(self, params, **kwargs):
        word_file = self.renderInvoiceWordFile(params)
        fn = generateInvoiceName(params)
        with word_file.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)
        return DownloadResult(pdf_file, fn)

    def downLoadInvoiceWord(self, params, **kwargs):
        word_file = self.renderInvoiceWordFile(params)
        fn = generateInvoiceName(params)
        return DownloadResult(word_file, fn)

    ####################################################
    ################# Helper functions #################
    ####################################################

    @staticmethod
    def unpackDataIntoDataItems(data: dict) -> DataGroup:
        """
        Unpack data into DataItems
        """
        dataItems = []
        for key, value in data.items():
            if isinstance(value, dict):
                dataItems.append(
                    DataItem(
                        key,
                        "expand dict ->",
                        subgroup=Controller.unpackDataIntoDataItems(value),
                    )
                )
            elif isinstance(value, list):
                if not value:
                    dataItems.append(DataItem(key, "empty list"))
                    continue
                dataDict = {}
                for i, item in enumerate(value):
                    label = f"{key}: Item {i+1}"
                    dataDict[str(i)] = DataItem(label, item)
                dataGroup = DataGroup(**dataDict)
                dataItems.append(DataItem(key, "expand list ->", subgroup=dataGroup))
            elif (
                isinstance(value, str)
                or isinstance(value, int)
                or isinstance(value, float)
            ):
                dataItems.append(DataItem(key, value))
            else:
                raise UserError(f"Unknown data type {type(value)} in finance data")
        return DataGroup(*dataItems)

    def renderInvoiceWordFile(self, params, **kwargs) -> File:
        """
        Render invoice using template with most up to date input
        """
        template_dir = pyutils.get_root() / "app" / "lib" / "invoice_template.docx"
        with open(template_dir, "rb") as template:
            result = render_word_file(template, self.gatherInvoiceComponents(params))
        return result

    def gatherInvoiceComponents(self, params, **kwargs) -> list[WordFileTag]:
        """
        gather list of WordFileTag objects to be used in the render_word_file function
        Combine data from source excel file and user input. Idea is that user can choose which client
        to generate invoice for and which data to include in the invoice.
        """
        invoiceData = params.invoiceStep

        # client adress
        clientAddres = Munch(
            streetAndNumber="streetAndNumber", postalCode="postalCode", city="city"
        )

        # dates
        invoiceDate = invoiceData.invoiceDate
        invoiceDateOrdinal = invoiceDate.toordinal()
        expirationDate = convertOrdinalToDate(invoiceDateOrdinal + 30)

        # payment data
        currentPayments = []
        allPayments = getFinanceDataAttributeFromStorage(invoiceData.clientName)
        periods = getInvoicePeriods(params)
        periodNumber = periods.index(invoiceData.invoicePeriod)
        start, end = getPeriodOrdinals(periodNumber, invoiceData.invoiceYear)
        totalExcl = 0
        tax = 0
        total = 0
        for date, data in allPayments.items():
            if "/" in date:
                currentPayment = {}
                ordinal = convertDateToOrdinal(date)
                if start <= ordinal <= end:
                    # date
                    currentPayment["date"] = date

                    # exclusive price
                    priceExcl = data["priceExcl"]
                    currentPayment["price"] = f"{priceExcl:.2f}"

                    # quantity
                    quantity = data["quantity"]
                    currentPayment["quantity"] = f"{quantity:.0f}"

                    # subtotal
                    subtotal = quantity * priceExcl
                    currentPayment["total"] = f"{subtotal:.2f}"

                    # inclusive price
                    priceIncl = data["priceIncl"]

                    # taxrate
                    taxrate = (priceIncl - priceExcl) / priceExcl * 100
                    currentPayment["taxRate"] = f"{taxrate:.0f}"

                    # save current payment
                    currentPayments.append(currentPayment)

                    # cumalatives
                    totalExcl += subtotal
                    tax += priceIncl - priceExcl
                    total += priceIncl

        components = [
            WordFileTag("clientName", removeSpecialCharacters(invoiceData.clientName)),
            WordFileTag("invoiceDate", invoiceDate.strftime(r"%d/%m/%Y")),
            WordFileTag("invoicePeriod", str(invoiceData.invoicePeriod)),
            WordFileTag("expirationDate", expirationDate),
            WordFileTag("invoiceNumber", invoiceData.invoiceNumber),
            WordFileTag("clientLegalContact", str()),
            WordFileTag("clientAddress", clientAddres),
            WordFileTag("clientEmail", str()),
            WordFileTag("payments", currentPayments),
            WordFileTag("totalExcl", f"{totalExcl:.2f}"),
            WordFileTag("tax", f"{tax:.2f}"),
            WordFileTag("total", f"{total:.2f}"),
        ]

        return components

    def getStorageKey(self, params) -> str:
        """
        Get storage key for invoice
        """
        return f"{params.invoiceStep.clientName}-{params.invoiceStep.invoiceNumber}"

    def getFinanceDataExcel(self, params, **kwargs) -> SpreadsheetResult:
        """
        Load finance data from uploaded excel file. Optionally pass any inputs from user
        (Not implemented yet)
        """
        inputs = [SpreadsheetCalculationInput("clientName", "")]
        financeFile = Controller.obtainFileFromResource(params.uploadStep.financeSheet)
        financeSheet = SpreadsheetCalculation(financeFile, inputs)
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
                valueArray[~empty] = convertExcelFloat(floats).tolist()
                financeData[itemKey] = valueArray
            elif itemKey == "invoiceDates":  # data is a list of dates
                values = valueArray.tolist()
                financeData[itemKey] = []
                for value in values:
                    if value != "NA":
                        financeData[itemKey] += [
                            convertOrdinalToDate(convertExcelOrdinal(int(value)))
                        ]
                    else:
                        financeData[itemKey] += [value]

            else:  # unknown key
                raise UserError(f"Unknown key {itemKey} in finance data sheet")
        return Controller.sortFinanceData(financeData)

    @staticmethod
    def obtainFileFromResource(fileResource: FileResource) -> File:
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
    def sortFinanceData(financeData: dict) -> dict:
        """
        sort by clients first then by date. This is also the structure of database
        """
        sortedFinanceData = {}
        print(financeData["availableClients"])
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
        sortedFinanceData["clientLegalContact"] = clientLegalContact[
            clientLegalContact != "NA"
        ].tolist()
        clientStreetAndNumber = np.array(financeData["clientStreetAndNumber"])
        sortedFinanceData["clientStreetAndNumber"] = clientStreetAndNumber[
            clientStreetAndNumber != "NA"
        ].tolist()
        clientPostalCode = np.array(financeData["clientPostalCode"])
        sortedFinanceData["clientPostalCode"] = clientPostalCode[
            clientPostalCode != "NA"
        ].tolist()
        clientCity = np.array(financeData["clientCity"])
        sortedFinanceData["clientCity"] = clientCity[clientCity != "NA"].tolist()
        clientEmail = np.array(financeData["clientEmail"])
        sortedFinanceData["clientEmail"] = clientEmail[clientEmail != "NA"].tolist()

        return sortedFinanceData
