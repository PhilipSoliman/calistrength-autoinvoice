from viktor.parametrization import (
    ActionButton,
    DateField,
    DownloadButton,
    FileField,
    HiddenField,
    LineBreak,
    OptionField,
    SetParamsButton,
    Step,
    Text,
    TextField,
    ViktorParametrization,
)

from app.auto_invoice.definitions import (
    INVOICE_PERIODS,
    INVOICE_YEARS,
    getAvailableClients,
    getAvailableDates,
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
    invoiceStep.subheader0 = Text("## Zoek naar factuur")
    invoiceStep.clientName = OptionField("Klantnaam", options=getAvailableClients)
    invoiceStep.invoiceDate = OptionField("Factuurdatum", options=getAvailableDates)
    invoiceStep.invoiceNumber = TextField("Factuurnummer")
    invoiceStep.invoicePeriod = OptionField("Invoice period", INVOICE_PERIODS)
    invoiceStep.expirationDate = DateField("Vervaldatum")
    invoiceStep.invoiceYear = OptionField("Invoice year", INVOICE_YEARS, default="2024")
    invoiceStep.lb1 = LineBreak()
    invoiceStep.subheader0 = Text(r"## Opslaan \& downloaden")
    invoiceStep.saveInvoice = ActionButton("Factuur opslaan", method="saveInvoice")
    invoiceStep.downloadInvoice = DownloadButton(
        "Factuur downloaden", method="downloadInvoice"
    )
