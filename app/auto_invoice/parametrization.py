from viktor.parametrization import (
    ActionButton,
    DateField,
    DownloadButton,
    FileField,
    HiddenField,
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
    CURRENT_YEAR,
    INVOICE_YEARS,
    getAvailableClients,
    getavailableInvoiceNumbers,
    getInvoicePeriods,
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
    # invoiceStep.invoiceDate = OptionField(
    #     "Factuurdatum",
    #     options=getAvailableDates,
    #     visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurdatum"),
    # )
    invoiceStep.invoiceNumber = OptionField(
        "Factuurnummer",
        options=getavailableInvoiceNumbers,
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurnummer"),
    )
    invoiceStep.invoiceYear = OptionField(
        "Invoice year",
        INVOICE_YEARS,
        default=CURRENT_YEAR,
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurperiode"),
    )
    invoiceStep.invoicePeriod = OptionField(
        "Invoice period",
        options=getInvoicePeriods,
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurperiode"),
    )
    invoiceStep.invoiceIndex = OptionField(
        "Invoice index",
        options=[],
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurperiode"),
    )
    invoiceStep.setupInvoiceButton = SetParamsButton(
        "Factuur Opstellen", method="setupInvoice"
    )
    # TODO: add dynamic array field for invoice items
    invoiceStep.expirationDate = OptionField("Vervaldatum", options=[], visible=False)
    invoiceStep.lb2 = LineBreak()
    invoiceStep.subheader1 = Text(r"## Opslaan \& downloaden" + "\n")
    invoiceStep.saveInvoice = ActionButton("Factuur opslaan", method="saveInvoice")
    invoiceStep.downloadInvoice = DownloadButton(
        "Factuur downloaden", method="downloadInvoice"
    )
