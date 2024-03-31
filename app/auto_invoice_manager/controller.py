from viktor import ViktorController


class Controller(ViktorController):
    label = "autoInvoiceManager"
    children = ["autoInvoice"]
    show_children_as = "Table"
