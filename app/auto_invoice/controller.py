from munch import Munch, unmunchify
from viktor import ViktorController
from viktor.core import File, UserMessage
from viktor.errors import UserError
from viktor.external.word import WordFileTag, render_word_file
from viktor.result import DownloadResult, SetParamsResult
from viktor.utils import convert_word_to_pdf
from viktor.views import DataGroup, DataItem, DataResult, DataView, PDFResult, PDFView

from app.auto_invoice.definitions import (
    checkInvoiceSetup,
    convertDateToOrdinal,
    generateInvoiceName,
    getInvoiceNumberFromPeriodAndIndex,
    getInvoicePeriodFromNumber,
    getInvoicePeriods,
    getPeriodOrdinals,
)
from app.auto_invoice.excel_reader import ExcelReader
from app.auto_invoice.parametrization import Parametrization
from app.helper import pyutils


class Controller(ViktorController):
    label = "autoInvoice"
    parametrization = Parametrization

    @DataView("Finance data", duration_guess=5)
    def viewFinanceData(self, params, **kwargs) -> DataResult:
        """
        View finance data
        """
        financeData = ExcelReader.readFinanceSheet(params.uploadStep.financeSheet)
        return DataResult(Controller.unpackDataIntoDataItems(financeData))

    def setupInvoice(self, params, **kwargs) -> SetParamsResult:
        """
        Search for invoice in finance data. The goal of this function
        is to make sure that invoice number, date & period (+year) are set.
        such that downstream functions can find all the relevant assignments
        and payment data.
        """
        invoiceParams = params.invoiceStep
        if invoiceParams.searchMethod == "Factuurperiode":
            clientName = params.invoiceStep.clientName
            period = params.invoiceStep.invoicePeriod
            year = params.invoiceStep.invoiceYear
            index = params.invoiceStep.invoiceIndex
            invoiceParams.invoiceNumber = getInvoiceNumberFromPeriodAndIndex(
                params, clientName, index, period, year
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

    def downloadInvoicePDF(self, params, **kwargs):
        word_file = self.renderInvoiceWordFile(params)
        fn = generateInvoiceName(params, fn_ext="pdf")
        with word_file.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)
        return DownloadResult(pdf_file, fn)

    def downLoadInvoiceWord(self, params, **kwargs):
        word_file = self.renderInvoiceWordFile(params)
        fn = generateInvoiceName(params, fn_ext="docx")
        return DownloadResult(word_file, fn)

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
        template_path = pyutils.get_root() / "lib" / "invoice_template.docx"
        with open(template_path, "rb") as template:
            result = render_word_file(template, self.gatherInvoiceComponents(params))
        return result

    def gatherInvoiceComponents(self, params, **kwargs) -> list[WordFileTag]:
        """
        gather list of WordFileTag objects to be used in the render_word_file function
        Combine data from source excel file and user input. Idea is that user can choose which client
        to generate invoice for and which data to include in the invoice.
        """
        invoiceData = params.invoiceStep

        # client details
        financeData = ExcelReader.readFinanceSheet(params.uploadStep.financeSheet)
        clientData = Munch(financeData[invoiceData.clientName])
        clientAddres = Munch(
            streetAndNumber=clientData.streetAndNumber,
            postalCode=clientData.postalCode,
            city=clientData.city,
        )
        legalContact = clientData.legalContact
        email = clientData.email

        # dates
        invoiceDate = invoiceData.invoiceDate
        invoiceDateOrdinal = invoiceDate.toordinal()
        expirationDate = ExcelReader._convertOrdinalToDate(invoiceDateOrdinal + 30)

        # payment data
        currentPayments = []
        periods = getInvoicePeriods(params)
        periodNumber = periods.index(invoiceData.invoicePeriod)
        start, end = getPeriodOrdinals(periodNumber, invoiceData.invoiceYear)
        totalExcl = 0
        tax = 0
        total = 0
        for date, data in clientData.items():
            if "/" in date:
                currentPayment = {}
                ordinal = convertDateToOrdinal(date)
                if start <= ordinal <= end:
                    # extract payment data
                    quantity = float(data["quantity"])
                    priceExcl = float(data["priceExcl"]) / quantity
                    subtotal = quantity * priceExcl
                    if subtotal == 0:
                        continue
                    priceIncl = float(data["priceIncl"])
                    taxrate = (priceIncl - subtotal) / subtotal * 100
                    description = data["description"]

                    # save current payment
                    currentPayment["date"] = date
                    currentPayment["quantity"] = f"{quantity:.1f}"
                    currentPayment["price"] = f"{priceExcl:.2f}"
                    currentPayment["total"] = f"{subtotal:.2f}"
                    currentPayment["taxRate"] = f"{taxrate:.0f}"
                    currentPayment["description"] = description
                    currentPayments.append(currentPayment)

                    # cumalatives
                    totalExcl += subtotal
                    tax += priceIncl - subtotal
                    total += priceIncl

        components = [
            WordFileTag(
                "clientName", rf"{invoiceData.clientName}"
            ),  # removeSpecialCharacters(invoiceData.clientName)),
            WordFileTag("invoiceDate", invoiceDate.strftime(r"%d/%m/%Y")),
            WordFileTag("invoicePeriod", str(invoiceData.invoicePeriod)),
            WordFileTag("expirationDate", expirationDate),
            WordFileTag("invoiceNumber", invoiceData.invoiceNumber),
            WordFileTag("clientLegalContact", rf"{legalContact}"),
            WordFileTag("clientAddress", clientAddres),
            WordFileTag("clientEmail", rf"{email}"),
            WordFileTag("payments", currentPayments),
            WordFileTag("totalExcl", f"{totalExcl:.2f}"),
            WordFileTag("tax", f"{tax:.2f}"),
            WordFileTag("total", f"{total:.2f}"),
        ]

        return components
