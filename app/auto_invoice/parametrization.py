from viktor.parametrization import (
    ActionButton,
    DateField,
    DownloadButton,
    FileField,
    IsEqual,
    IsNotEqual,
    LineBreak,
    Lookup,
    OptionField,
    SetParamsButton,
    Step,
    Text,
    ViktorParametrization,
)

from app.auto_invoice.definitions import (
    getAvailableClients,
    getavailableInvoiceNumbers,
    getInvoiceIndices,
    getInvoicePeriods,
    getInvoiceYears,
)


class Parametrization(ViktorParametrization):
    uploadStep = Step("Upload finance xlsx", views=["viewFinanceData"])
    uploadStep.intro = Text(
        "# CALISTRENGTH: auto invoice app 💰 \n Upload hieronder de meest recente versie van de finance excel"
    )
    uploadStep.financeSheet = FileField(
        "Finance (xlsx)", file_types=[".xlsx"], max_size=5_000_000
    )
    uploadStep.updateFinanceDataButton = ActionButton(
        "Update finance data", method="updateFinanceData"
    )

    invoiceStep = Step("Genereer factuur", views=["viewInvoice"])
    invoiceStep.intro = Text(
        "# Factuur gegevens\nVul hieronder de gegevens in voor de factuur. De factuur wordt automatisch gegenereerd en kan vervolgens worden opgeslagen of bekeken."
    )
    invoiceStep.lb0 = LineBreak()
    invoiceStep.subheader0 = Text(
        "## Zoek naar factuur\nKies eerst de klant en zoekmethode\n"
    )
    invoiceStep.clientName = OptionField("Klantnaam", options=getAvailableClients)
    invoiceStep.searchMethod = OptionField(
        "Hoe wilt u zoeken?",
        ["Factuurnummer", "Factuurperiode"],
        default="Factuurnummer",
        variant="radio-inline",
        visible=IsNotEqual(Lookup("invoiceStep.clientName"), None),
    )
    invoiceStep.lb1 = LineBreak()
    invoiceStep.invoiceNumber = OptionField(
        "Factuurnummer",
        options=getavailableInvoiceNumbers,
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurnummer"),
    )
    invoiceStep.invoiceYear = OptionField(
        "Invoice year",
        options=getInvoiceYears,
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurperiode"),
    )
    invoiceStep.invoicePeriod = OptionField(
        "Invoice period",
        options=getInvoicePeriods,
        visible=IsNotEqual(Lookup("invoiceStep.invoiceYear"), None)
        and IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurperiode"),
    )
    invoiceStep.invoiceIndex = OptionField(
        "Invoice index",
        options=getInvoiceIndices,
        visible=IsNotEqual(Lookup("invoiceStep.invoicePeriod"), None)
        and IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurperiode"),
    )
    invoiceStep.lb2 = LineBreak()
    invoiceStep.invoiceDate = DateField("Geef factuurdatum op")
    # TODO: add dynamic array field for invoice items
    invoiceStep.lb3 = LineBreak()
    invoiceStep.setupInvoiceText = Text(
        "Wanneer de factuurgegevens hierboven zijn ingevuld, klik dan op de onderstaande knop om de factuur op te stellen."
        + "\n Hierna kan de factuur gegenereerd worden door in het rechter scherm op 'Update' te klikken."
        "\n Zodra gegevens worden aangepast, moet de factuur opnieuw worden opgesteld."
    )
    invoiceStep.setupInvoiceButton = SetParamsButton(
        "Factuur opstellen", method="setupInvoice"
    )
    invoiceStep.subheader1 = Text(r"## Opslaan \& downloaden" + "\n")
    invoiceStep.saveInvoice = ActionButton(
        "Factuur opslaan (database)", method="saveInvoice"
    )
    invoiceStep.downloadInvoicePDF = DownloadButton(
        "Factuur downloaden (pdf)", method="downloadInvoicePDF"
    )
    invoiceStep.downLoadInvoiceWord = DownloadButton(
        "Factuur downloaden (docx)", method="downLoadInvoiceWord"
    )
