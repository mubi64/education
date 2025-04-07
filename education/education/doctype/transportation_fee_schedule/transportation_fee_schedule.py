# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import erpnext
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import add_months, add_days
from education.education.api import get_current_enrollment


class TransportationFeeSchedule(Document):
	def onload(self):
		info = self.get_dashboard_info()
		self.set_onload("dashboard_info", info)

	def get_dashboard_info(self):
		info = {
			"total_paid": 0,
			"total_unpaid": 0,
			"currency": erpnext.get_company_currency(self.company),
		}

		return info

	def validate(self):
		if self.total_student == 0:
			frappe.throw(_("Please get student first"))

	@frappe.whitelist()
	def create_fees(self):
		if self.total_student > 10:
			frappe.msgprint(
				_(
					"""Fee records will be created in the background.
				In case of any error the error message will be updated in the Schedule."""
				)
			)
			enqueue(
				self.generate_fee,
				queue="default",
				timeout=6000,
				event="generate_fee",
			)
		else:
			self.generate_fee()
	
	def generate_fee(self):
		students = frappe.db.get_all("Student", filters=[
			["transportation_fee_structure", "is", "set"],
			["enabled", "=", 1]
		], fields=['name'])

		if not students:
			frappe.throw("There are no students with a transportation fee structure enabled.")

		created_records = 0
		error = False
		error_logs = []

		for st in students:
			try:
				enrollment = get_current_enrollment(st.name)
				if not enrollment:
					error = True
					error_logs.append(f"Enrollment not found for student {st.name}")
					continue

				one_month_earlier = add_months(self.posting_date, -1)
				result_date = add_days(one_month_earlier, 1)

				student = frappe.get_doc("Student", st.name, fields=['*'])
				trans_student = frappe.get_doc("Transportation Fee Structure", student.transportation_fee_structure, fields=['*'])
				
				# Check if fee already exists
				existing_fees = frappe.db.get_all("Fees", filters=[
					['docstatus', "!=", 2],
					['posting_date', 'between', [result_date, self.posting_date]],
					['student', "=", student.name],
					['Fee Component', 'fees_category', '=', trans_student.fee_category]
				], fields=["name"])

				if existing_fees:
					continue  # Skip if fee already exists

				tran_months_array = [m.month_number for m in trans_student.transportation_fee_structure_months]
				posting_month = frappe.utils.formatdate(self.posting_date, "MM")
				if frappe.utils.getdate(str(self.posting_date)) >= frappe.utils.getdate(str(student.start_date)):
					if (posting_month in tran_months_array): # and trans_student.dependant_fee_category in fees_category_array
						fee = frappe.new_doc('Fees')
						fee.student = student.name
						fee.program = enrollment.program
						fee.posting_date = self.posting_date
						fee.transportation_fee_schedule = self.name
						fee.due_date = self.due_date
						fee.components = []
						fee.append('components', {
							"fees_category": trans_student.fee_category,
							"amount": trans_student.fee_amount,
							"gross_amount": trans_student.fee_amount
						})
						fee.taxes_and_charges = self.taxes_and_charges
						for tax in self.taxes:
							fee.append("taxes", {
								"charge_type": tax.charge_type,
								"description": tax.description,
								"account_head": tax.account_head,
								"included_in_print_rate": tax.included_in_print_rate,
								"cost_center": tax.cost_center,
								"rate": tax.rate,
								"account_currency": tax.account_currency,
								"base_tax_amount": tax.base_tax_amount,
								"tax_amount": tax.tax_amount,
								"base_total": tax.base_total,
								"total": tax.total,
								"tax_amount_after_discount_amount": tax.tax_amount_after_discount_amount 
							})
						# fee.taxes = 
						if self.receivable_account:
							fee.receivable_account = self.receivable_account
						if self.income_account:
							fee.income_account = self.income_account
						fee.save()
						created_records += 1
			except Exception as e:
				error = True
				err_msg = frappe.get_traceback()
				error_logs.append(f"Error for student {st.name}: {err_msg}")
		if error:
			frappe.db.rollback()
			frappe.db.set_value("Transportation Fee Schedule", self.name,
								"fee_creation_status", "Failed")
			frappe.db.set_value("Transportation Fee Schedule", self.name,
							"error_log", "\n".join(error_logs))

		else:
			frappe.db.set_value("Transportation Fee Schedule", self.name,
								"fee_creation_status", "Successful")
			frappe.db.set_value("Transportation Fee Schedule", self.name, "error_log", None)

		frappe.publish_realtime(
			"transportation_fee_progress", {"progress": "100", "reload": 1}, user=frappe.session.user
		)
			

	@frappe.whitelist()
	def get_transportation_student_count(self):
		students = frappe.db.get_all("Student", filters=[
			["transportation_fee_structure", "is", "set"]
		])

		return len(students)
