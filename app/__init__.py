from .auto_invoice_manager.controller import Controller as autoInvoiceManager
from .auto_invoice.controller import Controller as autoInvoice

from viktor import InitialEntity

initial_entities = [
    InitialEntity(
        "autoInvoiceManager",
        name="Auto invoice manager",
        children=[
            InitialEntity("autoInvoice", name="Auto invoice"),
        ],
    ),
]
