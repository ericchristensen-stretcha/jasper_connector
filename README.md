jasper_connector
-----------------------

This module interfaces JasperReport Server with Odoo V10

The work is based on the work of Mirounga, but it is more geared
towards the successfull calling of an existing report existing on the
jasperserver.

Goals:

- create a report via JasperStudio
- publish the report
- call the report as any other report in Odoo (Print action)

This module required library to work properly

# pip install httplib2 (>= 0.6.0)
# pip install pyPdf (>= 1.13)
