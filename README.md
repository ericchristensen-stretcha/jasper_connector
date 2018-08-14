jasper_connector
-----------------------

This module interfaces JasperReport Server with Odoo V10

Features:
- Document source must be in CSV, XML
- Save document as attachment on object
- Retrieve attachment if present
- Launch multiple reports and merge in one printing action
- Add additionnals parameters (ex from fields function)
- Affect group on report
- Use context to display or not the print button
    (eg: in stock.picking separate per type)
- Execute SQL query before and after treatement
- Launch report based on SQL View
- Add additional pages at the begining or at the end of the document

This module required library to work properly

# pip install httplib2 (>= 0.6.0)
# pip install pyPdf (>= 1.13)
