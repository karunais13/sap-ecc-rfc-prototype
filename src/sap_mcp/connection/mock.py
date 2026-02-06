"""Mock SAP connection for development without a real SAP system."""

from __future__ import annotations

from datetime import datetime


def _success_return(message: str = "Success") -> dict:
    return {"TYPE": "S", "ID": "MOCK", "NUMBER": "000", "MESSAGE": message}


def _error_return(message: str) -> dict:
    return {"TYPE": "E", "ID": "MOCK", "NUMBER": "001", "MESSAGE": message}


_MOCK_MATERIALS = {
    "000000000000000100": {
        "MATERIAL": "000000000000000100",
        "MATL_DESC": "Steel Rod 10mm",
        "MATL_TYPE": "ROH",
        "MATL_GROUP": "001",
        "BASE_UOM": "KG",
        "NET_WEIGHT": "1.500",
        "GROSS_WEIGHT": "1.600",
        "UNIT_OF_WT": "KG",
    },
    "000000000000000200": {
        "MATERIAL": "000000000000000200",
        "MATL_DESC": "Copper Wire 2mm",
        "MATL_TYPE": "ROH",
        "MATL_GROUP": "002",
        "BASE_UOM": "M",
        "NET_WEIGHT": "0.050",
        "GROSS_WEIGHT": "0.055",
        "UNIT_OF_WT": "KG",
    },
    "000000000000001000": {
        "MATERIAL": "000000000000001000",
        "MATL_DESC": "Electric Motor 5kW",
        "MATL_TYPE": "FERT",
        "MATL_GROUP": "010",
        "BASE_UOM": "EA",
        "NET_WEIGHT": "25.000",
        "GROSS_WEIGHT": "27.000",
        "UNIT_OF_WT": "KG",
    },
}

_MOCK_CUSTOMERS = {
    "0000001000": {
        "CUSTOMER": "0000001000",
        "NAME": "Acme Corporation",
        "STREET": "123 Industrial Way",
        "CITY": "Munich",
        "POSTL_CODE": "80331",
        "COUNTRY": "DE",
        "REGION": "BY",
        "PHONE": "+49 89 1234567",
        "EMAIL": "orders@acme.de",
    },
    "0000002000": {
        "CUSTOMER": "0000002000",
        "NAME": "TechParts GmbH",
        "STREET": "Berliner Str. 42",
        "CITY": "Berlin",
        "POSTL_CODE": "10115",
        "COUNTRY": "DE",
        "REGION": "BE",
        "PHONE": "+49 30 9876543",
        "EMAIL": "info@techparts.de",
    },
}

_MOCK_VENDORS = {
    "0000003000": {
        "VENDOR": "0000003000",
        "NAME": "Steel Supplies AG",
        "STREET": "Stahlweg 7",
        "CITY": "Essen",
        "POSTL_CODE": "45127",
        "COUNTRY": "DE",
        "PHONE": "+49 201 5551234",
    },
    "0000004000": {
        "VENDOR": "0000004000",
        "NAME": "Global Components Ltd",
        "STREET": "15 Commerce Road",
        "CITY": "London",
        "POSTL_CODE": "EC1A 1BB",
        "COUNTRY": "GB",
        "PHONE": "+44 20 7946 0958",
    },
}

_MOCK_SALES_ORDERS = [
    {
        "SD_DOC": "0000010001",
        "DOC_TYPE": "TA",
        "SOLD_TO": "0000001000",
        "PURCH_NO": "PO-ACME-001",
        "DOC_DATE": "20250101",
        "NET_VALUE": "15000.00",
        "CURRENCY": "EUR",
        "ITEMS": [
            {
                "ITM_NUMBER": "000010",
                "MATERIAL": "000000000000001000",
                "SHORT_TEXT": "Electric Motor 5kW",
                "REQ_QTY": "10.000",
                "SALES_UNIT": "EA",
                "NET_PRICE": "1500.00",
                "CURRENCY": "EUR",
            },
        ],
    },
    {
        "SD_DOC": "0000010002",
        "DOC_TYPE": "TA",
        "SOLD_TO": "0000002000",
        "PURCH_NO": "PO-TP-042",
        "DOC_DATE": "20250115",
        "NET_VALUE": "750.00",
        "CURRENCY": "EUR",
        "ITEMS": [
            {
                "ITM_NUMBER": "000010",
                "MATERIAL": "000000000000000100",
                "SHORT_TEXT": "Steel Rod 10mm",
                "REQ_QTY": "500.000",
                "SALES_UNIT": "KG",
                "NET_PRICE": "1.50",
                "CURRENCY": "EUR",
            },
        ],
    },
]

_MOCK_PURCHASE_ORDERS = [
    {
        "PO_NUMBER": "4500000001",
        "DOC_TYPE": "NB",
        "VENDOR": "0000003000",
        "DOC_DATE": "20250110",
        "CURRENCY": "EUR",
        "ITEMS": [
            {
                "PO_ITEM": "00010",
                "MATERIAL": "000000000000000100",
                "SHORT_TEXT": "Steel Rod 10mm",
                "QUANTITY": "1000.000",
                "UNIT": "KG",
                "NET_PRICE": "1.20",
                "CURRENCY": "EUR",
            },
        ],
    },
]

_MOCK_INVOICES = [
    {
        "INVOICE": "9000000001",
        "DOC_TYPE": "RN",
        "REF_DOC": "0000010001",
        "COMP_CODE": "1000",
        "DOC_DATE": "20250115",
        "POST_DATE": "20250115",
        "NET_VALUE": "15000.00",
        "TAX_AMOUNT": "2850.00",
        "CURRENCY": "EUR",
    },
]

_MOCK_TABLES = {
    "MARA": {
        "fields": ["MATNR", "MTART", "MATKL", "MEINS", "BRGEW", "NTGEW", "GEWEI"],
        "rows": [
            ["000000000000000100", "ROH", "001", "KG", "1.600", "1.500", "KG"],
            ["000000000000000200", "ROH", "002", "M", "0.055", "0.050", "KG"],
            ["000000000000001000", "FERT", "010", "EA", "27.000", "25.000", "KG"],
        ],
    },
    "MAKT": {
        "fields": ["MATNR", "SPRAS", "MAKTX"],
        "rows": [
            ["000000000000000100", "E", "Steel Rod 10mm"],
            ["000000000000000200", "E", "Copper Wire 2mm"],
            ["000000000000001000", "E", "Electric Motor 5kW"],
        ],
    },
    "KNA1": {
        "fields": ["KUNNR", "NAME1", "ORT01", "PSTLZ", "LAND1"],
        "rows": [
            ["0000001000", "Acme Corporation", "Munich", "80331", "DE"],
            ["0000002000", "TechParts GmbH", "Berlin", "10115", "DE"],
        ],
    },
    "LFA1": {
        "fields": ["LIFNR", "NAME1", "ORT01", "PSTLZ", "LAND1"],
        "rows": [
            ["0000003000", "Steel Supplies AG", "Essen", "45127", "DE"],
            ["0000004000", "Global Components Ltd", "London", "EC1A 1BB", "GB"],
        ],
    },
    "VBAK": {
        "fields": ["VBELN", "AUART", "KUNNR", "BSTNK", "AUDAT", "NETWR", "WAERK"],
        "rows": [
            ["0000010001", "TA", "0000001000", "PO-ACME-001", "20250101", "15000.00", "EUR"],
            ["0000010002", "TA", "0000002000", "PO-TP-042", "20250115", "750.00", "EUR"],
        ],
    },
    "EKKO": {
        "fields": ["EBELN", "BSART", "LIFNR", "BEDAT", "WAERS"],
        "rows": [
            ["4500000001", "NB", "0000003000", "20250110", "EUR"],
        ],
    },
    "MARD": {
        "fields": ["MATNR", "WERKS", "LGORT", "LABST"],
        "rows": [
            ["000000000000000100", "1000", "0001", "50.000"],
            ["000000000000000200", "1000", "0001", "5000.000"],
            ["000000000000001000", "1000", "0001", "3.000"],
        ],
    },
}

_NEXT_SO_NUMBER = 10003
_NEXT_PO_NUMBER = 4500000002


class MockConnection:
    """Mock SAP RFC connection for development without a real SAP system."""

    def __init__(self, **params: str) -> None:
        self._params = params
        self._alive = True

    @property
    def alive(self) -> bool:
        return self._alive

    def close(self) -> None:
        self._alive = False

    def call(self, func_name: str, **params: object) -> dict:
        if not self._alive:
            raise RuntimeError("Connection is closed")

        handler = _FUNCTION_HANDLERS.get(func_name)
        if handler:
            return handler(**params)

        return {"RETURN": _success_return(f"Mock call to {func_name}")}

    def get_function_description(self, func_name: str) -> MockFuncDesc:
        return MockFuncDesc(func_name)


class MockFuncDesc:
    """Mock function description mimicking pyrfc FunctionDescription."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.parameters = _MOCK_FUNC_PARAMS.get(name, [
            {"name": "RETURN", "parameter_type": "RFCTYPE_TABLE",
             "direction": "RFC_EXPORT", "nuc_length": 0, "uc_length": 0,
             "decimals": 0, "default_value": "", "optional": True,
             "parameter_text": "Return messages", "type_description": None},
        ])


def _handle_material_get_detail(**params: object) -> dict:
    matnr = str(params.get("MATERIAL", ""))
    mat = _MOCK_MATERIALS.get(matnr)
    if mat:
        return {
            "MATERIAL_GENERAL_DATA": mat,
            "RETURN": _success_return("Material read successfully"),
        }
    return {
        "MATERIAL_GENERAL_DATA": {},
        "RETURN": _error_return(f"Material {matnr} not found"),
    }


def _handle_material_getlist(**params: object) -> dict:
    desc = str(params.get("MATNR_RA", [{}])[0].get("LOW", "")) if params.get("MATNR_RA") else ""
    desc_sel = params.get("MATERIAL_DESCRIPTION", "")
    results = []
    for mat in _MOCK_MATERIALS.values():
        if desc and desc.upper() not in mat["MATL_DESC"].upper():
            continue
        results.append({"MATERIAL": mat["MATERIAL"], "MATL_DESC": mat["MATL_DESC"]})
    return {"MATNRLIST": results, "RETURN": _success_return()}


def _handle_customer_getdetail2(**params: object) -> dict:
    custno = str(params.get("CUSTOMERNO", ""))
    cust = _MOCK_CUSTOMERS.get(custno)
    if cust:
        return {
            "CUSTOMERGENERALDETAIL": {
                "CUSTOMER": cust["CUSTOMER"],
                "NAME": cust["NAME"],
                "STREET": cust["STREET"],
                "CITY": cust["CITY"],
                "POSTL_CODE": cust["POSTL_CODE"],
                "COUNTRY": cust["COUNTRY"],
            },
            "RETURN": _success_return("Customer read successfully"),
        }
    return {
        "CUSTOMERGENERALDETAIL": {},
        "RETURN": _error_return(f"Customer {custno} not found"),
    }


def _handle_customer_getlist(**params: object) -> dict:
    results = []
    for cust in _MOCK_CUSTOMERS.values():
        results.append({
            "CUSTOMER": cust["CUSTOMER"],
            "NAME": cust["NAME"],
            "CITY": cust["CITY"],
            "COUNTRY": cust["COUNTRY"],
        })
    return {"ADDRESSDATA": results, "RETURN": _success_return()}


def _handle_vendor_getdetail(**params: object) -> dict:
    vendorno = str(params.get("VENDORNO", ""))
    vendor = _MOCK_VENDORS.get(vendorno)
    if vendor:
        return {
            "GENERALDETAIL": {
                "VENDOR": vendor["VENDOR"],
                "NAME": vendor["NAME"],
                "STREET": vendor["STREET"],
                "CITY": vendor["CITY"],
                "POSTL_CODE": vendor["POSTL_CODE"],
                "COUNTRY": vendor["COUNTRY"],
            },
            "RETURN": _success_return("Vendor read successfully"),
        }
    return {
        "GENERALDETAIL": {},
        "RETURN": _error_return(f"Vendor {vendorno} not found"),
    }


def _handle_vendor_getlist(**params: object) -> dict:
    results = []
    for v in _MOCK_VENDORS.values():
        results.append({
            "VENDOR": v["VENDOR"],
            "NAME": v["NAME"],
            "CITY": v["CITY"],
            "COUNTRY": v["COUNTRY"],
        })
    return {"VENDORS": results, "RETURN": _success_return()}


def _handle_salesorder_getlist(**params: object) -> dict:
    customer = str(params.get("CUSTOMER_NUMBER", ""))
    results = []
    for so in _MOCK_SALES_ORDERS:
        if customer and so["SOLD_TO"] != customer:
            continue
        results.append({
            "SD_DOC": so["SD_DOC"],
            "DOC_TYPE": so["DOC_TYPE"],
            "SOLD_TO": so["SOLD_TO"],
            "PURCH_NO": so["PURCH_NO"],
            "DOC_DATE": so["DOC_DATE"],
            "NET_VALUE": so["NET_VALUE"],
            "CURRENCY": so["CURRENCY"],
        })
    return {"SALES_ORDERS": results, "RETURN": _success_return()}


def _handle_salesorder_getdetail(**params: object) -> dict:
    doc_num = str(params.get("I_BAPI_VIEW", {}).get("SD_DOC", "") or params.get("SALESDOCUMENT", ""))
    for so in _MOCK_SALES_ORDERS:
        if so["SD_DOC"] == doc_num:
            return {
                "ORDER_HEADER_IN": {
                    "SD_DOC": so["SD_DOC"],
                    "DOC_TYPE": so["DOC_TYPE"],
                    "SOLD_TO": so["SOLD_TO"],
                    "PURCH_NO": so["PURCH_NO"],
                    "DOC_DATE": so["DOC_DATE"],
                },
                "ORDER_ITEMS_IN": so["ITEMS"],
                "RETURN": _success_return(),
            }
    return {"ORDER_HEADER_IN": {}, "ORDER_ITEMS_IN": [], "RETURN": _error_return(f"Sales order {doc_num} not found")}


def _handle_salesorder_createfromdat2(**params: object) -> dict:
    global _NEXT_SO_NUMBER
    so_num = f"00000{_NEXT_SO_NUMBER}"
    _NEXT_SO_NUMBER += 1
    return {
        "SALESDOCUMENT": so_num,
        "RETURN": [_success_return(f"Sales order {so_num} created")],
    }


def _handle_salesorder_change(**params: object) -> dict:
    doc = str(params.get("SALESDOCUMENT", ""))
    return {
        "RETURN": [_success_return(f"Sales order {doc} changed successfully")],
    }


def _handle_po_getdetail1(**params: object) -> dict:
    po_num = str(params.get("PURCHASEORDER", ""))
    for po in _MOCK_PURCHASE_ORDERS:
        if po["PO_NUMBER"] == po_num:
            return {
                "PO_HEADER": {
                    "PO_NUMBER": po["PO_NUMBER"],
                    "DOC_TYPE": po["DOC_TYPE"],
                    "VENDOR": po["VENDOR"],
                    "DOC_DATE": po["DOC_DATE"],
                    "CURRENCY": po["CURRENCY"],
                },
                "PO_ITEMS": po["ITEMS"],
                "RETURN": [_success_return()],
            }
    return {"PO_HEADER": {}, "PO_ITEMS": [], "RETURN": [_error_return(f"PO {po_num} not found")]}


def _handle_po_getitems(**params: object) -> dict:
    results = []
    for po in _MOCK_PURCHASE_ORDERS:
        for item in po["ITEMS"]:
            results.append({
                "PO_NUMBER": po["PO_NUMBER"],
                "PO_ITEM": item["PO_ITEM"],
                "MATERIAL": item["MATERIAL"],
                "SHORT_TEXT": item["SHORT_TEXT"],
                "VENDOR": po["VENDOR"],
            })
    return {"PO_ITEMS": results, "RETURN": [_success_return()]}


def _handle_po_create1(**params: object) -> dict:
    global _NEXT_PO_NUMBER
    po_num = str(_NEXT_PO_NUMBER)
    _NEXT_PO_NUMBER += 1
    return {
        "PURCHASEORDER": po_num,
        "RETURN": [_success_return(f"Purchase order {po_num} created")],
    }


def _handle_bapi_transaction_commit(**params: object) -> dict:
    return {"RETURN": _success_return("Transaction committed")}


def _handle_bapi_transaction_rollback(**params: object) -> dict:
    return {"RETURN": _success_return("Transaction rolled back")}


def _handle_rfc_read_table(**params: object) -> dict:
    table_name = str(params.get("QUERY_TABLE", ""))
    delimiter = str(params.get("DELIMITER", "|"))
    fields_param = params.get("FIELDS", [])
    options = params.get("OPTIONS", [])
    rowcount = int(params.get("ROWCOUNT", 0))

    table_data = _MOCK_TABLES.get(table_name)
    if not table_data:
        return {
            "DATA": [],
            "FIELDS": [],
            "RETURN": _error_return(f"Table {table_name} not found"),
        }

    all_fields = table_data["fields"]
    if fields_param:
        requested = [f["FIELDNAME"] for f in fields_param if "FIELDNAME" in f]
        if requested:
            col_indices = [all_fields.index(f) for f in requested if f in all_fields]
            selected_fields = [all_fields[i] for i in col_indices]
        else:
            col_indices = list(range(len(all_fields)))
            selected_fields = all_fields
    else:
        col_indices = list(range(len(all_fields)))
        selected_fields = all_fields

    fields_out = [
        {"FIELDNAME": f, "OFFSET": str(i * 30), "LENGTH": "30", "TYPE": "C", "FIELDTEXT": f}
        for i, f in enumerate(selected_fields)
    ]

    rows = table_data["rows"]
    if rowcount > 0:
        rows = rows[:rowcount]

    data_out = []
    for row in rows:
        vals = [row[i] for i in col_indices]
        data_out.append({"WA": delimiter.join(vals)})

    return {"DATA": data_out, "FIELDS": fields_out}


def _handle_invoice_getlist(**params: object) -> dict:
    return {"INVOICELIST": _MOCK_INVOICES, "RETURN": _success_return()}


_FUNCTION_HANDLERS: dict[str, object] = {
    "BAPI_MATERIAL_GET_DETAIL": _handle_material_get_detail,
    "BAPI_MATERIAL_GETLIST": _handle_material_getlist,
    "BAPI_CUSTOMER_GETDETAIL2": _handle_customer_getdetail2,
    "BAPI_CUSTOMER_GETLIST": _handle_customer_getlist,
    "BAPI_VENDOR_GETDETAIL": _handle_vendor_getdetail,
    "BAPI_VENDOR_GETLIST": _handle_vendor_getlist,
    "BAPI_SALESORDER_GETLIST": _handle_salesorder_getlist,
    "BAPI_SALESORDER_GETDETAIL": _handle_salesorder_getdetail,
    "BAPI_SALESORDER_CREATEFROMDAT2": _handle_salesorder_createfromdat2,
    "BAPI_SALESORDER_CHANGE": _handle_salesorder_change,
    "BAPI_PO_GETDETAIL1": _handle_po_getdetail1,
    "BAPI_PO_GETITEMS": _handle_po_getitems,
    "BAPI_PO_CREATE1": _handle_po_create1,
    "BAPI_TRANSACTION_COMMIT": _handle_bapi_transaction_commit,
    "BAPI_TRANSACTION_ROLLBACK": _handle_bapi_transaction_rollback,
    "RFC_READ_TABLE": _handle_rfc_read_table,
    "BAPI_INCOMINGINVOICE_GETLIST": _handle_invoice_getlist,
}


_MOCK_FUNC_PARAMS: dict[str, list[dict]] = {
    "BAPI_MATERIAL_GET_DETAIL": [
        {"name": "MATERIAL", "parameter_type": "RFCTYPE_CHAR", "direction": "RFC_IMPORT",
         "nuc_length": 18, "uc_length": 36, "decimals": 0, "default_value": "",
         "optional": False, "parameter_text": "Material Number", "type_description": None},
        {"name": "MATERIAL_GENERAL_DATA", "parameter_type": "RFCTYPE_STRUCTURE", "direction": "RFC_EXPORT",
         "nuc_length": 0, "uc_length": 0, "decimals": 0, "default_value": "",
         "optional": True, "parameter_text": "Material General Data", "type_description": None},
        {"name": "RETURN", "parameter_type": "RFCTYPE_STRUCTURE", "direction": "RFC_EXPORT",
         "nuc_length": 0, "uc_length": 0, "decimals": 0, "default_value": "",
         "optional": True, "parameter_text": "Return Messages", "type_description": None},
    ],
    "RFC_READ_TABLE": [
        {"name": "QUERY_TABLE", "parameter_type": "RFCTYPE_CHAR", "direction": "RFC_IMPORT",
         "nuc_length": 30, "uc_length": 60, "decimals": 0, "default_value": "",
         "optional": False, "parameter_text": "Table name", "type_description": None},
        {"name": "DELIMITER", "parameter_type": "RFCTYPE_CHAR", "direction": "RFC_IMPORT",
         "nuc_length": 1, "uc_length": 2, "decimals": 0, "default_value": "|",
         "optional": True, "parameter_text": "Field delimiter", "type_description": None},
        {"name": "ROWCOUNT", "parameter_type": "RFCTYPE_INT", "direction": "RFC_IMPORT",
         "nuc_length": 4, "uc_length": 4, "decimals": 0, "default_value": "0",
         "optional": True, "parameter_text": "Max rows", "type_description": None},
        {"name": "OPTIONS", "parameter_type": "RFCTYPE_TABLE", "direction": "RFC_TABLES",
         "nuc_length": 72, "uc_length": 144, "decimals": 0, "default_value": "",
         "optional": True, "parameter_text": "Selection options", "type_description": None},
        {"name": "FIELDS", "parameter_type": "RFCTYPE_TABLE", "direction": "RFC_TABLES",
         "nuc_length": 0, "uc_length": 0, "decimals": 0, "default_value": "",
         "optional": True, "parameter_text": "Fields to read", "type_description": None},
        {"name": "DATA", "parameter_type": "RFCTYPE_TABLE", "direction": "RFC_TABLES",
         "nuc_length": 512, "uc_length": 1024, "decimals": 0, "default_value": "",
         "optional": True, "parameter_text": "Data rows", "type_description": None},
    ],
}
