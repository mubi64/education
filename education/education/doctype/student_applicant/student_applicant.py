# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import AccountsController
from frappe.utils import add_years, date_diff, getdate, nowdate


class StudentApplicant(AccountsController):
    def autoname(self):
        from frappe.model.naming import set_name_by_naming_series

        if self.student_admission:
            naming_series = None
            if self.program:
                # set the naming series from the student admission if provided.
                student_admission = get_student_admission_data(
                    self.student_admission, self.program)
                if student_admission:
                    naming_series = student_admission.get(
                        "applicant_naming_series")
                else:
                    naming_series = None
            else:
                frappe.throw(_("Select the program first"))

            if naming_series:
                self.naming_series = naming_series

        set_name_by_naming_series(self)

    def validate(self):
        # total_fee = 0
        # total_fee_amount = 0
        # total_tax_amounts = 0
        self.validate_dates()
        self.validate_term()
        education_setting = frappe.get_doc("Education Settings")
        if education_setting.account_paid_to and not self.account_paid_to:
            self.account_paid_to = education_setting.account_paid_to
        elif education_setting.income_account and not self.income_account:
            self.income_account = education_setting.income_account

        self.validate_student_tax()

        self.title = " ".join(
            filter(None, [self.first_name, self.middle_name, self.last_name])
        )

        if self.student_admission and self.program and self.date_of_birth:
            self.validation_from_student_admission()

    def validate_student_tax(self):
        student_admission = get_student_admission(self.student_admission)
        tax_and_charges = 0
        if student_admission:
            total = 0
            if len(student_admission.program_details) > 0:
                for i, sadmission in enumerate(student_admission.program_details):
                    if (self.program == sadmission.program):
                        total = sadmission.application_fee
                        if not self.taxes_and_charges and sadmission.taxes_and_charges:
                            self.taxes_and_charges = sadmission.taxes_and_charges
            if self.taxes_and_charges and len(self.taxes) == 0:
                from education.education.api import get_fee_sales_charges
                taxes_and_charges_table = get_fee_sales_charges(
                    self.taxes_and_charges)
                for i, tax in enumerate(taxes_and_charges_table):
                    row = self.append('taxes', {})
                    row.charge_type = tax.charge_type
                    row.account_head = tax.account_head
                    row.description = tax.description
                    row.cost_center = tax.cost_center
                    row.rate = tax.rate
                    row.included_in_print_rate = tax.included_in_print_rate

            self.total = total
            self.grand_total_before_tax = total
            self.grand_total = total
            total_tax = 0
            if self.taxes:
                for i, tax in enumerate(self.taxes):
                    rate_persent = tax.rate / 100
                    total_amount = 0
                    amount = 0
                    uncheck_grand_total =0


                    if len(student_admission.program_details) > 0:
                        for e, program in enumerate(student_admission.program_details):
                            if (self.program == sadmission.program):
                                total_amount = program.application_fee
                                amount = rate_persent * program.application_fee

                        grand_total = total

                        if tax.included_in_print_rate == 1:
                            rate_plus_1 = rate_persent + 1
                            total_amount = total_amount + amount
                            totals = total_amount / rate_plus_1
                            tax.tax_amount = total_amount - totals
                            tax.total = totals
                            tax_and_charges += total_amount - totals
                            grand_total += tax_and_charges
                            print(grand_total, tax_and_charges, grand_total -
                                  tax_and_charges, "check grand total")
                            self.grand_total = grand_total - tax_and_charges
                        else:
                            tax.tax_amount = amount
                            tax.total = total_amount + amount
                            totals = total_amount + amount
                            tax_and_charges += amount
                            print(total_amount, amount, total_amount +
                                  amount, "uncheck grand total")
                            uncheck_grand_total+= total_amount + amount
                            self.grand_total = uncheck_grand_total
                            print(total, tax_and_charges, total -
                                  tax_and_charges, "uncheck grand total before tax")
                        self.grand_total_before_tax = self.grand_total - tax_and_charges
                        total_tax += tax.tax_amount
                        self.total_taxes_and_charges = total_tax
                        self.total_taxes_and_charges_company_currency = total_tax 


    def validate_dates(self):
        if self.date_of_birth and getdate(self.date_of_birth) >= getdate():
            frappe.throw(_("Date of Birth cannot be greater than today."))

    def validate_term(self):
        if self.academic_year and self.academic_term:
            actual_academic_year = frappe.db.get_value(
                "Academic Term", self.academic_term, "academic_year"
            )
            if actual_academic_year != self.academic_year:
                frappe.throw(
                    _("Academic Term {0} does not belong to Academic Year {1}").format(
                        self.academic_term, self.academic_year
                    )
                )

    def on_update_after_submit(self):
        student = frappe.get_list(
            "Student", filters={"student_applicant": self.name})
        if student:
            frappe.throw(
                _(
                    "Cannot change status as student {0} is linked with student application {1}"
                ).format(student[0].name, self.name)
            )

    def on_submit(self):
        if self.paid and not self.student_admission:
            frappe.throw(
                _(
                    "Please select Student Admission which is mandatory for the paid student applicant"
                )
            )

    def validation_from_student_admission(self):

        student_admission = get_student_admission_data(
            self.student_admission, self.program)

        if (
                student_admission
                and student_admission.min_age
                and date_diff(
                    nowdate(), add_years(getdate(self.date_of_birth), student_admission.min_age)
                )
                < 0
        ):
            frappe.throw(
                _("Not eligible for the admission in this program as per Date Of Birth")
            )

        if (
                student_admission
                and student_admission.max_age
                and date_diff(
                    nowdate(), add_years(getdate(self.date_of_birth), student_admission.max_age)
                )
                > 0
        ):
            frappe.throw(
                _("Not eligible for the admission in this program as per Date Of Birth")
            )

    def on_payment_authorized(self, *args, **kwargs):
        self.db_set("paid", 1)


def get_student_admission_data(student_admission, program):

    student_admission = frappe.db.sql(
        """select sa.admission_start_date, sa.admission_end_date,
		sap.program, sap.min_age, sap.max_age, sap.applicant_naming_series
		from `tabStudent Admission` sa, `tabStudent Admission Program` sap
		where sa.name = sap.parent and sa.name = %s and sap.program = %s""",
        (student_admission, program),
        as_dict=1,
    )

    if student_admission:
        return student_admission[0]
    else:
        return None


@frappe.whitelist()
def get_student_admission(name):
    doc = frappe.get_doc('Student Admission', name)

    return doc


@frappe.whitelist()
def make_payment(doc, current_docname):
    doc = eval(doc)
    if not doc:
        return
    current_doc = frappe.get_doc('Student Applicant', current_docname)
    current_company = frappe.get_doc('Company', current_doc.company)
    gl_entries = []
    amount = 0
    for i, tax in enumerate(current_doc.taxes):
        amount = tax.tax_amount

        gl_entries.append(current_doc.get_gl_dict(
            {
                "account": tax.account_head,
                "credit": amount,
                "credit_in_account_currency": amount,
                "cost_center": tax.cost_center,
            },
            item=current_doc,
        ))
    # fee_doc = frappe.get_doc('Fee Category', fee["fees_category"])

    fee_gl_entry = current_doc.get_gl_dict(
        {
            "account": current_doc.income_account,
            "credit": current_doc.grand_total_before_tax,
            "credit_in_account_currency": current_doc.grand_total_before_tax,
            "cost_center": current_company.cost_center,
            "against_voucher": current_doc.name,
            "against_voucher_type": current_doc.doctype,
        },
        item=current_doc,
    )
    student_gl_entry = current_doc.get_gl_dict(
        {
            "account": current_doc.account_paid_to,
            "debit": current_doc.grand_total,
            "debit_in_account_currency": current_doc.grand_total,
            "cost_center": current_company.cost_center,
            "against_voucher": current_doc.name,
            "against_voucher_type": current_doc.doctype,
        },
        item=current_doc,
    )
    gl_entries.append(student_gl_entry)
    gl_entries.append(fee_gl_entry)

    from erpnext.accounts.general_ledger import make_gl_entries

    make_gl_entries(
        gl_entries,
        cancel=(current_doc.docstatus == 2),
        update_outstanding="No",
    )
