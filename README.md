# jasper_connector

## A module to run existing reports on a JasperSoft Server.

<span style="font-family: Helvetica,Arial,sans-serif;">The work is based on the original module of Mirounga, but its philosophy is more to stay with the standard design architecture of JasperSoft.  

In extension:  

</span>

*   Design your report with JasperSoft Studio
*   Publish it to the JasperSoft Server Repository
*   Use it in Odoo

<span style="font-family: Helvetica,Arial,sans-serif;">There are two ways of calling reports:  

</span>

1.  As any other report

<div style="font-family: Helvetica,Arial,sans-serif; margin-left: 40px;">

- You define a jasperDocument which refers to the existing report in the JasperSoft Server Repository  
- Filter you records through standard Odoo search filtering  
- Generate your report  

</div>

2.  Through the generic report caller

<div style="font-family: Helvetica,Arial,sans-serif; margin-left: 40px;">

- You define a jasperDocument which refers to the existing report in the JasperSoft Server Repository  
- open the generic jasperreport wizard  
- Provide any report parameters  
- Generate your report

</div>

Tibco, JasperSoft and JasperSoft Studio are trademarks of Tibco Sotware Inc.