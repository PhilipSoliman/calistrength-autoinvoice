from pathlib import Path
from pprint import pprint

from viktor import ViktorController
from viktor.core import File, Storage
from viktor.errors import UserError
from viktor.external.spreadsheet import (
    SpreadsheetCalculation,
    SpreadsheetCalculationInput,
    SpreadsheetResult,
)
from viktor.external.word import WordFileTag, render_word_file
from viktor.result import SetParamsResult
from viktor.utils import convert_word_to_pdf
from viktor.views import PDFResult, PDFView

from app.auto_invoice.definitions import convertExcelDate, convertExcelFloat
from app.auto_invoice.parametrization import Parametrization
from app.helper import pyutils


class Controller(ViktorController):
    label = "autoInvoice"
    parametrization = Parametrization

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

    def renderInvoice(self, params, **kwargs) -> File:
        """
        Render invoice using template with most up to date input
        """
        template_dir = pyutils.get_root() / "app" / "lib" / "invoice_template.docx"
        with open(template_dir, "rb") as template:
            result = render_word_file(template, self.gatherInvoiceComponents(params))

        return result

    @PDFView("PDF viewer", duration_guess=5)
    def viewInvoice(self, params, **kwargs):
        word_file = self.renderInvoice(params)

        with word_file.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)

        return PDFResult(file=pdf_file)

    def saveInvoice(self, params, **kwargs) -> None:
        """
        Save rendered invoice to storage
        """
        word_file = self.renderInvoice(params)
        storage = Storage()
        storage.set(self.getStorageKey(params), data=word_file, scope="workspace")

    @staticmethod
    def loadInvoice(invoiceNumber: str) -> File:
        """
        Load invoice from storage
        """
        storage = Storage()
        word_file = storage.get(invoiceNumber, scope="workspace")
        return word_file

    def getFinanceData(self, params, **kwargs) -> SpreadsheetResult:
        """
        Load finance data from uploaded excel file, also pass any inputs from user
        """
        # TODO: move finance data from params to storage to prevent slow app in the future
        # example of inputs
        inputs = [
            SpreadsheetCalculationInput("clientName", params.invoiceStep.clientName)
        ]
        financeSheet = SpreadsheetCalculation(
            params.uploadStep.financeSheet.file, inputs
        )
        financeData = financeSheet.evaluate(include_filled_file=False).values
        for itemKey, dataString in financeData.items():
            # get values from string
            if isinstance(dataString, str):
                values = dataString.split(";")
            else:
                UserError("Data in finance sheet should be string")

            # assign values to financeData dict and do some type conversion
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
                UserError(f"Unknown key {itemKey} in finance data sheet")

        pprint(params)
        return SetParamsResult({"uploadStep": {"financeData": financeData}})
