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
        # student_admission = get_student_admission(self.student_admission)
        # for i, program in enumerate(student_admission.program_details):
        #     total_fee += program.application_fee
        #     for i, tax in enumerate(self.taxes):
        #         if tax.included_in_print_rate == 1:
        #             rate = (tax.rate / 100) + 1
        #             total_fee_amount = total_fee / rate
        #             tax_amount = total_fee - total_fee_amount
        #             total_tax_amounts += tax_amount
        #             tax.tax_amount = tax_amount
        #             tax.total = total_fee_amount
        #             total_fee = total_fee_amount
        #         else:
        #             rate = tax.rate / 100
        #             tax_amount = rate * total_fee
        #             total_tax_amounts += tax_amount
        #             tax.tax_amount = tax_amount
        #             tax.total = total_fee

        # self.total_taxes_and_charges = total_tax_amounts
        # self.total_taxes_and_charges_company_currency = total_tax_amounts
        # self.grand_total_before_tax = total_fee
        # self.grand_total = total_fee + total_tax_amounts
        self.title = " ".join(
            filter(None, [self.first_name, self.middle_name, self.last_name])
        )

        if self.student_admission and self.program and self.date_of_birth:
            self.validation_from_student_admission()

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
