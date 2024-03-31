from pathlib import Path

from viktor import ViktorController
from viktor.core import File, Storage
from viktor.external.word import WordFileTag, render_word_file
from viktor.utils import convert_word_to_pdf
from viktor.views import PDFResult, PDFView

from ..helper import pyutils
from .parametrization import Parametrization


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
            WordFileTag("invoice_date", params.invoiceDate),
            WordFileTag("expiration_date", params.expirationDate),
            WordFileTag("invoice_number", params.invoiceNumber),
            WordFileTag("invoice_period", params.invoicePeriod),
        ]

        return components

    def renderInvoice(self, params, **kwargs) -> File:
        """
        Render invoice using template with most up to date input
        """
        components = self.gatherInvoiceComponents(params)
        template_dir = pyutils.get_root() / "app" / "lib" / "invoice_template.docx"
        with open(template_dir, "w") as template:
            result = render_word_file(template, components)

        return result

    @PDFView("PDF viewer", duration_guess=5)
    def pdf_view(self, params, **kwargs):
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

    def loadInvoice(self, params, **kwargs) -> File:
        """
        Load invoice from storage
        """
        storage = Storage()
        word_file = storage.get(self.getStorageKey(params), scope="workspace")
        return word_file

    def getStorageKey(self, params, **kwargs) -> str:
        """
        Generate storage key for the invoice
        """
        return params.client_name + "_" + params.invoice_number
