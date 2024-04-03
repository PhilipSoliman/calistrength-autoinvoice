from viktor.parametrization import (
    ActionButton,
    DateField,
    DownloadButton,
    FileField,
    HiddenField,
    IsEqual,
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
    getAvailableDates,
    getInvoicePeriods,
)


class Parametrization(ViktorParametrization):
    uploadStep = Step("Upload finance xlsx", views=[])
    uploadStep.intro = Text(
        "# CALISTRENGTH: auto invoice app 💰 \n Upload hieronder de meest recente versie van de finance excel"
    )
    uploadStep.financeSheet = FileField(
        "Finance (xlsx)", file_types=[".xlsx"], max_size=5_000_000
    )
    uploadStep.updateFinanceDataButton = ActionButton(
        "Update finance data", method="updateFinanceData"
    )
    # TODO: add DataView for current finance data

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
        ["Factuurdatum", "Factuurperiode", "Factuurnummer"],
        default="Factuurdatum",
        variant="radio-inline",
    )
    invoiceStep.lb1 = LineBreak()
    invoiceStep.invoiceDate = OptionField(
        "Factuurdatum",
        options=getAvailableDates,
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurdatum"),
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
    invoiceStep.invoiceNumber = OptionField(
        "Factuurnummer",
        options=[],  # getAvailableInvoiceNumbers
        visible=IsEqual(Lookup("invoiceStep.searchMethod"), "Factuurnummer"),
    )
    invoiceStep.setupInvoiceButton = SetParamsButton(
        "Factuur Opstellen", method="setupInvoice"
    )
    invoiceStep.expirationDate = OptionField("Vervaldatum", options=[], visible=False)
    # invoiceStep.invoiceFound = HiddenField("invoice found", name="invoiceFound")
    invoiceStep.lb2 = LineBreak()
    # invoiceStep.generateInvoiceButton = SetParamsButton(
    #     "Genereer factuur",
    #     method="generateInvoice",
    #     visible=Lookup("invoiceStep.invoiceFound"),
    # )
    # invoiceStep.cachedInvoice = HiddenField("cached invoice", name="cachedInvoice")
    invoiceStep.subheader1 = Text(r"## Opslaan \& downloaden" + "\n")
    invoiceStep.saveInvoice = ActionButton("Factuur opslaan", method="saveInvoice")
    invoiceStep.downloadInvoice = DownloadButton(
        "Factuur downloaden", method="downloadInvoice"
    )
