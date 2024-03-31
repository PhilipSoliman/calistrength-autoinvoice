from viktor.parametrization import (
    DateField,
    FileField,
    LineBreak,
    OptionField,
    Step,
    Text,
    TextField,
    ViktorParametrization,
)

from app.auto_invoice.definitions import INVOICE_PERIODS, INVOICE_YEARS


class Parametrization(ViktorParametrization):
    # TODO: add DataView for current finance data
    uploadStep = Step("Upload finance xlsx", views=[])
    uploadStep.intro = Text(
        "# CALISTRENGTH: auto invoice app 💰 \n Upload hieronder de meest recente versie van de finance excel"
    )
    uploadStep.file = FileField("Finance (xlsx)", file_types=[".xlsx"], max_size=5_000_000)

    invoiceStep = Step("Invoice settings", views=["viewInvoice"])
    invoiceStep.intro = Text(
        "Vul hieronder de gegevens in voor de factuur. De factuur wordt automatisch gegenereerd en kan vervolgens worden opgeslagen of bekeken."
    )
    invoiceStep.client_name = TextField("Klantnaam")
    invoiceStep.invoiceDate = DateField("Factuurdatum")
    invoiceStep.expirationDate = DateField("Vervaldatum")
    invoiceStep.invoiceNumber = TextField("Factuurnummer")
    invoiceStep.invoicePeriod = OptionField("Invoice period", INVOICE_PERIODS)
    invoiceStep.invoiceYear = OptionField("Invoice year", INVOICE_YEARS, default="2024")
