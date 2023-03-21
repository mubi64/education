# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import erpnext
import frappe
from erpnext.accounts.doctype.payment_request.payment_request import \
    make_payment_request
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from frappe import _
from frappe.utils import money_in_words
from frappe.utils.csvutils import getlink
from frappe.query_builder import DocType


class Fees(AccountsController):
    def set_indicator(self):
        """Set indicator for portal"""
        if self.outstanding_amount > 0:
            self.indicator_color = "orange"
            self.indicator_title = _("Unpaid")
        else:
            # isRecorded = True
            # for i, fee in enumerate(self.components):
            #     if fee.income_recorded == 0:
            #         isRecorded = False
            #         break
            # if isRecorded:
            self.indicator_color = "green"
            self.indicator_title = _("Paid")
            # else:
            #     self.indicator_color = "orange"
            #     self.indicator_title = _("Paid, Income not Recorded")

    def validate(self):
        for i, comp in enumerate(self.components):
            comp.gross_amount = comp.amount if comp.gross_amount == 0 else comp.gross_amount
        self.append_transportation()
        self.append_discount()
        tax_and_char = 0
        for i, comp in enumerate(self.components):
            comp.taxes_and_charges = 0.0
            for i, tax in enumerate(self.taxes):
                rate = tax.rate / 100
                tax_and_char = comp.amount * rate
                comp.taxes_and_charges += tax_and_char
                comp.amount_after_tax = comp.taxes_and_charges + comp.amount

        for i, tax in enumerate(self.taxes):
            tax.tax_amount = 0
            tax.total = 0
            rate = tax.rate / 100
            for i, comp in enumerate(self.components):
                tax.tax_amount += comp.amount * rate
                tax.total += comp.taxes_and_charges + comp.amount

        self.calculate_total()
        self.set_missing_accounts_and_fields()

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
                            print(percent, "percent")
                            print(component.gross_amount,
                                  "omponent.gross_amount")
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

    def calculate_total(self):
        """Calculates total amount."""
        self.grand_total = 0
        for d in self.components:
            self.grand_total += d.amount
        # self.outstanding_amount = self.grand_total
        taxes_amount = 0
        for i, tax in enumerate(self.taxes):
            taxes_amount += tax.tax_amount
        self.total_taxes_and_charges = taxes_amount
        self.total_taxes_and_charges_company_currency = taxes_amount
        self.grand_total_before_tax = self.grand_total
        self.grand_total += taxes_amount
        self.outstanding_amount = self.grand_total
        self.grand_total_in_words = money_in_words(self.grand_total)

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
        if not self.record_income_in_temp_account:
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
                        "account": self.receivable_account,
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
            recorded_gl_entries.append(self.get_gl_dict(
                {
                    "account": self.receivable_account,
                    "party_type": "Student",
                    "party": self.student,
                    "against": self.income_account,
                    "debit": self.grand_total,
                    "debit_in_account_currency": self.grand_total,
                    "against_voucher": self.name,
                    "against_voucher_type": self.doctype,
                },
                item=self,
            ))

            recorded_gl_entries.append(self.get_gl_dict(
                {
                    "account": self.income_account,
                    "against": self.student,
                    "credit": self.grand_total,
                    "credit_in_account_currency": self.grand_total,
                    "cost_center": self.cost_center,
                },
                item=self,
            ))
        else:
            if not self.components:
                return
            gl_entries = []
            tax_gl_amount = 0
            for i, tax in enumerate(self.taxes):
                tax_gl_amount += tax.tax_amount
            gl_entries.append(self.get_gl_dict(
                {
                    "account": self.temporary_income_account,
                    "against": self.student,
                    "credit": tax_gl_amount,
                    "credit_in_account_currency": tax_gl_amount,
                    "cost_center": tax.cost_center,
                },
                item=self,
            ))
            gl_entries.append(self.get_gl_dict(
                {
                    "account": self.receivable_account,
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
                student_gl_entry = self.get_gl_dict(
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
                )
                gl_entries.append(student_gl_entry)
            fee_gl_entry = self.get_gl_dict(
                {
                    "account": self.temporary_income_account,
                    "against": self.student,
                    "credit": self.grand_total_before_tax,
                    "credit_in_account_currency": self.grand_total_before_tax,
                    "cost_center": self.cost_center,
                },
                item=self,
            )
            gl_entries.append(fee_gl_entry)

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
def record_income(fees, current_docname):
    fees = eval(fees)
    if not fees:
        return
    current_doc = frappe.get_doc('Fees', current_docname)
    gl_entries = []
    amount = 0
    for i, comp in enumerate(fees):
        for i, tax in enumerate(current_doc.taxes):
            gl_rate = tax.rate / 100
            amount = comp["amount"] * gl_rate
            gl_entries.append(current_doc.get_gl_dict(
                {
                    "account": current_doc.temporary_income_account,
                    "party_type": "Student",
                    "party": current_doc.student,
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
                    "against": current_doc.student,
                    "credit": amount,
                    "credit_in_account_currency": amount,
                    "cost_center": tax.cost_center,
                },
                item=current_doc,
            ))
    for i, fee in enumerate(fees):
        fee_doc = frappe.get_doc('Fee Category', fee["fees_category"])
        student_gl_entry = current_doc.get_gl_dict(
            {
                "account": current_doc.temporary_income_account,
                "party_type": "Student",
                "party": current_doc.student,
                "against": fee_doc.income_account,
                "debit": fee["amount"],
                "debit_in_account_currency": fee["amount"],
                "against_voucher": current_doc.name,
                "against_voucher_type": current_doc.doctype,
            },
            item=current_doc,
        )

        fee_gl_entry = current_doc.get_gl_dict(
            {
                "account": fee_doc.income_account,
                "against": current_doc.student,
                "credit": fee["amount"],
                "credit_in_account_currency": fee["amount"],
                "cost_center": current_doc.cost_center,
            },
            item=current_doc,
        )
        gl_entries.append(student_gl_entry)
        gl_entries.append(fee_gl_entry)
        for i, comp in enumerate(current_doc.components):
            if comp.fees_category == fee["fees_category"]:
                frappe.db.set_value('Fee Component', comp.name,
                                    'income_recorded', 1, update_modified=True)

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
