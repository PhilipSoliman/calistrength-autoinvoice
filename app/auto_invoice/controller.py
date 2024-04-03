from pprint import pprint

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
from viktor.views import PDFResult, PDFView

from app.auto_invoice.definitions import (
    convertExcelDate,
    convertExcelFloat,
    getFinanceDataFromStorage,
    saveFinanceDataToStorage,
)
from app.auto_invoice.parametrization import Parametrization
from app.helper import pyutils


class Controller(ViktorController):
    label = "autoInvoice"
    parametrization = Parametrization

    @PDFView("PDF viewer", duration_guess=5)
    def viewInvoice(self, params, **kwargs):
        wordFile = self.renderInvoice(params)
        with wordFile.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)
        return PDFResult(file=pdf_file)

    def loadInvoice(self, params) -> File:
        """
        Load invoice from storage
        """
        storageKey = self.getStorageKey(params)
        if storageKey not in Storage().list(scope="entity"):
            raise UserError(f"No invoice {storageKey} found in storage")
        return Storage().get(storageKey, scope="entity")

    def saveInvoice(self, params, **kwargs) -> None:
        """
        Save rendered invoice to storage
        """
        storageKey = self.getStorageKey(params)
        wordFile = self.renderInvoice(params)
        Storage().set(storageKey, data=wordFile, scope="entity")

    def downloadInvoice(self, params, **kwargs):
        word_file = self.renderInvoice(params)
        fn = f"invoice-{self.getStorageKey(params)}.pdf"
        with word_file.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)
        return DownloadResult(pdf_file, fn)

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

        # update finance data (only for possibly novel clients in current finance data)
        newFinanceData = dict(oldFinanceData)
        for client in financeData["availableClients"]:
            if client not in newFinanceData:
                newFinanceData[client] = financeData[client]
            else:
                newFinanceData[client].update(financeData[client])
        newFinanceData["availableClients"] = financeData["availableClients"]

        # save new finance data
        saveFinanceDataToStorage(newFinanceData)

    ####################################################
    ################# Helper functions #################
    ####################################################

    def renderInvoice(self, params, **kwargs) -> File:
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
        # TODO: construct list of rows containing payment data (custumer name, amount, date, tax rate etc.)
        components = [
            WordFileTag("invoiceDate", str(params.invoiceStep.invoiceDate)),
            WordFileTag("expirationDate", str(params.invoiceStep.expirationDate)),
            WordFileTag("invoiceNumber", params.invoiceStep.invoiceNumber),
            WordFileTag("invoicePeriod", params.invoiceStep.invoicePeriod),
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
        inputs = [
            SpreadsheetCalculationInput("clientName", params.invoiceStep.clientName)
        ]
        financeFile = Controller.obtainFileFromResource(params.uploadStep.financeSheet)
        financeSheet = SpreadsheetCalculation(financeFile, inputs)
        financeData = financeSheet.evaluate(include_filled_file=False).values
        for itemKey, dataString in financeData.items():
            if isinstance(dataString, str):
                values = dataString.split(";")
            else:
                raise UserError("Data values in finance sheet should be strings")
            if itemKey in ["clients", "availableClients"]:
                financeData[itemKey] = values[1:]
            elif itemKey in ["pricesIncl", "pricesExcl"]:
                financeData[itemKey] = [
                    convertExcelFloat(value) for value in values[1:]
                ]
            elif itemKey == "invoiceDates":
                financeData[itemKey] = [
                    convertExcelDate(int(value)) for value in values[1:]
                ]
            else:
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
        for client in financeData["availableClients"]:
            sortedFinanceData[client] = {}

        for i, client in enumerate(financeData["clients"]):
            if client not in financeData["availableClients"]:
                continue
            date = financeData["invoiceDates"][i]
            sortedFinanceData[client][date] = {
                "priceIncl": financeData["pricesIncl"][i],
                "priceExcl": financeData["pricesExcl"][i],
            }
        sortedFinanceData["availableClients"] = financeData["availableClients"]
        return sortedFinanceData
