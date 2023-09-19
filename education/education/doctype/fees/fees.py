# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import erpnext
import frappe
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from frappe import _
from frappe.utils import money_in_words, add_months, add_days, flt
from frappe.utils.csvutils import getlink
from frappe.query_builder import DocType


class Fees(AccountsController):
    def set_indicator(self):
        """Set indicator for portal"""
        if self.outstanding_amount > 0:
            self.indicator_color = "orange"
            self.indicator_title = _("Unpaid")
        else:
            self.indicator_color = "green"
            self.indicator_title = _("Paid")

    def validate(self):
        fees_category_array = []
        one_month_earlier = add_months(self.posting_date, -1)
        # Subtract one day
        # result_date = one_month_earlier + timedelta(days=1)
        result_date = add_days(one_month_earlier, 1)
        for com in self.components:
            fees_category_array.append(com.fees_category)
        
        fee = frappe.db.get_all("Fees", filters=[
                ['name', '!=', self.name],
                ['docstatus', "!=", 2],
                ['posting_date', 'between', [result_date, self.posting_date]],
                ['student', "=", self.student],
                ['Fee Component', 'fees_category', 'in', fees_category_array]
            ], fields=["*"])

        if len(fee) > 0:
            # frappe.throw(_("Duplicating fee creation is not permitted."), status_code="404")
            raise TypeError(_("Duplicating fee creation is not permitted."))
        else:
            for i, comp in enumerate(self.components):
                comp.gross_amount = comp.amount if comp.gross_amount == 0 else comp.gross_amount
            self.set_late_fee_fine_and_readmission()
            self.append_transportation()
            self.append_discount()
            self.set_missing_accounts_and_fields()
            self.calculate_total()

    def set_late_fee_fine_and_readmission(self):
        due_date = str(self.due_date)
        current_date = frappe.utils.today()
        fees_category_list = []

        if due_date < current_date:
            diff_days = frappe.utils.date_diff(current_date,due_date)
            for i in self.components:
                if i.fees_category == "Late Fee Fine" or i.fees_category == "Re-Admission Fee":
                    fees_category_list.append(i.fees_category)
                
            if diff_days <= 40 and diff_days > 0:
                if "Late Fee Fine" not in fees_category_list:
                    self.append("components",{
                        "fees_category": "Late Fee Fine",
                        "gross_amount": diff_days,
                        "amount": diff_days
                    })
                else:
                    for i in self.components:
                        if i.fees_category == "Late Fee Fine":
                            i.amount = diff_days
                            i.gross_amount = diff_days
                            
                if "Re-Admission Fee" in fees_category_list:
                    self.components = [i for i in self.components if i.fees_category != "Re-Admission Fee"]
            elif diff_days > 40:
                if "Late Fee Fine" not in fees_category_list:
                    self.append("components",{
                        "fees_category": "Late Fee Fine",
                        "gross_amount": 40,
                        "amount": 40
                    })
                else:
                    for i in self.components:
                        if i.fees_category == "Late Fee Fine":
                            i.amount = 40
                            i.gross_amount = 40
                if "Re-Admission Fee" not in fees_category_list:
                    self.append("components",{
                        "fees_category": "Re-Admission Fee",
                        "gross_amount": 50,
                        "amount": 50
                    })
                else:
                    for i in self.components:
                        if i.fees_category == "Re-Admission Fee":
                            i.amount = 50
                            i.gross_amount = 50

    def append_discount(self):
        discount_doc = get_student_dicount(self.student)
        if discount_doc != None:
            discounts = discount_doc.discount
            for e, component in enumerate(self.components):
                for i, discount in enumerate(discounts):
                    if component.fees_category == discount.fee_category:
                        component.discount_type = discount.discount_type
                        if discount.discount_type == "Percentage":
                            component.percentage = discount.percentage
                            percent = component.percentage / 100
                            discount_amount = percent * component.gross_amount
                            component.amount = component.gross_amount - discount_amount
                        elif discount.discount_type == "Amount":
                            component.discount_amount = discount.amount
                            component.amount = component.gross_amount - component.discount_amount

    def append_transportation(self):
        fee_student = frappe.get_doc('Student', self.student)
        if fee_student.transportation_fee_structure:
            transportation_student = frappe.get_doc(
                'Transportation Fee Structure', fee_student.transportation_fee_structure)
            # self.total_amount += transportation_student.fee_amount
            insert = False
            for i, comp in enumerate(self.components):
                if comp.fees_category != transportation_student.fee_category:
                    insert = True
                else:
                    insert = False
            if insert:
                row = self.append('components', {})
                row.fees_category = transportation_student.fee_category
                row.amount = transportation_student.fee_amount
                row.gross_amount = transportation_student.fee_amount

    def set_missing_accounts_and_fields(self):
        if not self.company:
            self.company = frappe.defaults.get_defaults().company
        if not self.currency:
            self.currency = erpnext.get_company_currency(self.company)
        if not (self.receivable_account and self.income_account and self.cost_center):
            accounts_details = frappe.get_all(
                "Company",
                fields=["default_receivable_account",
                        "default_income_account", "cost_center"],
                filters={"name": self.company},
            )[0]
        if not self.receivable_account:
            self.receivable_account = accounts_details.default_receivable_account
        if not self.income_account:
            self.income_account = accounts_details.default_income_account
        if not self.cost_center:
            self.cost_center = accounts_details.cost_center
        if not self.student_email:
            self.student_email = self.get_student_emails()

    def calculate_total(self):
        """Calculates total amount."""
        tax_and_char = 0
        tax_amount = 0
        tax_total = 0
        for i, comp in enumerate(self.components):
            comp.taxes_and_charges = 0.0
            for i, tax in enumerate(self.taxes):
                rate = tax.rate / 100
                tax_and_char = comp.amount * rate
                comp.taxes_and_charges += tax_and_char
                comp.amount_after_tax = comp.taxes_and_charges + comp.amount
                tax_amount += comp.taxes_and_charges
                tax_total += comp.amount
                tax.tax_amount = tax_amount
                tax.total = tax_total + tax.tax_amount
                # print(comp.amount, comp.taxes_and_charges, "text")
                # tax.tax_amount = comp.taxt


        for i, tax in enumerate(self.taxes):
            if not tax.tax_amount or not tax.total:
                tax.tax_amount = 0
                tax.total = 0
                rate = tax.rate / 100
                for i, comp in enumerate(self.components):
                    # print(comp.taxes_and_charges, "checking")
                    tax.tax_amount += comp.amount * rate
                    tax.total += comp.taxes_and_charges + comp.amount


        self.grand_total = 0
        for d in self.components:
            self.grand_total += d.amount
        taxes_amount = 0
        for i, tax in enumerate(self.taxes):
            taxes_amount += tax.tax_amount
        self.amount_before_discount = self.grand_total
        self.total_discount_amount = flt(self.amount_before_discount) - flt(self.grand_total_before_tax)
        if self.discount_type == "Amount":
            self.grand_total = flt(self.grand_total) - flt(self.discount_amount)
        
        if self.discount_type == "Percentage":
            percentage = self.percentage / 100
            self.grand_total = flt(self.grand_total) - flt(self.grand_total * percentage)
        
        self.grand_total_before_tax = self.grand_total
        if self.discount_type != "":
            taxes_amount = 0
            for i, row in enumerate(self.taxes):
                rate_persent = row.rate / 100
                amount = rate_persent * self.grand_total_before_tax
                row.total = amount + self.grand_total_before_tax
                row.tax_amount = amount
                taxes_amount += amount


        self.total_taxes_and_charges = taxes_amount
        self.total_taxes_and_charges_company_currency = taxes_amount
        self.grand_total += taxes_amount
        self.grand_total_in_words = money_in_words(self.grand_total)
        self.outstanding_amount = self.grand_total

    def get_student_emails(self):
        student_emails = frappe.db.sql_list(
            """
			select g.email_address
			from `tabGuardian` g, `tabStudent Guardian` sg
			where g.name = sg.guardian and sg.parent = %s and sg.parenttype = 'Student'
			and ifnull(g.email_address, '')!=''
		""",
            self.student,
        )

        student_email_id = frappe.db.get_value(
            "Student", self.student, "student_email_id")
        if student_email_id:
            student_emails.append(student_email_id)
        if student_emails:
            return ", ".join(list(set(student_emails)))
        else:
            return None

    def on_submit(self):
        self.make_gl_entries()

        if self.send_payment_request and self.student_email:
            pr = make_payment_request(
                party_type="Student",
                party=self.student,
                dt="Fees",
                dn=self.name,
                recipient_id=self.student_email,
                submit_doc=True,
                use_dummy_message=True,
            )
            frappe.msgprint(
                _("Payment request {0} created").format(
                    getlink("Payment Request", pr.name))
            )

    def on_cancel(self):
        self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
        make_reverse_gl_entries(
            voucher_type=self.doctype, voucher_no=self.name)
        # frappe.db.set(self, 'status', 'Cancelled')

    
    def make_gl_entries(self):
        if not self.grand_total:
            return
            
        recorded_gl_entries = []
        gl_entries = []
        temporary_income_account = self.temporary_income_account
        receivable_account = self.receivable_account
        income_account = self.income_account
        total_discount_amount = self.total_discount_amount
        amount_before_discount = self.amount_before_discount
        tax_gl_amount = sum(tax.tax_amount for tax in self.taxes) if self.taxes else 0
        
        if not self.record_income_in_temp_account:
            if self.taxes:
                for i, tax in enumerate(self.taxes):
                    recorded_gl_entries.append(self.get_gl_dict(
                        {
                            "account": tax.account_head,
                            "against": self.student,
                            "credit": tax.tax_amount,
                            "credit_in_account_currency": tax.tax_amount,
                            "cost_center": self.cost_center,
                        },
                        item=self,
                    ))
                    recorded_gl_entries.append(self.get_gl_dict(
                        {
                            "account": receivable_account,
                            "party_type": "Student",
                            "party": self.student,
                            "against": tax.account_head,
                            "debit": tax.tax_amount,
                            "debit_in_account_currency": tax.tax_amount,
                            "against_voucher": self.name,
                            "against_voucher_type": self.doctype,
                        },
                        item=self,
                    ))

            for i, fee in enumerate(self.components):
                recorded_gl_entries.append(self.get_gl_dict(
                    {
                        "account": receivable_account,
                        "party_type": "Student",
                        "party": self.student,
                        "against": income_account,
                        "debit": fee.amount,
                        "debit_in_account_currency": fee.amount,
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                    },
                    item=self,
                ))
            if self.discount_type != "":
                recorded_gl_entries.append(self.get_gl_dict(
                    {
                        "account": receivable_account,
                        "party_type": "Student",
                        "party": self.student,
                        "against": self.student,
                        "credit": total_discount_amount,
                        "credit_in_account_currency": total_discount_amount,
                        "cost_center": self.cost_center,
                    },
                    item=self,
                ))

                recorded_gl_entries.append(self.get_gl_dict(
                    {
                        "account": self.income_account,
                        "party_type": "Student",
                        "party": self.student,
                        "against": self.student,
                        "debit": total_discount_amount,
                        "debit_in_account_currency": total_discount_amount,
                        "cost_center": self.cost_center,
                    },
                    item=self,
                ))
            for i, fee in enumerate(self.components):
                fee_doc = frappe.get_doc('Fee Category', fee.fees_category)
                recorded_gl_entries.append(self.get_gl_dict(
                    {
                        "account": fee_doc.income_account,
                        "against": self.student,
                        "credit": fee.amount,
                        "credit_in_account_currency": fee.amount,
                        "cost_center": self.cost_center,
                    },
                    item=self,
                ))
                # recorded_gl_entries.append(self.get_gl_dict(
                #     {
                #         "account": income_account,
                #         "against": self.student,
                #         "credit": amount_before_discount,
                #         "credit_in_account_currency": amount_before_discount,
                #         "cost_center": self.cost_center,
                #     },
                #     item=self,
                # ))

        else:
            if not self.components:
                return
            if self.taxes:
                # for i, tax in enumerate(self.taxes):
                #     tax_gl_amount += tax.tax_amount
                gl_entries.append(self.get_gl_dict(
                    {
                        "account": temporary_income_account,
                        "party_type": "Student",
                        "party": self.student,
                        "against": self.student,
                        "credit": tax_gl_amount,
                        "credit_in_account_currency": tax_gl_amount,
                        "cost_center": self.cost_center,
                    },
                    item=self,
                ))
                gl_entries.append(self.get_gl_dict(
                    {
                        "account": receivable_account,
                        "party_type": "Student",
                        "party": self.student,
                        "debit": tax_gl_amount,
                        "debit_in_account_currency": tax_gl_amount,
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                    },
                    item=self,
                ))
            for i, fee in enumerate(self.components):
                fee_doc = frappe.get_doc('Fee Category', fee.fees_category)
                gl_entries.append(self.get_gl_dict(
                    {
                        "account": fee_doc.receivable_account,
                        "party_type": "Student",
                        "party": self.student,
                        "against": fee_doc.income_account,
                        "debit": fee.amount,
                        "debit_in_account_currency": fee.amount,
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                    },
                    item=self,
                ))
                
            gl_entries.append(self.get_gl_dict(
                {
                    "account": temporary_income_account,
                    "party_type": "Student",
                    "party": self.student,
                    "against": self.student,
                    "credit": amount_before_discount,
                    "credit_in_account_currency": amount_before_discount,
                    "cost_center": self.cost_center,
                },
                item=self,
            ))
            
            if self.discount_type != "":
                gl_entries.append(self.get_gl_dict(
                    {
                        "account": receivable_account,
                        "party_type": "Student",
                        "party": self.student,
                        "against": self.student,
                        "credit": total_discount_amount,
                        "credit_in_account_currency": total_discount_amount,
                        "cost_center": self.cost_center,
                    },
                    item=self,
                ))

                gl_entries.append(self.get_gl_dict(
                    {
                        "account": temporary_income_account,
                        "party_type": "Student",
                        "party": self.student,
                        "against": self.student,
                        "debit": total_discount_amount,
                        "debit_in_account_currency": total_discount_amount,
                        "cost_center": self.cost_center,
                    },
                    item=self,
                ))

        from erpnext.accounts.general_ledger import make_gl_entries
        make_gl_entries(
            recorded_gl_entries if not self.record_income_in_temp_account else gl_entries,
            cancel=(self.docstatus == 2),
            update_outstanding="Yes",
            merge_entries=False,
        )


def get_fee_list(
        doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
    user = frappe.session.user
    student = frappe.db.sql(
        "select name from `tabStudent` where student_email_id= %s", user
    )
    if student:
        return frappe.db.sql(
            """
			select name, program, due_date, grand_total - outstanding_amount as paid_amount,
			outstanding_amount, grand_total, currency
			from `tabFees`
			where student= %s and docstatus=1
			order by due_date asc limit {0} , {1}""".format(
                limit_start, limit_page_length
            ),
            student,
            as_dict=True,
        )


def get_list_context(context=None):
    return {
        "show_sidebar": True,
        "show_search": True,
        "no_breadcrumbs": True,
        "title": _("Fees"),
        "get_list": get_fee_list,
        "row_template": "templates/includes/fee/fee_row.html",
    }

@frappe.whitelist()
def record_payment(fees, current_docname):
    fees = eval(fees)
    if not fees:
        return
    current_doc = frappe.get_doc('Fees', current_docname)
    for i, fee in enumerate(fees):
        for i, comp in enumerate(current_doc.components):
                if comp.fees_category == fee["fees_category"]:
                    frappe.db.set_value('Fee Component', comp.name,
                                        'income_recorded', 1, update_modified=True)


@frappe.whitelist()
def record_income(fees, current_docname):
    fees = eval(fees)
    if not fees:
        return
    current_doc = frappe.get_doc('Fees', current_docname)
    gl_entries = []
    amount = 0
    temporary_income_account = current_doc.temporary_income_account
    student = current_doc.student
    total_discount_amount = current_doc.total_discount_amount
    for i, comp in enumerate(fees):
        for i, tax in enumerate(current_doc.taxes):
            gl_rate = tax.rate / 100
            amount = comp["amount"] * gl_rate
            gl_entries.append(current_doc.get_gl_dict(
                {
                    "account": temporary_income_account,
                    "party_type": "Student",
                    "party": student,
                    "debit": amount,
                    "debit_in_account_currency": amount,
                    "against_voucher": current_doc.name,
                    "against_voucher_type": current_doc.doctype,
                },
                item=current_doc,
            ))
            gl_entries.append(current_doc.get_gl_dict(
                {
                    "account": tax.account_head,
                    "against": student,
                    "credit": amount,
                    "credit_in_account_currency": amount,
                    "cost_center": tax.cost_center,
                },
                item=current_doc,
            ))
    for i, fee in enumerate(fees):
        fee_doc = frappe.get_doc('Fee Category', fee["fees_category"])
        gl_entries.append(current_doc.get_gl_dict(
            {
                "account": temporary_income_account,
                "party_type": "Student",
                "party": student,
                "against": fee_doc.income_account,
                "debit": fee["amount"],
                "debit_in_account_currency": fee["amount"],
                "against_voucher": current_doc.name,
                "against_voucher_type": current_doc.doctype,
            },
            item=current_doc,
        ))

        gl_entries.append(current_doc.get_gl_dict(
            {
                "account": fee_doc.income_account,
                "against": student,
                "credit": fee["amount"],
                "credit_in_account_currency": fee["amount"],
                "cost_center": current_doc.cost_center,
            },
            item=current_doc,
        ))
        for i, comp in enumerate(current_doc.components):
            if comp.fees_category == fee["fees_category"]:
                frappe.db.set_value('Fee Component', comp.name,
                                    'income_recorded', 1, update_modified=True)
                
    gl_entries.append(current_doc.get_gl_dict(
        {
            "account": temporary_income_account,
            "against": student,
            "credit": total_discount_amount,
            "credit_in_account_currency": total_discount_amount,
            "cost_center": current_doc.cost_center,
        },
        item=current_doc,
    ))

    gl_entries.append(current_doc.get_gl_dict(
        {
            "account": fee_doc.income_account,
            "party_type": "Student",
            "party": student,
            "against": fee_doc.income_account,
            "debit": total_discount_amount,
            "debit_in_account_currency": total_discount_amount,
            "against_voucher": current_doc.name,
            "against_voucher_type": current_doc.doctype,
            "cost_center": current_doc.cost_center,
        },
        item=current_doc,
    ))

    from erpnext.accounts.general_ledger import make_gl_entries

    make_gl_entries(
        gl_entries,
        cancel=(current_doc.docstatus == 2),
        update_outstanding="No",
    )


@frappe.whitelist()
def get_student_dicount(student):
    fee_student = frappe.get_doc('Student', student)
    if fee_student.fee_discount_type:
        return frappe.get_doc(
            'Fee Discount Type', fee_student.fee_discount_type)
